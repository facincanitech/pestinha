"""
DESENHO - o pet olha a janela que está na frente e faz um desenho dela, com giz de cera.

O desenho melhora com a prática: cada desenho feito conta, e a habilidade sobe devagar
(1 - e^(-feitos/30)). No começo é um rabisco de criança (poucas cores, borrado, sai da
linha, com sol no canto); com o tempo ganha mais detalhe, mais cores e traço firme.

Nada sai do computador. Cada desenho é guardado em memory/pets/<pet>/desenhos/.
Só acontece com a permissão "Fazer desenhos da tela" ligada.
"""

import math
import random
from datetime import datetime

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QImage, QPainter, QPainterPath, QPen, QPixmap

from .. import plataforma
from ..log import log
from ..store import read_json, write_json
from .objetos import Thing

PRATICA = 30.0              # desenhos para chegar a ~63% da habilidade
LARGURA = 300               # largura da folha em px
GIZ = ["#e53935", "#fb8c00", "#fdd835", "#7cb342", "#2e7d32", "#4fc3f7",
       "#1e5bd8", "#8e44ad", "#f06292", "#8d5524", "#212121", "#9e9e9e"]
GIZ_RGB = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in GIZ], dtype=float)
PESO_LUZ = np.array([0.299, 0.587, 0.114])


def _lerp(a, b, t):
    return a + (b - a) * t


def _imagem_para_rgb(img):
    """QImage -> array numpy (altura, largura, 3)."""
    img = img.convertToFormat(QImage.Format_RGB888)
    w, h, linha = img.width(), img.height(), img.bytesPerLine()
    dados = np.frombuffer(img.constBits(), dtype=np.uint8, count=linha * h).reshape(h, linha)
    return dados[:, : w * 3].reshape(h, w, 3).astype(float).copy()


def _reduzir(rgb, gw, gh):
    """Média de blocos: a imagem vira uma grade gw x gh de cores."""
    h, w = rgb.shape[:2]
    ys = np.linspace(0, h, gh + 1).astype(int)
    xs = np.linspace(0, w, gw + 1).astype(int)
    out = np.zeros((gh, gw, 3))
    for j in range(gh):
        faixa = rgb[ys[j]:max(ys[j + 1], ys[j] + 1)]
        for i in range(gw):
            bloco = faixa[:, xs[i]:max(xs[i + 1], xs[i] + 1)]
            out[j, i] = bloco.reshape(-1, 3).mean(axis=0)
    return out


def _cor(rgb, alfa):
    c = QColor(int(rgb[0]), int(rgb[1]), int(rgb[2]))
    c.setAlpha(int(alfa))
    return c


def _linha_tremida(p, a, b, tremor, r):
    """Linha de a até b com uma curvinha de mão trêmula."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1.0
    off = r.uniform(-1, 1) * tremor * n
    path = QPainterPath(QPointF(*a))
    path.quadTo(QPointF(mx - dy / n * off, my + dx / n * off), QPointF(*b))
    p.drawPath(path)


def _area(W, H):
    """Onde ele pinta, dentro da folha (o resto é margem, assinatura e autorretrato)."""
    return QRectF(18, 26, W - 36, H - 26 - 40)


def desenhar(rgb, s, nome, numero, moldura, olho, emocao, r=None, modelo=None):
    """
    Faz o desenho (QPixmap) a partir da imagem da janela.
    s: habilidade 0..1. moldura/olho: cores do pet (QColor), para o autorretrato.
    """
    r = r or random.Random()
    h0, w0 = rgb.shape[:2]
    aspecto = min(1.8, max(0.75, w0 / max(1, h0)))
    W = LARGURA
    H = int(max(180, min(360, W / aspecto + 40)))
    area = _area(W, H)

    gw = int(round(_lerp(8, 40, s) + (max(0.0, s - 0.85) / 0.15) * 24))
    gh = max(4, int(round(gw * area.height() / area.width())))
    grade = _reduzir(rgb, gw, gh)
    luz = grade @ PESO_LUZ / 255.0

    # cores: o pet pega só os gizes que mais aparecem; quanto mais hábil, mais gizes e mais fiel
    dist = ((grade[:, :, None, :] - GIZ_RGB[None, None]) ** 2).sum(-1)
    escuros = luz < 0.85
    usados = np.bincount(dist.argmin(-1)[escuros].ravel(), minlength=len(GIZ)) if escuros.any() else np.ones(len(GIZ))
    k = int(round(_lerp(4, 12, s)))
    caixa = np.argsort(-usados)[:k]
    escolha = caixa[dist[:, :, caixa].argmin(-1)]
    cores = GIZ_RGB[escolha]
    if s > 0.6:
        t = min(0.95, (s - 0.6) / 0.4 * 0.95)
        cores = cores * (1 - t) + grade * t
    if emocao == "triste":
        cinza = (cores @ PESO_LUZ)[..., None]
        cores = cores * 0.5 + np.concatenate([cinza * 0.8, cinza * 0.85, cinza * 1.1], -1) * 0.5

    # contornos: onde a luz muda de repente
    fina = _reduzir(rgb, gw * 2, gh * 2) @ PESO_LUZ / 255.0
    gy, gx = np.gradient(fina)
    forca = np.hypot(gx, gy)
    corte = max(0.06, float(np.quantile(forca, 1 - _lerp(0.04, 0.16, s))))
    bordas = forca > corte

    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    # folha e fita
    folha = QRectF(4, 6, W - 8, H - 10)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, 45))
    p.drawRect(folha.translated(3, 4))
    p.setBrush(QColor("#fffdf6"))
    p.drawRect(folha)
    p.save()
    p.translate(W / 2, 8)
    p.rotate(r.uniform(-7, 7))
    p.setBrush(QColor(255, 238, 150, 175))
    p.drawRect(QRectF(-30, -8, 60, 16))
    p.restore()

    if modelo is not None and not modelo.isNull():
        mini = modelo.scaledToWidth(64, Qt.SmoothTransformation)
        p.save()
        p.translate(W - 44, 30)
        p.rotate(r.uniform(4, 10))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawRect(QRectF(-mini.width() / 2 + 2, -mini.height() / 2 + 3, mini.width(), mini.height()))
        p.drawImage(QPointF(-mini.width() / 2, -mini.height() / 2), mini)
        p.setBrush(QColor(255, 238, 150, 190))
        p.drawRect(QRectF(-12, -mini.height() / 2 - 6, 24, 10))
        p.restore()

    cw, ch = area.width() / gw, area.height() / gh
    bagunca = _lerp(0.9, 0.08, s)            # quanto sai da linha
    tremor = _lerp(0.35, 0.04, s)
    largura = max(1.4, min(cw, ch) * _lerp(0.95, 0.55, s))
    pula = 0.3 * (1 - s) ** 2                # no começo ele esquece de pintar uns pedaços
    alfa = _lerp(150, 225, s)

    # pintura: rabisco em zigue-zague em cada quadradinho
    for j in range(gh):
        for i in range(gw):
            if luz[j, i] > 0.85 or r.random() < pula:
                continue
            p.setPen(QPen(_cor(cores[j, i], alfa), largura, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            x0, y0 = area.left() + i * cw, area.top() + j * ch
            n = 2 + int(round(2 * s))
            path = QPainterPath()
            for v in range(n + 1):
                px = x0 + v / n * cw + r.uniform(-0.5, 0.5) * bagunca * cw
                py = y0 + (0.15 if v % 2 == 0 else 0.85) * ch + r.uniform(-0.5, 0.5) * bagunca * ch
                if v == 0:
                    path.moveTo(px, py)
                else:
                    path.lineTo(px, py)
            p.drawPath(path)

    # contornos
    ew, eh = area.width() / (gw * 2), area.height() / (gh * 2)
    p.setPen(QPen(QColor(40, 32, 30, int(_lerp(170, 230, s))), max(1.1, _lerp(2.6, 1.3, s)),
                  Qt.SolidLine, Qt.RoundCap))
    for y, x in zip(*np.nonzero(bordas)):
        a = math.atan2(gy[y, x], gx[y, x]) + math.pi / 2
        meio = (area.left() + (x + 0.5) * ew + r.uniform(-1, 1) * tremor * ew * 2,
                area.top() + (y + 0.5) * eh + r.uniform(-1, 1) * tremor * eh * 2)
        L = (ew + eh) * 0.75 * (1 + (1 - s) * r.uniform(-0.3, 0.6))
        _linha_tremida(p, (meio[0] - math.cos(a) * L / 2, meio[1] - math.sin(a) * L / 2),
                       (meio[0] + math.cos(a) * L / 2, meio[1] + math.sin(a) * L / 2), tremor, r)

    # coisas de criança: sol no canto (some quando ele fica bom) e coraçõezinhos se feliz
    if s < 0.45 and modelo is None:
        cx, cy, raio = area.right() - 16, area.top() + 14, 11
        p.setPen(QPen(QColor(253, 216, 53, 230), 3, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(QColor(253, 216, 53, 200))
        p.drawEllipse(QPointF(cx, cy), raio, raio)
        for v in range(8):
            a = v * math.pi / 4 + r.uniform(-0.2, 0.2)
            _linha_tremida(p, (cx + math.cos(a) * (raio + 4), cy + math.sin(a) * (raio + 4)),
                           (cx + math.cos(a) * (raio + 12), cy + math.sin(a) * (raio + 12)), 0.2, r)
        p.setBrush(Qt.NoBrush)
    if emocao == "feliz":
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(240, 98, 146, 210))
        for _ in range(3):
            hx, hy, t = r.uniform(area.left(), area.right()), r.uniform(area.top(), area.bottom()), r.uniform(5, 8)
            cor = QPainterPath(QPointF(hx, hy + t))
            cor.cubicTo(hx - t * 1.6, hy - t * 0.2, hx - t * 0.6, hy - t * 1.3, hx, hy - t * 0.4)
            cor.cubicTo(hx + t * 0.6, hy - t * 1.3, hx + t * 1.6, hy - t * 0.2, hx, hy + t)
            p.drawPath(cor)

    # autorretrato no canto: a telinha com dois olhos, que fica mais caprichada com o tempo
    bx, by, lado = 16, H - 44, 30
    t = tremor * 10
    p.setPen(QPen(moldura, _lerp(3.2, 2.2, s), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    cantos = [(bx + r.uniform(-t, t), by + r.uniform(-t, t)), (bx + lado + r.uniform(-t, t), by + r.uniform(-t, t)),
              (bx + lado + r.uniform(-t, t), by + lado * 0.8 + r.uniform(-t, t)), (bx + r.uniform(-t, t), by + lado * 0.8 + r.uniform(-t, t))]
    for v in range(4):
        _linha_tremida(p, cantos[v], cantos[(v + 1) % 4], tremor, r)
    p.setPen(Qt.NoPen)
    p.setBrush(olho)
    for ox in (0.32, 0.68):
        p.drawEllipse(QPointF(bx + lado * ox + r.uniform(-t, t) * 0.4, by + lado * 0.38), 2.6, 3.4)
    if s > 0.4:
        p.setPen(QPen(olho, 1.6, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(bx + lado * 0.35, by + lado * 0.42, lado * 0.3, lado * 0.22), 200 * 16, 140 * 16)

    # assinatura: torta no começo, firme depois
    p.setPen(QColor(55, 45, 40, 230))
    fonte = QFont("Segoe Print", 10)
    p.setFont(fonte)
    texto = f"{nome}  nº {numero}"
    if s > 0.7:
        texto += "  " + datetime.now().strftime("%d/%m")
    medida = QFontMetricsF(fonte)
    x = W - 22 - medida.horizontalAdvance(texto)
    for letra in texto:
        p.save()
        p.translate(x, H - 18 + r.uniform(-1, 1) * tremor * 12)
        p.rotate(r.uniform(-1, 1) * tremor * 40)
        p.drawText(QPointF(0, 0), letra)
        p.restore()
        x += medida.horizontalAdvance(letra) + r.uniform(-0.3, 0.8) * tremor * 4
    p.end()
    return QPixmap.fromImage(img)


def similaridade(pix, rgb_modelo):
    """0..1: quanto o desenho (só a área pintada) parece o modelo, comparando cores em grade 24x16."""
    recorte = pix.toImage().copy(_area(pix.width(), pix.height()).toRect())
    fundo = QImage(recorte.size(), QImage.Format_RGB888)
    fundo.fill(QColor("#fffdf6"))
    p = QPainter(fundo)
    p.drawImage(0, 0, recorte)
    p.end()
    a = _reduzir(_imagem_para_rgb(fundo), 24, 16)
    b = _reduzir(rgb_modelo, 24, 16)
    erro = np.abs(a - b).mean() / 255.0
    return float(max(0.0, min(1.0, 1.0 - erro * 2.2)))


def anotar(pix, texto):
    """Escreve uma linha pequena no pé da folha (tentativa e semelhança)."""
    img = pix.toImage()
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QColor(90, 80, 70, 220))
    p.setFont(QFont("Segoe Print", 8))
    p.drawText(QPointF(54, img.height() - 34), texto)
    p.end()
    return QPixmap.fromImage(img)


def _interessante(rgb):
    """
    O pedaço da tela que chama atenção (colorido e cheio de detalhe, tipo thumbnail ou vídeo).
    Devolve (x0, y0, x1, y1) em frações da imagem, ou None se nada se destaca.
    """
    gw, gh = 16, 10
    h, w = rgb.shape[:2]
    ys = np.linspace(0, h, gh + 1).astype(int)
    xs = np.linspace(0, w, gw + 1).astype(int)
    nota = np.zeros((gh, gw))
    for j in range(gh):
        for i in range(gw):
            b = rgb[ys[j]:ys[j + 1], xs[i]:xs[i + 1]].reshape(-1, 3)
            if len(b) == 0:
                continue
            rg = b[:, 0] - b[:, 1]
            yb = 0.5 * (b[:, 0] + b[:, 1]) - b[:, 2]
            cor = math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())
            nota[j, i] = cor + 0.5 * (b @ PESO_LUZ).std()
    if nota.max() < 28.0:
        return None
    # a mancha colorida inteira (vídeo, thumbnail, foto): regiões ligadas acima do corte
    marcada = nota > max(20.0, 0.4 * nota.max())
    visto = np.zeros_like(marcada)
    melhor, caixa = 0.0, None
    for j0 in range(gh):
        for i0 in range(gw):
            if not marcada[j0, i0] or visto[j0, i0]:
                continue
            pilha, celulas = [(j0, i0)], []
            visto[j0, i0] = True
            while pilha:
                j, i = pilha.pop()
                celulas.append((j, i))
                for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nj, ni = j + dj, i + di
                    if 0 <= nj < gh and 0 <= ni < gw and marcada[nj, ni] and not visto[nj, ni]:
                        visto[nj, ni] = True
                        pilha.append((nj, ni))
            soma = sum(nota[c] for c in celulas)
            if len(celulas) >= 4 and soma > melhor:
                js, is_ = [c[0] for c in celulas], [c[1] for c in celulas]
                melhor, caixa = soma, (min(is_) / gw, min(js) / gh, (max(is_) + 1) / gw, (max(js) + 1) / gh)
    return caixa


class DesenhoThing(Thing):
    """O desenho na tela: cai, pode ser arrastado e fecha com um clique (continua salvo na galeria)."""
    def __init__(self, pix):
        self.pix = pix
        self.valida = not pix.isNull()
        super().__init__(pix.width() + 16, pix.height() + 16)
        self.setToolTip("clique para fechar (o desenho fica salvo na galeria)")

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.translate(self.width() / 2, self.height() / 2)
        p.rotate(self.tilt * 0.5)
        p.drawPixmap(-self.pix.width() // 2, -self.pix.height() // 2, self.pix)
        p.end()


MAX_TENTATIVAS = 15         # tentativas no mesmo modelo antes de procurar outro
BOM_O_BASTANTE = 0.80       # semelhança em que ele dá o modelo por dominado


class Desenhista:
    """
    Olha a tela, escolhe algo que achou legal (o pedaço mais colorido e cheio de detalhe),
    guarda como modelo e desenha esse modelo de novo a cada vez, melhorando até ficar parecido.
    Sem nada interessante na tela, desenha a janela inteira, como um rabisco livre.
    """
    def __init__(self, pasta_do_pet, nome, aparencia):
        self.arquivo = pasta_do_pet / "desenhos.json"
        self.galeria = pasta_do_pet / "desenhos"
        self.nome = nome
        self.moldura = QColor(aparencia.moldura)
        self.olho = QColor(aparencia.olho)
        dados = read_json(self.arquivo, default={})
        dados = dados if isinstance(dados, dict) else {}
        self.feitos = self._inteiro(dados.get("feitos"))
        self.recompensa = lambda quanto, motivo: 0          # o app liga na carteira
        self.modelos = self._inteiro(dados.get("modelos"))
        ref = dados.get("modelo_atual")
        self.ref = None
        if isinstance(ref, dict) and isinstance(ref.get("id"), int):
            self.ref = {"id": ref["id"], "tentativas": self._inteiro(ref.get("tentativas")),
                        "melhor": float(ref.get("melhor", 0.0)) if isinstance(ref.get("melhor"), (int, float)) else 0.0}

    @staticmethod
    def _inteiro(v):
        return int(v) if isinstance(v, (int, float)) and 0 <= v < 1e7 else 0

    @property
    def habilidade(self):
        """Prática geral: 0 = rabisco, 1 = caprichado."""
        return 1.0 - math.exp(-self.feitos / PRATICA)

    def _pasta_ref(self, ref_id):
        return self.galeria / f"modelo_{ref_id:03d}"

    def _capturar(self):
        """Imagem (QImage) da janela que está na frente, ou da tela toda se não der."""
        retangulo = plataforma.retangulo_ativo(1.0)
        tela = QGuiApplication.primaryScreen()
        if retangulo:
            cx, cy = (retangulo[0] + retangulo[2]) / 2, (retangulo[1] + retangulo[3]) / 2
            for sc in QGuiApplication.screens():
                g, dpr = sc.geometry(), sc.devicePixelRatio()
                if g.x() <= cx < g.x() + g.width() * dpr and g.y() <= cy < g.y() + g.height() * dpr:
                    tela = sc
                    break
        imagem = tela.grabWindow(0).toImage()
        if imagem.isNull():
            return None
        if retangulo and plataforma.NOME_DO_SISTEMA == "Windows":
            g = tela.geometry()
            x0, y0 = max(0, int(retangulo[0] - g.x())), max(0, int(retangulo[1] - g.y()))
            x1, y1 = min(imagem.width(), int(retangulo[2] - g.x())), min(imagem.height(), int(retangulo[3] - g.y()))
            if x1 - x0 > 60 and y1 - y0 > 60:
                imagem = imagem.copy(x0, y0, x1 - x0, y1 - y0)
        return imagem

    def _novo_modelo(self, imagem):
        """Procura algo legal na tela; se achar, guarda como o próximo modelo. Devolve True se achou."""
        pequena = imagem.scaledToWidth(min(480, imagem.width()), Qt.SmoothTransformation)
        caixa = _interessante(_imagem_para_rgb(pequena))
        if caixa is None:
            return False
        w, h = imagem.width(), imagem.height()
        recorte = imagem.copy(int(caixa[0] * w), int(caixa[1] * h),
                              int((caixa[2] - caixa[0]) * w), int((caixa[3] - caixa[1]) * h))
        if recorte.width() > 640:
            recorte = recorte.scaledToWidth(640, Qt.SmoothTransformation)
        self.modelos += 1
        pasta = self._pasta_ref(self.modelos)
        pasta.mkdir(parents=True, exist_ok=True)
        recorte.save(str(pasta / "modelo.png"), "PNG")
        self.ref = {"id": self.modelos, "tentativas": 0, "melhor": 0.0}
        log(f"[desenho] achou algo legal na tela: modelo {self.modelos}")
        return True

    def fazer(self, emocao):
        """Faz um desenho novo agora. None se não conseguiu olhar a tela."""
        try:
            return self._fazer(emocao)
        except Exception as error:
            log(f"[desenho] não deu para desenhar: {error}")
            return None

    def _fazer(self, emocao):
        terminado = self.ref is None or self.ref["tentativas"] >= MAX_TENTATIVAS or self.ref["melhor"] >= BOM_O_BASTANTE
        modelo = None
        if terminado:
            self.ref = None
            imagem = self._capturar()
            if imagem is None:
                return None
            if not self._novo_modelo(imagem):
                modelo = None
                rgb = _imagem_para_rgb(imagem.scaledToWidth(min(480, imagem.width()), Qt.SmoothTransformation))
        if self.ref is not None:
            modelo = QImage(str(self._pasta_ref(self.ref["id"]) / "modelo.png"))
            if modelo.isNull():
                self.ref = None
                return None
            rgb = _imagem_para_rgb(modelo.scaledToWidth(min(480, modelo.width()), Qt.SmoothTransformation))

        base = self.habilidade
        self.feitos += 1
        if self.ref is not None:
            self.ref["tentativas"] += 1
            k = self.ref["tentativas"]
            s = base + (1.0 - base) * (1.0 - math.exp(-(k - 1) / 4.5))       # cada tentativa no mesmo modelo ajuda muito
            pix = desenhar(rgb, s, self.nome, self.feitos, self.moldura, self.olho, emocao, modelo=modelo)
            sim = similaridade(pix, rgb)
            if self.ref["melhor"] < BOM_O_BASTANTE <= sim:
                self.recompensa(40, "dominou um desenho")
            self.ref["melhor"] = max(self.ref["melhor"], sim)
            pix = anotar(pix, f"tentativa {k} · {round(sim * 100)}% parecido")
            destino = self._pasta_ref(self.ref["id"]) / f"tentativa_{k:02d}.png"
            log(f"[desenho] modelo {self.ref['id']}, tentativa {k}, habilidade {s:.2f}, {sim:.0%} parecido")
        else:
            pix = desenhar(rgb, base, self.nome, self.feitos, self.moldura, self.olho, emocao)
            destino = self.galeria / f"livre_{self.feitos:04d}.png"
            log(f"[desenho] livre nº {self.feitos}, habilidade {base:.2f}")
        self.recompensa(3, "fez um desenho")
        try:
            self.galeria.mkdir(parents=True, exist_ok=True)
            pix.save(str(destino), "PNG")
            write_json(self.arquivo, {"feitos": self.feitos, "modelos": self.modelos, "modelo_atual": self.ref})
        except OSError as error:
            log(f"[desenho] não salvou na galeria: {error}")
        return DesenhoThing(pix)
