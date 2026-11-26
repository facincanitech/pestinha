"""
CASINHA - o quarto do pet: uma casinha arrastável, em corte, com cama, TV e notebook.

Só desenho e mouse. Quem decide entrar e sair é mind/casinha_ctl.py.
Com ele dentro, a janela do pet some e ele aparece aqui, pequenininho:
dormindo na cama, vendo TV ou mexendo no notebook.
A TV passa o modelo que ele está tentando desenhar (ver world/desenho.py).
"""

import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen, QPolygonF

from ..body.desenho_rosto import draw_face, draw_zzz
from .arrastavel import FloatingWidget, save_position

W, H = 300, 220                 # tamanho do desenho; a janela é isso vezes TAMANHO
TAMANHO = 0.62
ESCALA_PET = 0.36
PORTA = QRectF(254, 128, 30, 62)          # na parede da direita
LUGARES = {                                # onde ele fica em cada atividade (centro do corpo)
    "cama": QPointF(72, 150),
    "tv": QPointF(168, 168),
    "eletronico": QPointF(231, 158),
}


LW, LH = int(W * TAMANHO), int(H * TAMANHO)


def _posicao_padrao():
    tela = QGuiApplication.primaryScreen().availableGeometry()
    return (tela.left() + 30, tela.bottom() - LH + 1)


class Casinha(FloatingWidget):
    """A casinha na tela. `app` dá o estado do pet (rosto, emoção, aparência)."""

    def __init__(self, app, ctl):
        super().__init__(app, "casinha", f"Casinha do {app.nome}", (LW, LH), (LW, LH), _posicao_padrao())
        self.ctl = ctl
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setToolTip("casinha: arraste para mudar de lugar · botão direito para o menu")
        self._tv_id = None
        self._tv_img = None
        self._apertou = None
        self.relogio = QTimer(self)
        self.relogio.timeout.connect(self.update)
        self.relogio.start(70)

    # ---------------- posição ----------------

    def porta_global(self):
        """Ponto da porta (no chão) em coordenadas da tela."""
        return self.x() + PORTA.center().x() * TAMANHO, self.y() + PORTA.bottom() * TAMANHO

    def encostar(self, salvar=False):
        """Fica sempre em pé em cima da barra de tarefas (o fundo da área útil da tela em que está)."""
        centro = self.geometry().center()
        tela = QGuiApplication.screenAt(centro) or QGuiApplication.primaryScreen()
        g = tela.availableGeometry()
        x = min(max(self.x(), g.left()), g.right() - self.width() + 1)
        self.move(x, g.bottom() - self.height() + 1 + int(4 * TAMANHO))   # a sombra do chão passa da borda
        if salvar:
            save_position(self.app.paths.panels, self.key, self.x(), self.y())

    def showEvent(self, event):
        super().showEvent(event)
        self.encostar()

    # ---------------- TV ----------------

    def _imagem_da_tv(self):
        d = getattr(self.app.mischief, "desenhista", None)
        ref = getattr(d, "ref", None) if d else None
        if not ref:
            return None
        if ref["id"] != self._tv_id:
            img = QImage(str(d._pasta_ref(ref["id"]) / "modelo.png"))
            self._tv_img = None if img.isNull() else img.scaled(78, 50, Qt.KeepAspectRatioByExpanding,
                                                                 Qt.SmoothTransformation)
            self._tv_id = ref["id"]
        return self._tv_img

    # ---------------- desenho ----------------

    def _tem(self, item):
        return self.ctl.carteira.tem(item)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(TAMANHO, TAMANHO)
        agora = time.monotonic()
        casa = self.ctl.carteira.casa or "casinha"
        hora = time.localtime().tm_hour
        noite = hora >= 19 or hora < 6

        p.setPen(Qt.NoPen)
        if casa != "barraca":
            p.setBrush(QColor(0, 0, 0, 50))
            p.drawRect(QRectF(14, 56, W - 20, H - 58))
        if casa == "papelao":
            self._caixa(p)
        elif casa == "barraca":
            self._barraca(p)
        else:
            self._paredes(p, casa)
            self._janela(p, noite)
            self._cortina(p)
        chao = QRectF(10, H - 42, W - 20, 38)
        p.setBrush(QColor({"papelao": "#c9a06b", "barraca": "#6aa84f", "praia": "#f1d9a6",
                           "mansao": "#6d4c41"}.get(casa, "#a8734a")))
        p.drawRect(chao)
        p.setPen(QPen(QColor("#8d5d38"), 1))
        for x in range(20, W - 10, 34):
            p.drawLine(QPointF(x, chao.top()), QPointF(x, chao.bottom()))
        p.setPen(Qt.NoPen)

        if self._tem("tapete"):
            p.setBrush(QColor("#5f8fd6"))
            p.drawEllipse(QRectF(120, H - 40, 100, 22))
        if self._tem("estante") and casa not in ("papelao", "barraca"):
            p.setBrush(QColor("#8d5b33"))
            for y in (86, 104):
                p.drawRect(QRectF(88, y, 48, 3))
            cores = ["#e53935", "#1e88e5", "#43a047", "#fdd835", "#8e24aa", "#fb8c00"]
            for k in range(6):
                p.setBrush(QColor(cores[k]))
                p.drawRect(QRectF(90 + k * 7, 74 + (k % 2) * 2, 5, 12 - (k % 2) * 2))
                p.setBrush(QColor(cores[(k + 3) % 6]))
                p.drawRect(QRectF(92 + k * 7, 92, 5, 12))
        if self._tem("luminaria"):
            p.setBrush(QColor("#6b6f75"))
            p.drawRect(QRectF(130, 120, 3, 56))
            p.setBrush(QColor("#ffe082") if noite else QColor("#fff3cf"))
            p.drawPolygon(QPolygonF([QPointF(122, 120), QPointF(141, 120), QPointF(137, 106), QPointF(126, 106)]))
            if noite:
                p.setBrush(QColor(255, 224, 130, 45))
                p.drawEllipse(QPointF(131, 135), 34, 26)

        if self._tem("cama"):
            p.setBrush(QColor("#7a4b2a"))
            p.drawRect(QRectF(24, 150, 70, 26))
            p.drawRect(QRectF(22, 128, 8, 48))
            p.setBrush(QColor("#ffffff"))
            p.drawRoundedRect(QRectF(32, 140, 24, 12), 5, 5)
            p.setBrush(QColor("#e55b5b"))
            p.drawRoundedRect(QRectF(54, 142, 42, 14), 4, 4)
        else:
            p.setBrush(QColor("#9e9e9e"))                    # sem cama: dorme num paninho
            p.drawRoundedRect(QRectF(30, 168, 60, 9), 4, 4)

        if self._tem("fliperama"):
            p.setBrush(QColor("#283593"))
            p.drawRoundedRect(QRectF(98, 116, 26, 62), 3, 3)
            p.setBrush(QColor.fromHsv(int(agora * 80) % 360, 200, 255))
            p.drawRect(QRectF(102, 122, 18, 14))
            p.setBrush(QColor("#ff5252"))
            p.drawEllipse(QPointF(106, 144), 2.5, 2.5)
            p.setBrush(QColor("#ffeb3b"))
            p.drawEllipse(QPointF(116, 144), 2.5, 2.5)
        if self._tem("poltrona"):
            p.setBrush(QColor("#6a1b9a"))
            p.drawRoundedRect(QRectF(100, 154, 30, 24), 6, 6)
            p.setBrush(QColor("#8e24aa"))
            p.drawRoundedRect(QRectF(104, 162, 22, 10), 4, 4)

        if self._tem("tv"):
            self._tv(p, agora)
            if self._tem("console") or self._tem("console_retro"):
                p.setBrush(QColor("#eceff1") if self._tem("console") else QColor("#9e9e9e"))
                p.drawRoundedRect(QRectF(174, 140, 24, 8), 2, 2)
            if self._tem("caixa_som"):
                p.setBrush(QColor("#263238"))
                p.drawRoundedRect(QRectF(176, 78, 20, 13), 3, 3)
                p.setBrush(QColor("#90a4ae"))
                p.drawEllipse(QPointF(182, 84.5), 3, 3)
                p.drawEllipse(QPointF(190, 84.5), 3, 3)
        if self._tem("planta"):
            p.setBrush(QColor("#b5653b"))
            p.drawRect(QRectF(146, 80, 12, 12) if self._tem("tv") else QRectF(96, 160, 16, 16))
            base = QPointF(152, 80) if self._tem("tv") else QPointF(104, 160)
            p.setBrush(QColor("#43a047"))
            for dx, dy in ((-6, -8), (6, -10), (0, -16), (-2, -4), (8, -2)):
                p.drawEllipse(QPointF(base.x() + dx, base.y() + dy), 7, 5)
        if self._tem("sofa"):
            p.setBrush(QColor("#00897b"))
            p.drawRoundedRect(QRectF(138, 158, 70, 22), 8, 8)
            p.setBrush(QColor("#26a69a"))
            p.drawRoundedRect(QRectF(144, 164, 58, 10), 5, 5)

        if casa not in ("papelao", "barraca"):
            p.setBrush(QColor("#6d4325"))
            p.drawRoundedRect(PORTA, 4, 4)
            p.setBrush(QColor("#f2c14e"))
            p.drawEllipse(QPointF(PORTA.left() + 6, PORTA.center().y() + 4), 2.5, 2.5)

        if self.ctl.dentro:
            self._pet(p, agora)
        self._eletronico(p, agora)
        p.end()

    def _caixa(self, p):
        """Caixa de papelão: aberta na frente, com as abas para cima."""
        p.setBrush(QColor("#d6a76c"))
        p.drawRect(QRectF(10, 70, W - 20, H - 74))
        p.setBrush(QColor("#c4935a"))
        p.drawPolygon(QPolygonF([QPointF(10, 70), QPointF(40, 40), QPointF(120, 50), QPointF(90, 70)]))
        p.drawPolygon(QPolygonF([QPointF(W - 10, 70), QPointF(W - 30, 36), QPointF(W - 120, 46), QPointF(W - 90, 70)]))
        p.setPen(QPen(QColor("#9c6f3c"), 2))
        p.drawText(QRectF(20, 80, 140, 20), Qt.AlignLeft, "FRÁGIL ↑↑")
        p.setPen(Qt.NoPen)

    def _paredes(self, p, casa):
        telhado = QPainterPath(QPointF(2, 58))
        telhado.lineTo(W / 2, 4)
        telhado.lineTo(W - 2, 58)
        telhado.closeSubpath()
        telha = {"casa": "#5d4037", "praia": "#00838f", "mansao": "#1a237e"}.get(casa, "#b5523b")
        p.setBrush(QColor(telha))
        p.drawPath(telhado)
        p.setPen(QPen(QColor("#3e2723") if casa == "casa" else QColor("#8c3b28"), 2))
        for i in range(1, 4):
            y = 4 + i * 13
            meia = (y - 4) / 54 * (W / 2 - 2)
            p.drawLine(QPointF(W / 2 - meia, y), QPointF(W / 2 + meia, y))
        p.setPen(Qt.NoPen)
        if casa == "casa":
            p.setBrush(QColor("#c8745a"))
            p.drawRect(QRectF(10, 52, W - 20, H - 56))
            p.setPen(QPen(QColor("#a85a43"), 1))
            for row, y in enumerate(range(56, H - 42, 10)):
                p.drawLine(QPointF(10, y), QPointF(W - 10, y))
                for x in range(10 + (row % 2) * 12, W - 10, 24):
                    p.drawLine(QPointF(x, y), QPointF(x, y + 10))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 240, 220, 120))
            p.drawRect(QRectF(14, 56, W - 28, H - 98))
        elif casa == "mansao":
            p.setBrush(QColor("#f5ecd7"))
            p.drawRect(QRectF(10, 52, W - 20, H - 56))
            p.setBrush(QColor("#ffd54f"))
            p.drawRect(QRectF(10, 52, W - 20, 5))
            p.setBrush(QColor("#e8dcc0"))
            for x in (14, W - 26):
                p.drawRect(QRectF(x, 57, 12, H - 99))
            p.setBrush(QColor("#c5a14a"))
            p.drawEllipse(QPointF(W / 2, 30), 8, 8)
        elif casa == "praia":
            p.setBrush(QColor("#d7f1f5"))
            p.drawRect(QRectF(10, 52, W - 20, H - 56))
            p.setBrush(QColor("#b2e3ec"))
            for x in range(18, W - 18, 22):
                p.drawRect(QRectF(x, 52, 4, H - 92))
        else:
            p.setBrush(QColor("#f3e2c7"))
            p.drawRect(QRectF(10, 52, W - 20, H - 56))
            p.setBrush(QColor("#ead2ad"))
            for x in range(18, W - 18, 22):
                p.drawRect(QRectF(x, 52, 2, H - 92))

    def _barraca(self, p):
        """Barraca de camping, aberta na frente."""
        lona = QPainterPath(QPointF(6, H - 40))
        lona.lineTo(W / 2, 22)
        lona.lineTo(W - 6, H - 40)
        lona.closeSubpath()
        p.setBrush(QColor("#ef6c00"))
        p.drawPath(lona)
        dentro = QPainterPath(QPointF(40, H - 40))
        dentro.lineTo(W / 2, 46)
        dentro.lineTo(W - 40, H - 40)
        dentro.closeSubpath()
        p.setBrush(QColor("#ffcc80"))
        p.drawPath(dentro)
        p.setPen(QPen(QColor("#6d4c41"), 3))
        p.drawLine(QPointF(W / 2, 14), QPointF(W / 2, 24))
        p.setPen(Qt.NoPen)

    def _cortina(self, p):
        """Cortina na janela (a equipada na loja)."""
        qual = self.ctl.carteira.cortina
        if not qual:
            return
        cor = {"cortina_azul": "#1e88e5", "cortina_vermelha": "#c62828", "cortina_listrada": "#ffffff",
               "cortina_estrelas": "#283593"}.get(qual, "#1e88e5")
        jan = QRectF(26, 70, 54, 40)
        for lado in (0, 1):
            x0 = jan.left() - 6 if lado == 0 else jan.right() - 12
            pano = QPainterPath(QPointF(x0, jan.top() - 6))
            pano.lineTo(x0 + 18, jan.top() - 6)
            pano.quadTo(x0 + (4 if lado == 0 else 14), jan.center().y(), x0 + (8 if lado == 0 else 10), jan.bottom() + 6)
            pano.lineTo(x0, jan.bottom() + 6)
            pano.closeSubpath()
            p.setBrush(QColor(cor))
            p.drawPath(pano)
            if qual == "cortina_listrada":
                p.setBrush(QColor("#e53935"))
                for k in range(0, 50, 10):
                    p.drawRect(QRectF(x0, jan.top() - 6 + k, 18, 4))
            elif qual == "cortina_estrelas":
                p.setBrush(QColor("#ffeb3b"))
                for k in range(3):
                    p.drawEllipse(QPointF(x0 + 6 + (k % 2) * 6, jan.top() + 4 + k * 14), 1.8, 1.8)
        p.setBrush(QColor("#6d4c41"))
        p.drawRect(QRectF(jan.left() - 10, jan.top() - 9, jan.width() + 20, 4))

    def _janela(self, p, noite):
        jan = QRectF(26, 70, 54, 40)
        p.setBrush(QColor("#ffffff"))
        p.drawRect(jan.adjusted(-3, -3, 3, 3))
        p.setBrush(QColor("#1b2747") if noite else QColor("#9fd8f2"))
        p.drawRect(jan)
        p.setBrush(QColor("#fff4c2") if noite else QColor("#ffd23f"))
        p.drawEllipse(QPointF(jan.right() - 12, jan.top() + 11), 6, 6)
        p.setBrush(QColor("#ffffff"))
        p.drawRect(QRectF(jan.center().x() - 1, jan.top(), 2, jan.height()))
        p.drawRect(QRectF(jan.left(), jan.center().y() - 1, jan.width(), 2))

    def _tv(self, p, agora):
        p.setBrush(QColor("#6b6f75"))
        p.drawRect(QRectF(150, 150, 70, 8))
        p.drawRect(QRectF(160, 158, 6, 18))
        p.drawRect(QRectF(204, 158, 6, 18))
        tv = QRectF(144, 92, 82, 56)
        p.setBrush(QColor("#22252a"))
        p.drawRoundedRect(tv, 5, 5)
        tela = tv.adjusted(4, 4, -4, -4)
        img = self._imagem_da_tv()
        if img is not None:
            p.save()
            p.setClipRect(tela)
            p.drawImage(QPointF(tela.center().x() - img.width() / 2, tela.center().y() - img.height() / 2), img)
            p.restore()
        else:
            cores = ["#ffffff", "#fdd835", "#4fc3f7", "#7cb342", "#f06292", "#e53935", "#1e5bd8"]
            largura = tela.width() / len(cores)
            desloca = int(agora * 2) % len(cores) if self.ctl.dentro and not self.app.asleep else 0
            for i in range(len(cores)):
                p.setBrush(QColor(cores[(i + desloca) % len(cores)]))
                p.drawRect(QRectF(tela.left() + i * largura, tela.top(), largura + 0.5, tela.height()))
        if not (self.ctl.dentro and self.ctl.atividade == "tv") or self.app.asleep:
            p.setBrush(QColor(0, 0, 0, 150))
            p.drawRect(tela)

    def _eletronico(self, p, agora):
        """O eletrônico equipado, na frente dele: celular Mapple, notebook ou PC gamer."""
        usando = self.ctl.dentro and self.ctl.atividade == "eletronico" and not self.app.asleep
        qual = self.ctl.carteira.eletronico
        if qual == "pc_gamer":
            p.setBrush(QColor("#4e342e"))
            p.drawRect(QRectF(196, 172, 56, 6))
            p.setBrush(QColor("#212121"))
            p.drawRect(QRectF(240, 140, 12, 32))
            hue = int(agora * 90) % 360
            p.setBrush(QColor.fromHsv(hue, 220, 255) if usando else QColor("#37474f"))
            p.drawRect(QRectF(242, 144, 8, 3))
            p.setBrush(QColor("#212121"))
            p.drawRoundedRect(QRectF(200, 136, 36, 26), 2, 2)
            p.setBrush(QColor.fromHsv((hue + 120) % 360, 160, 255) if usando else QColor("#37474f"))
            p.drawRect(QRectF(203, 139, 30, 20))
            p.setBrush(QColor("#212121"))
            p.drawRect(QRectF(215, 162, 6, 10))
        elif qual == "notebook":
            p.setBrush(QColor("#8d6e63"))
            p.drawRect(QRectF(212, 178, 36, 6))
            p.setBrush(QColor("#3b3e41"))
            p.drawRoundedRect(QRectF(218, 160, 26, 19), 3, 3)
            p.setBrush(QColor("#63e56f") if usando else QColor("#4a4d50"))
            p.drawRect(QRectF(221, 163, 20, 13))
        elif usando:
            # celular Mapple na mão dele: a pera mordida atrás
            pos = LUGARES["eletronico"]
            p.setBrush(QColor("#eceff1"))
            p.drawRoundedRect(QRectF(pos.x() - 7, pos.y() + 2, 14, 22), 3, 3)
            p.setBrush(QColor("#9ccc65"))
            p.drawEllipse(QPointF(pos.x(), pos.y() + 15), 3.2, 4.2)
            p.drawEllipse(QPointF(pos.x(), pos.y() + 10.5), 2.2, 2.4)
            p.setBrush(QColor("#eceff1"))
            p.drawEllipse(QPointF(pos.x() + 3.2, pos.y() + 13), 1.8, 1.8)

    def _pet(self, p, agora):
        st = self.app.pet_state
        dormindo = self.app.asleep
        atividade = "cama" if dormindo else self.ctl.atividade
        pos = LUGARES.get(atividade, LUGARES["tv"])
        p.save()
        p.translate(pos)
        p.scale(ESCALA_PET, ESCALA_PET)
        if atividade == "cama":
            p.rotate(-8)
        elif atividade == "eletronico":
            p.rotate(1.5 * math.sin(agora * math.tau * 2.4))
        else:
            p.translate(0, -abs(math.sin(agora * 1.3)) * 3)
        olhar = {"tv": (0.0, -0.4), "eletronico": (0.6, 0.4)}.get(atividade, st.gaze)
        piscada = 0.08 if (agora % 4.2) < 0.12 else 1.0
        emocao = "dormindo" if dormindo else st.emotion
        draw_face(p, st.shape, olhar, piscada, emocao, carinho=st.feliz_fechado(), aparencia=self.app.pet.aparencia)
        p.restore()
        if dormindo:
            p.save()
            p.translate(pos)
            p.scale(ESCALA_PET * 1.4, ESCALA_PET * 1.4)
            draw_zzz(p, 0, 0, agora, self.app.pet.aparencia.olho)
            p.restore()

    # ---------------- mouse ----------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._apertou = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Arrasta só para os lados: ela continua em cima da barra."""
        if self._grab is not None:
            self.move(event.globalPosition().toPoint().x() - self._grab.x(), self.y())

    def mouseReleaseEvent(self, event):
        clique = (self._apertou is not None and event.button() == Qt.LeftButton
                  and (event.position() - self._apertou).manhattanLength() < 5)
        pos = event.position() / TAMANHO
        self._apertou = None
        super().mouseReleaseEvent(event)
        self.encostar(salvar=True)
        if clique and self.ctl.dentro:
            alvo = LUGARES.get("cama" if self.app.asleep else self.ctl.atividade, LUGARES["tv"])
            if math.hypot(pos.x() - alvo.x(), pos.y() - alvo.y()) < 30:
                self.ctl.clicou_no_pet()
            elif PORTA.contains(pos):
                self.ctl.sair("porta")

    def contextMenuEvent(self, event):
        self.ctl.menu(event.globalPos())
