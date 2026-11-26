"""
LOJA (app do celular) - categorias em cards; dentro de cada uma, os itens com figurinha, nome e preço em ouro.
Toque em "Comprar" para comprar (e já usar); em "Usar" para trocar de casa, celular, chapéu ou cortina.
"""

import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..core.economia import CATALOGO, CATEGORIAS, EQUIPAVEIS, FIGURA_CATEGORIA, FIGURAS
from ..core.emotion import PRIORITY

FUNDO = QColor("#12131a")
CARD = QColor("#1e2130")
OURO = QColor("#ffc83d")
CORES_CAT = {"casa": "#ff7043", "eletronico": "#42a5f5", "videogame": "#ab47bc", "movel": "#26a69a",
             "cortina": "#ec407a", "chapeu": "#ffa726"}


def _texto_que_cabe(p, r, texto, maximo, minimo=8, cor=QColor("#ffffff"), flags=Qt.AlignCenter | Qt.TextWordWrap):
    for tam in range(maximo, minimo - 1, -1):
        f = QFont("Segoe UI", tam, QFont.Bold)
        m = QFontMetricsF(f)
        if max((m.horizontalAdvance(w) for w in texto.split()), default=0) <= r.width() and \
                m.boundingRect(r, int(flags), texto).height() <= r.height():
            break
    p.setFont(f)
    p.setPen(cor)
    p.drawText(r, flags, texto)


class LojaApp(QWidget):
    def __init__(self, app, ao_mudar=None):
        super().__init__()
        self.app = app
        self.ao_mudar = ao_mudar          # avisa a tela do celular (título, saldo)
        self.categoria = None
        self.rolagem = 0.0
        self.aviso = None                 # (texto, até)
        self._botoes = []                 # [(QRectF, ação, item)]
        t = QTimer(self)
        t.timeout.connect(self.update)
        t.start(200)

    @property
    def titulo(self):
        return f"Loja · {CATEGORIAS[self.categoria]}" if self.categoria else "Loja"

    def voltar(self):
        """Devolve True se tratou o voltar (saiu de uma categoria)."""
        if self.categoria:
            self.categoria = None
            self.rolagem = 0
            self.update()
            return True
        return False

    # ---------------- desenho ----------------

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), FUNDO)
        self._botoes = []
        p.translate(0, -self.rolagem)
        if self.categoria is None:
            self._altura = self._categorias(p)
        else:
            self._altura = self._itens(p)
        p.resetTransform()
        if self.aviso and time.monotonic() < self.aviso[1]:
            r = QRectF(20, self.height() - 60, self.width() - 40, 40)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 200))
            p.drawRoundedRect(r, 20, 20)
            _texto_que_cabe(p, r, self.aviso[0], 12)
        p.end()

    def _saldo(self, p, y):
        r = QRectF(10, y, self.width() - 20, 52)
        g = QLinearGradient(r.topLeft(), r.topRight())
        g.setColorAt(0, QColor("#3a2c05"))
        g.setColorAt(1, QColor("#6b4e0a"))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, 16, 16)
        p.setFont(QFont("Segoe UI Emoji", 20))
        p.setPen(OURO)
        p.drawText(QRectF(r.left() + 12, r.top(), 40, r.height()), Qt.AlignCenter, "🪙")
        p.setFont(QFont("Segoe UI", 18, QFont.Black))
        p.drawText(QRectF(r.left() + 56, r.top(), 200, r.height()), Qt.AlignLeft | Qt.AlignVCenter,
                   f"{self.app.carteira.moedas:,}".replace(",", "."))
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        p.setPen(QColor("#e0c27a"))
        p.drawText(QRectF(r.right() - 140, r.top(), 128, r.height()), Qt.AlignRight | Qt.AlignVCenter, "suas moedas")
        return r.bottom() + 12

    def _categorias(self, p):
        y = self._saldo(p, 6)
        w = (self.width() - 30) / 2
        c = self.app.carteira
        for i, (cat, nome) in enumerate(CATEGORIAS.items()):
            r = QRectF(10 + (i % 2) * (w + 10), y + (i // 2) * 132, w, 122)
            cor = QColor(CORES_CAT[cat])
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0, cor.darker(140))
            g.setColorAt(1, cor.darker(260))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(r, 18, 18)
            p.setFont(QFont("Segoe UI Emoji", 34))
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(r.left(), r.top() + 8, r.width(), 56), Qt.AlignCenter, FIGURA_CATEGORIA[cat])
            _texto_que_cabe(p, QRectF(r.left() + 6, r.top() + 66, r.width() - 12, 24), nome, 15)
            total = sum(1 for d in CATALOGO.values() if d[0] == cat)
            tem = sum(1 for i2, d in CATALOGO.items() if d[0] == cat and c.tem(i2))
            p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.setPen(QColor(255, 255, 255, 170))
            p.drawText(QRectF(r.left(), r.top() + 92, r.width(), 20), Qt.AlignCenter, f"{tem}/{total} itens")
            self._botoes.append((r, "categoria", cat))
        return y + ((len(CATEGORIAS) + 1) // 2) * 132

    def _itens(self, p):
        y = self._saldo(p, 6)
        c = self.app.carteira
        itens = sorted(((i, d) for i, d in CATALOGO.items() if d[0] == self.categoria), key=lambda x: (x[1][3], x[1][2]))
        w = (self.width() - 30) / 2
        cor_cat = QColor(CORES_CAT[self.categoria])
        for k, (item, (cat, nome, preco, _nivel)) in enumerate(itens):
            r = QRectF(10 + (k % 2) * (w + 10), y + (k // 2) * 190, w, 180)
            usando = c.equipado.get(cat) == item
            p.setPen(QPen(OURO, 2) if usando else Qt.NoPen)
            p.setBrush(CARD)
            p.drawRoundedRect(r, 16, 16)
            fig = QRectF(r.left() + 10, r.top() + 10, r.width() - 20, 74)
            p.setPen(Qt.NoPen)
            p.setBrush(cor_cat.darker(220))
            p.drawRoundedRect(fig, 12, 12)
            p.setFont(QFont("Segoe UI Emoji", 34))
            p.setPen(QColor("#ffffff"))
            p.drawText(fig, Qt.AlignCenter, FIGURAS.get(item, "❔"))
            _texto_que_cabe(p, QRectF(r.left() + 8, r.top() + 88, r.width() - 16, 34), nome, 12, 8)
            if not c.tem(item):
                p.setFont(QFont("Segoe UI", 13, QFont.Black))
                p.setPen(OURO)
                p.drawText(QRectF(r.left(), r.top() + 122, r.width(), 18), Qt.AlignCenter, f"🪙 {preco}")
            bot = QRectF(r.left() + 10, r.bottom() - 36, r.width() - 20, 28)
            if not c.tem(item):
                pode = c.pode_comprar(item)
                rotulo, fundo, letra, acao = ("Comprar", OURO, QColor("#3a2a00"), "comprar") if pode else \
                    ("Falta 🪙", QColor("#2c2f3d"), QColor("#8a8fa3"), None)
            elif cat in EQUIPAVEIS:
                if usando and cat in ("chapeu", "cortina"):
                    rotulo, fundo, letra, acao = "Tirar", QColor("#37474f"), QColor("#ffffff"), "usar"
                elif usando:
                    rotulo, fundo, letra, acao = "Usando ✓", QColor("#1b5e20"), QColor("#c8e6c9"), None
                else:
                    rotulo, fundo, letra, acao = "Usar", QColor("#2e7d32"), QColor("#ffffff"), "usar"
            else:
                rotulo, fundo, letra, acao = "Na casa ✓", QColor("#1b5e20"), QColor("#c8e6c9"), None
            p.setPen(Qt.NoPen)
            p.setBrush(fundo)
            p.drawRoundedRect(bot, 14, 14)
            _texto_que_cabe(p, bot, rotulo, 12, 9, letra)
            if acao:
                self._botoes.append((bot, acao, item))
        return y + ((len(itens) + 1) // 2) * 190

    # ---------------- mouse ----------------

    def wheelEvent(self, ev):
        maximo = max(0.0, getattr(self, "_altura", 0) - self.height() + 20)
        self.rolagem = min(maximo, max(0.0, self.rolagem - ev.angleDelta().y() / 2))
        self.update()

    def mousePressEvent(self, ev):
        pos = ev.position()
        pos.setY(pos.y() + self.rolagem)
        for r, acao, item in self._botoes:
            if r.contains(pos):
                self._acao(acao, item)
                return

    def _acao(self, acao, item):
        a, c = self.app, self.app.carteira
        if acao == "categoria":
            self.categoria, self.rolagem = item, 0
        elif acao == "comprar":
            primeira_casa = CATALOGO[item][0] == "casa" and not c.casa
            if c.comprar(item):
                a.casinha_ctl.aplicar_progresso()
                a.update_visibility()
                a.emotion.force("feliz", 4.0, priority=PRIORITY.get("carinho", 15))
                self.aviso = (f"Comprado: {CATALOGO[item][1]}!", time.monotonic() + 2)
                if primeira_casa:
                    a.tray.icon.showMessage(a.nome, "Agora eu tenho uma casa!")
        elif acao == "usar":
            if c.equipar(item):
                a.casinha_ctl.aplicar_progresso()
                a.update_visibility()
                if a.aparelho is not None:
                    a.aparelho.ajustar()          # trocou de celular/notebook/PC: a tela muda de formato
        if self.ao_mudar:
            self.ao_mudar()
        self.update()
