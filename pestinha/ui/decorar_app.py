"""
DECORAR (app do celular) - muda as cores e os estilos do quarto: parede, chão, cama, sofá e tapete.
Cada troca custa algumas moedinhas. Em cima, a prévia do quarto do jeito que está.
"""

import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..core.economia import ESTILO_PRECO, ESTILOS

FUNDO = QColor("#12131a")
OURO = QColor("#ffc83d")


class DecorarApp(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.rolagem = 0.0
        self.aviso = None
        self._alvos = []
        self._previa = None
        self._previa_em = 0.0
        t = QTimer(self)
        t.timeout.connect(self.update)
        t.start(300)

    def _imagem_previa(self):
        agora = time.monotonic()
        if self._previa is None or agora - self._previa_em > 1.0:
            casinha = self.app.casinha_ctl.casinha
            self._previa = casinha.grab().toImage()
            self._previa_em = agora
        return self._previa

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), FUNDO)
        self._alvos = []
        p.translate(0, -self.rolagem)
        y = 6.0
        if not self.app.carteira.casa:
            p.setPen(QColor("#c9cbd6"))
            p.setFont(QFont("Segoe UI", 13, QFont.Bold))
            p.drawText(QRectF(16, 40, self.width() - 32, 120), Qt.AlignCenter | Qt.TextWordWrap,
                       "Ainda não tem casa para decorar.\nCompre a barraca ou o quarto na Loja.")
            p.end()
            return
        img = self._imagem_previa()
        if not img.isNull():
            alvo = QRectF(10, y, self.width() - 20, (self.width() - 20) * img.height() / max(1, img.width()))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#1e2130"))
            p.drawRoundedRect(alvo.adjusted(-4, -4, 4, 4), 14, 14)
            p.drawImage(alvo, img)
            y = alvo.bottom() + 14
        p.setPen(QColor("#9aa0b8"))
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        p.drawText(QRectF(14, y, self.width() - 28, 18), Qt.AlignLeft,
                   f"Cada troca custa 🪙 {ESTILO_PRECO} · você tem 🪙 {self.app.carteira.moedas}")
        y += 26
        estilo = self.app.carteira.estilo
        for chave, (nome, opcoes) in ESTILOS.items():
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 12, QFont.Bold))
            p.drawText(QRectF(14, y, self.width() - 28, 20), Qt.AlignLeft, nome)
            y += 24
            if opcoes[0].startswith("#"):
                for k, cor in enumerate(opcoes):
                    centro = QPointF(30 + k * 46, y + 18)
                    escolhida = estilo.get(chave) == cor
                    p.setPen(QPen(OURO, 3) if escolhida else QPen(QColor("#2c2f3d"), 2))
                    p.setBrush(QColor(cor))
                    p.drawEllipse(centro, 16, 16)
                    self._alvos.append((QRectF(centro.x() - 18, centro.y() - 18, 36, 36), chave, cor))
                y += 46
            else:
                x = 14.0
                for valor in opcoes:
                    larg = 18 + len(valor) * 8
                    if x + larg > self.width() - 10:
                        x, y = 14.0, y + 38
                    r = QRectF(x, y + 2, larg, 30)
                    escolhida = estilo.get(chave) == valor
                    p.setPen(QPen(OURO, 2) if escolhida else Qt.NoPen)
                    p.setBrush(QColor("#2b2f44") if escolhida else QColor("#1e2130"))
                    p.drawRoundedRect(r, 15, 15)
                    p.setPen(QColor("#ffffff"))
                    p.setFont(QFont("Segoe UI", 10, QFont.Bold))
                    p.drawText(r, Qt.AlignCenter, valor)
                    self._alvos.append((r, chave, valor))
                    x += larg + 8
                y += 44
        self._altura = y + 10
        p.resetTransform()
        if self.aviso and time.monotonic() < self.aviso[1]:
            r = QRectF(20, self.height() - 60, self.width() - 40, 40)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 210))
            p.drawRoundedRect(r, 20, 20)
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 11, QFont.Bold))
            p.drawText(r, Qt.AlignCenter, self.aviso[0])
        p.end()

    def wheelEvent(self, ev):
        maximo = max(0.0, getattr(self, "_altura", 0) - self.height())
        self.rolagem = min(maximo, max(0.0, self.rolagem - ev.angleDelta().y() / 2))
        self.update()

    def mousePressEvent(self, ev):
        pos = ev.position()
        pos.setY(pos.y() + self.rolagem)
        for r, chave, valor in self._alvos:
            if r.contains(pos):
                c = self.app.carteira
                if c.estilo.get(chave) == valor:
                    return
                if c.mudar_estilo(chave, valor):
                    self.app.casinha_ctl.casinha.update()
                    self._previa = None
                    self.aviso = (f"Pronto! -{ESTILO_PRECO} moedas", time.monotonic() + 1.6)
                else:
                    self.aviso = ("Moedas insuficientes", time.monotonic() + 1.6)
                self.update()
                return
