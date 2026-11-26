"""
DESENHO DO ROSTO - só o que se desenha do pet: moldura, olhos, brilho, acessórios e os Zzz.

Não tem estado nem decisão: recebe a forma dos olhos, a direção do olhar e a aparência do pet
(cores e acessórios, de pets/<pet>.json) e pinta. Os acessórios são uma camada por cima do rosto:
não mudam os olhos nem as expressões.
"""

import math
import re
from dataclasses import dataclass, field, replace

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPen, QPolygonF

from ..ajustes import ZZZ_PERIODO as ZZZ_PERIOD, ZZZ_QUANTIDADE as ZZZ_COUNT

BODY_W, BODY_H = 120, 90
FRAME = QColor("#63e56f")
SHELL = QColor("#101512")
SCREEN = QColor("#171e19")
EYE = QColor("#3ee877")
SHINE = QColor("#c8ffd8")

ACESSORIOS = ("oculos", "gravata", "chapeu_cowboy", "bone", "coroa", "cartola", "gorro")
COR_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
COR_PADRAO_ACESSORIO = {"oculos": "#e8e8e8", "gravata": "#b3261e", "chapeu_cowboy": "#9a5b2e", "bone": "#d32f2f",
                        "coroa": "#f2c14e", "cartola": "#1b1b1f", "gorro": "#d32f2f"}


@dataclass(frozen=True)
class Aparencia:
    """Cores do corpo e acessórios de um pet. O padrão é o visual original (o do pet)."""
    moldura: QColor = field(default_factory=lambda: QColor(FRAME))
    casca: QColor = field(default_factory=lambda: QColor(SHELL))
    tela: QColor = field(default_factory=lambda: QColor(SCREEN))
    olho: QColor = field(default_factory=lambda: QColor(EYE))
    brilho: QColor = field(default_factory=lambda: QColor(SHINE))
    acessorios: tuple = ()             # ((nome, QColor), ...) na ordem em que são desenhados


CAMPOS_DE_COR = ("moldura", "casca", "tela", "olho", "brilho")


def aparencia_de(dados):
    """
    Monta a Aparencia a partir do "aparencia" do pet.json. Cor fora do formato #rrggbb e
    acessório desconhecido são ignorados (ficam com o padrão), como os outros campos do pet.
    """
    if not isinstance(dados, dict):
        return Aparencia()
    cores = {k: QColor(dados[k]) for k in CAMPOS_DE_COR
             if isinstance(dados.get(k), str) and COR_HEX.match(dados[k])}
    pedidos = dados.get("acessorios")
    acessorios = []
    if isinstance(pedidos, dict):
        for nome in ACESSORIOS:                         # ordem fixa: a gravata não cobre os óculos
            if nome in pedidos:
                cor = pedidos[nome]
                cor = cor if isinstance(cor, str) and COR_HEX.match(cor) else COR_PADRAO_ACESSORIO[nome]
                acessorios.append((nome, QColor(cor)))
    return Aparencia(**cores, acessorios=tuple(acessorios))


PADRAO = Aparencia()


def lerp_shape(current, target, k):
    """Interpola duas formas de olho: `k` entre 0 (atual) e 1 (alvo), para a transição ser suave."""
    return {key: current[key] + (target[key] - current[key]) * k for key in target}


def draw_face(p, shape, gaze=(0.0, 0.0), blink=1.0, emotion="observando", carinho=False, aparencia=PADRAO):
    """Desenha moldura + tela + olhos (+ acessórios) com centro na origem do painter."""
    a = aparencia
    p.setPen(QPen(a.moldura, 5))
    p.setBrush(a.casca)
    p.drawRoundedRect(QRectF(-BODY_W / 2, -BODY_H / 2, BODY_W, BODY_H), 20, 20)
    p.setPen(Qt.NoPen)
    p.setBrush(a.tela)
    p.drawRoundedRect(QRectF(-BODY_W / 2 + 11, -BODY_H / 2 + 11, BODY_W - 22, BODY_H - 22), 12, 12)
    for nome, cor in a.acessorios:
        if nome == "gravata":                          # por cima da tela, sempre dentro do contorno do corpo
            _gravata(p, cor)

    if carinho:
        # carinho: olhinhos fechados de felicidade, em arco para cima (^ ^)
        p.setPen(QPen(a.olho, 5, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        for side in (-1, 1):
            cx, cy = side * 24, shape["dy"]
            p.drawArc(QRectF(cx - 15, cy - 8, 30, 22), 0, 180 * 16)
        p.setPen(Qt.NoPen)
    else:
        _olhos(p, shape, gaze, blink, emotion, a)
    for nome, cor in a.acessorios:
        if nome == "oculos":
            _oculos(p, cor)
    for nome, cor in a.acessorios:
        if nome == "chapeu_cowboy":
            _chapeu_cowboy(p, cor)
        elif nome == "bone":
            _bone(p, cor)
        elif nome == "coroa":
            _coroa(p, cor)
        elif nome == "cartola":
            _cartola(p, cor)
        elif nome == "gorro":
            _gorro(p, cor)


def com_acessorio(aparencia, nome, ligado, cor=None):
    """Nova Aparencia com o acessório posto (ligado) ou tirado; a ordem de desenho continua a de ACESSORIOS."""
    resto = [(n, c) for n, c in aparencia.acessorios if n != nome]
    if ligado:
        resto.append((nome, QColor(cor or COR_PADRAO_ACESSORIO.get(nome, "#ffffff"))))
    resto.sort(key=lambda par: ACESSORIOS.index(par[0]) if par[0] in ACESSORIOS else 99)
    return replace(aparencia, acessorios=tuple(resto))


def _bone(p, cor):
    """Boné de lado, com a aba para a direita."""
    p.save()
    topo = -BODY_H / 2
    escura = cor.darker(150)
    p.setPen(QPen(escura, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(cor)
    copa = QPainterPath(QPointF(-44, topo + 2))
    copa.cubicTo(-42, topo - 32, 38, topo - 32, 40, topo + 2)
    copa.closeSubpath()
    p.drawPath(copa)
    aba = QPainterPath(QPointF(30, topo - 2))
    aba.quadTo(70, topo - 8, 78, topo + 2)
    aba.quadTo(60, topo + 6, 36, topo + 3)
    aba.closeSubpath()
    p.setBrush(escura)
    p.drawPath(aba)
    p.setBrush(QColor("#ffffff"))
    p.drawEllipse(QPointF(-2, topo - 24), 3, 3)
    p.restore()


def _cartola(p, cor):
    """Cartola de mágico, com fita."""
    p.save()
    topo = -BODY_H / 2
    p.setPen(QPen(QColor("#000000"), 1.4))
    p.setBrush(cor)
    p.drawRoundedRect(QRectF(-26, topo - 50, 52, 50), 4, 4)
    p.setBrush(QColor("#b71c1c"))
    p.drawRect(QRectF(-26, topo - 14, 52, 8))
    p.setBrush(cor)
    p.drawRoundedRect(QRectF(-48, topo - 6, 96, 9), 4, 4)
    p.restore()


def _gorro(p, cor):
    """Gorro com pompom caído para o lado."""
    p.save()
    topo = -BODY_H / 2
    p.setPen(Qt.NoPen)
    p.setBrush(cor)
    gorro = QPainterPath(QPointF(-44, topo + 2))
    gorro.cubicTo(-40, topo - 40, 30, topo - 50, 54, topo - 18)
    gorro.lineTo(40, topo + 2)
    gorro.closeSubpath()
    p.drawPath(gorro)
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(-48, topo - 6, 92, 12), 6, 6)
    p.drawEllipse(QPointF(56, topo - 16), 9, 9)
    p.restore()


def _coroa(p, cor):
    """Coroa de rei, com pedrinhas."""
    p.save()
    topo = -BODY_H / 2
    escura = cor.darker(150)
    p.setPen(QPen(escura, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(cor)
    coroa = QPolygonF([QPointF(-36, topo + 2), QPointF(-40, topo - 30), QPointF(-20, topo - 14),
                       QPointF(0, topo - 38), QPointF(20, topo - 14), QPointF(40, topo - 30),
                       QPointF(36, topo + 2)])
    p.drawPolygon(coroa)
    for x, c in ((-22, "#e53935"), (0, "#1e88e5"), (22, "#43a047")):
        p.setBrush(QColor(c))
        p.drawEllipse(QPointF(x, topo - 6), 4, 4)
    p.restore()


def _chapeu_cowboy(p, cor):
    """Chapéu de cowboy em cima da moldura: copa com o vinco no meio, fita e aba virada nas pontas."""
    p.save()
    topo = -BODY_H / 2
    escura = cor.darker(150)
    p.setPen(QPen(escura, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(cor)
    copa = QPainterPath(QPointF(-33, topo - 2))
    copa.lineTo(-29, topo - 30)
    copa.quadTo(-16, topo - 41, 0, topo - 32)
    copa.quadTo(16, topo - 41, 29, topo - 30)
    copa.lineTo(33, topo - 2)
    copa.closeSubpath()
    p.drawPath(copa)
    p.setPen(Qt.NoPen)
    p.setBrush(escura)
    p.drawRect(QRectF(-32, topo - 11, 64, 6))
    p.setPen(QPen(escura, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(cor.lighter(108))
    aba = QPainterPath(QPointF(-80, topo - 12))
    aba.quadTo(-58, topo + 6, 0, topo + 3)
    aba.quadTo(58, topo + 6, 80, topo - 12)
    aba.quadTo(52, topo - 3, 0, topo - 5)
    aba.quadTo(-52, topo - 3, -80, topo - 12)
    p.drawPath(aba)
    p.restore()


def _olhos(p, shape, gaze, blink, emotion, a):
    """Desenha os dois olhos: forma, piscada, brilho e direção do olhar."""
    gx, gy = gaze
    for side in (-1, 1):
        w = shape["w"]
        h = shape["h"] * blink
        if emotion == "curioso" and side == 1:
            h *= 1.15
        h = max(h, 3.0)
        cx = side * 24 + gx * 4
        cy = shape["dy"] + gy * 3
        top = cy - h / 2

        eye = QPainterPath()
        eye.addRoundedRect(QRectF(cx - w / 2, top, w, h), min(w, h) * 0.38, min(w, h) * 0.38)

        if blink > 0.5:
            outer_x = cx + side * w / 2
            inner_x = cx - side * w / 2
            lid = QPainterPath()
            lid.addPolygon(QPolygonF([
                QPointF(outer_x + side * 4, top - 40),
                QPointF(inner_x - side * 4, top - 40),
                QPointF(inner_x - side * 4, top + shape["inner"] * h),
                QPointF(outer_x + side * 4, top + shape["outer"] * h),
            ]))
            eye = eye.subtracted(lid)
            if shape["smile"] > 0.02:
                cut = QPainterPath()
                ch = h * shape["smile"] * 1.6
                cut.addEllipse(QRectF(cx - w * 0.75, top + h - ch * 0.45, w * 1.5, ch))
                eye = eye.subtracted(cut)

        p.setBrush(a.olho)
        p.drawPath(eye)

        if blink > 0.5 and h >= 8:                 # olho fechado não tem brilho
            p.save()
            p.setClipPath(eye)
            p.setBrush(a.brilho)
            sx = cx - w * 0.18 + gx * 3
            sy = top + h * (0.24 + max(shape["inner"], shape["outer"]) * 0.6) + gy * 2
            p.drawEllipse(QPointF(sx, sy), 3.6, 3.6)
            p.restore()



def _oculos(p, cor):
    """Armação por cima dos olhos: aro grosso em cima, fino embaixo, e a ponte no meio."""
    p.save()
    p.setBrush(Qt.NoBrush)
    for side in (-1, 1):
        lente = QRectF(side * 24 - 21, -25, 42, 52)
        vidro = QColor(cor)
        vidro.setAlpha(22)                              # um reflexo leve: o olho continua aparecendo
        p.setPen(Qt.NoPen)
        p.setBrush(vidro)
        p.drawRoundedRect(lente, 10, 10)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(cor, 2))
        p.drawRoundedRect(lente, 10, 10)
        p.setPen(QPen(cor, 5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(lente.left() + 4, lente.top()), QPointF(lente.right() - 4, lente.top()))
    p.setPen(QPen(cor, 3, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(-3, -18), QPointF(3, -18))       # ponte
    p.restore()


def _gravata(p, cor):
    """
    Gravata na frente do peito, dentro do contorno do corpo. Termina antes da borda de baixo para
    não cair na barra de tarefas quando ele anda sobre ela.
    """
    p.save()
    topo = BODY_H / 2 - 24                              # nó logo abaixo da tela, cola no contorno
    escura = cor.darker(140)
    p.setPen(QPen(escura, 1.2))
    p.setBrush(cor)
    p.drawPolygon(QPolygonF([QPointF(-4, topo), QPointF(4, topo), QPointF(3.5, topo + 6),
                             QPointF(-3.5, topo + 6)]))          # nó
    p.drawPolygon(QPolygonF([QPointF(-3, topo + 5), QPointF(3, topo + 5), QPointF(5.5, topo + 17),
                             QPointF(0, topo + 21), QPointF(-5.5, topo + 17)]))   # ponta
    p.setPen(QPen(escura, 1.5))
    p.drawLine(QPointF(-4, topo + 10), QPointF(4, topo + 8))                   # listra
    p.restore()


def draw_zzz(p, cx, cy, now, cor=EYE):
    """Zs subindo do canto de cima do corpo, crescendo, balançando e sumindo."""
    for i in range(ZZZ_COUNT):
        t = ((now / ZZZ_PERIOD) + i / ZZZ_COUNT) % 1.0     # 0 nasce ... 1 some
        x = cx + BODY_W * 0.32 + 34 * t + 5 * math.sin(t * math.tau * 1.5)
        y = cy - BODY_H * 0.42 - 44 * t       # sobe até ~12 px do topo da janela
        size = 8 + 9 * t
        alpha = int(255 * min(1.0, t * 5) * (1.0 - t) ** 0.6)
        color = QColor(cor)
        color.setAlpha(alpha)
        p.save()
        p.translate(x, y)
        p.rotate(-12 + 10 * math.sin(t * math.tau))
        p.setPen(color)
        p.setFont(QFont("Consolas", int(size), QFont.Bold))
        p.drawText(QRectF(-20, -20, 40, 40), Qt.AlignCenter, "Z")
        p.restore()
