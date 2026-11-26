"""
CELULAR - o celular Mapple do pet, deitado na tela como o notebook: você vê a parte de trás
(preta, com a pera mordida e as câmeras). Clique nele para abrir a tela (ui/tela_aparelho.py).
Arrasta-se segurando o botão; a posição é lembrada como a dos painéis.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen

from .arrastavel import FloatingWidget

W, H = 74, 136


def _posicao_padrao():
    tela = QGuiApplication.primaryScreen().availableGeometry()
    return (tela.right() - W - 210, tela.bottom() - H - 6)


def desenhar_pera(p, cx, cy, s, cor):
    """A pera mordida da Mapple."""
    p.setPen(Qt.NoPen)
    p.setBrush(cor)
    corpo = QPainterPath()
    corpo.addEllipse(QPointF(cx, cy + s * 0.35), s * 0.55, s * 0.6)
    corpo.addEllipse(QPointF(cx, cy - s * 0.2), s * 0.36, s * 0.42)
    mordida = QPainterPath()
    mordida.addEllipse(QPointF(cx + s * 0.62, cy + s * 0.1), s * 0.26, s * 0.26)
    p.drawPath(corpo.subtracted(mordida))
    p.setPen(QPen(cor, max(1.5, s * 0.08), Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(cx, cy - s * 0.6), QPointF(cx + s * 0.08, cy - s * 0.85))
    folha = QPainterPath(QPointF(cx + s * 0.08, cy - s * 0.78))
    folha.quadTo(cx + s * 0.4, cy - s * 1.0, cx + s * 0.45, cy - s * 0.72)
    folha.quadTo(cx + s * 0.25, cy - s * 0.62, cx + s * 0.08, cy - s * 0.78)
    p.setPen(Qt.NoPen)
    p.drawPath(folha)


class Celular(FloatingWidget):
    def __init__(self, app, abrir):
        super().__init__(app, "celular", f"Celular do {app.nome}", (W, H), (W, H), _posicao_padrao())
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setToolTip("celular Mapple: clique para abrir · arraste para mudar de lugar")
        self.abrir = abrir
        self._apertou = None

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        corpo = QRectF(3, 3, W - 8, H - 8)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 70))
        p.drawRoundedRect(corpo.translated(2, 3), 14, 14)
        g = QLinearGradient(corpo.topLeft(), corpo.bottomRight())
        g.setColorAt(0, QColor("#2b2d31"))
        g.setColorAt(1, QColor("#0e0f11"))
        p.setPen(QPen(QColor("#5b5e66"), 1.6))
        p.setBrush(g)
        p.drawRoundedRect(corpo, 14, 14)
        # módulo de câmeras
        mod = QRectF(9, 9, 30, 30)
        p.setPen(QPen(QColor("#4a4d54"), 1))
        p.setBrush(QColor("#1c1d20"))
        p.drawRoundedRect(mod, 9, 9)
        for cx, cy in ((17, 17), (17, 31), (31, 24)):
            p.setPen(QPen(QColor("#5d6068"), 1.4))
            p.setBrush(QColor("#08090a"))
            p.drawEllipse(QPointF(cx, cy), 5.2, 5.2)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(90, 120, 200, 140))
            p.drawEllipse(QPointF(cx - 1.2, cy - 1.2), 1.6, 1.6)
        p.setBrush(QColor("#f6e7a8"))
        p.drawEllipse(QPointF(31, 14), 2, 2)                   # flash
        desenhar_pera(p, corpo.center().x(), corpo.center().y() + 8, 17, QColor("#b7bbc4"))
        p.setPen(QColor("#6d7079"))
        p.setFont(QFont("Segoe UI", 6, QFont.Bold))
        p.drawText(QRectF(corpo.left(), corpo.bottom() - 18, corpo.width(), 12), Qt.AlignCenter, "Mapple")
        p.end()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._apertou = ev.globalPosition()
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):
        clique = (self._apertou is not None and ev.button() == Qt.LeftButton
                  and (ev.globalPosition() - self._apertou).manhattanLength() < 5)
        self._apertou = None
        super().mouseReleaseEvent(ev)
        if clique:
            self.abrir()
