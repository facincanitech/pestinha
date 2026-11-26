"""
TELA DO APARELHO - o que aparece quando você clica no celular (ou no notebook/PC) do pet.

Celular Mapple: moldura de celular, barra de status (hora, moedas e a bateria, que é a energia dele),
tela inicial com papel de parede e ícones. Notebook e PC gamer: a mesma coisa em tela deitada.
Cada app abre dentro da tela, com "‹" para voltar. Botão lateral, Esc ou clique direito: bloqueia (fecha).
"""

import time
from datetime import datetime

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from ..world.celular import desenhar_pera
from .aparelho import Aparelho

APPS = [  # (nome, figura, cor do ícone, ação)
    ("Loja", "🛍️", "#ff7043", "loja"), ("Jogos", "🎮", "#7e57c2", "jogos"),
    ("Paciência", "🃏", "#2e7d32", "paciencia"), ("Rede", "👾", "#1e88e5", "rede"),
    ("Galeria", "🖼️", "#f9a825", "galeria"), ("Memes", "😂", "#ec407a", "rede"),
    ("Desenhar", "🎨", "#26a69a", "desenhar"), ("Casinha", "🏠", "#8d6e63", "casinha"),
    ("Ajustes", "⚙️", "#607d8b", "ajustes"),
]
DOCK = ["Loja", "Jogos", "Rede", "Galeria"]
PAGINAS = {"loja": 0, "jogos": 1, "rede": 2, "galeria": 3}
TITULOS = {"loja": "Loja", "jogos": "Jogos", "rede": "Rede dos pestinhas", "galeria": "Galeria"}

FORMATOS = {   # tamanho da janela e a área da tela dentro dela
    "mapple": ((360, 720), QRectF(14, 14, 332, 692), 40),
    "notebook": ((720, 500), QRectF(34, 26, 652, 400), 8),
    "pc_gamer": ((780, 540), QRectF(30, 26, 720, 430), 6),
}


class Inicio(QWidget):
    """A tela inicial: papel de parede, relógio e os ícones."""
    def __init__(self, tela):
        super().__init__()
        self.tela = tela
        self.setAttribute(Qt.WA_TranslucentBackground)

    def _grade(self):
        w, h = self.width(), self.height()
        deitado = w > h
        colunas = 6 if deitado else 4
        lado = 54 if deitado else 58
        passo_x = (w - 24) / colunas
        topo = 70 if deitado else 190
        posicoes = {}
        for i, (nome, fig, cor, acao) in enumerate(a for a in APPS if a[0] not in DOCK or deitado):
            col, lin = i % colunas, i // colunas
            cx = 12 + passo_x * (col + 0.5)
            posicoes[nome] = (QRectF(cx - lado / 2, topo + lin * (lado + 34), lado, lado), fig, cor, acao)
        if not deitado:
            for i, nome_dock in enumerate(DOCK):
                nome, fig, cor, acao = next(a for a in APPS if a[0] == nome_dock)
                cx = 12 + passo_x * (i + 0.5)
                posicoes["dock:" + nome] = (QRectF(cx - lado / 2, h - lado - 34, lado, lado), fig, cor, acao)
        return posicoes

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect())
        cor = self.tela.app.pet.aparencia.moldura
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, cor.darker(150))
        g.setColorAt(0.55, QColor("#1b1f3a"))
        g.setColorAt(1, cor.darker(260))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, self.tela.raio, self.tela.raio)
        deitado = r.width() > r.height()
        agora = datetime.now()
        if not deitado:
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 54, QFont.Light))
            p.drawText(QRectF(0, 64, r.width(), 76), Qt.AlignCenter, agora.strftime("%H:%M"))
            p.setFont(QFont("Segoe UI", 12, QFont.Bold))
            dias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
            p.drawText(QRectF(0, 140, r.width(), 24), Qt.AlignCenter, f"{dias[agora.weekday()]}, {agora:%d/%m}")
            dock = QRectF(10, r.height() - 112, r.width() - 20, 92)
            p.setBrush(QColor(255, 255, 255, 50))
            p.drawRoundedRect(dock, 26, 26)
        for chave, (ret, fig, cor_icone, _acao) in self._grade().items():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(cor_icone))
            p.drawRoundedRect(ret, 15, 15)
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI Emoji", 24))
            p.drawText(ret, Qt.AlignCenter, fig)
            if not chave.startswith("dock:"):
                p.setFont(QFont("Segoe UI", 9, QFont.Bold))
                p.drawText(QRectF(ret.left() - 14, ret.bottom() + 4, ret.width() + 28, 16), Qt.AlignCenter, chave)
        p.end()

    def mousePressEvent(self, ev):
        for ret, _fig, _cor, acao in self._grade().values():
            if ret.contains(ev.position()):
                self.tela.abrir_app(acao)
                return


class Barra(QWidget):
    """Camada por cima da tela: barra de status e barra de início (não pega cliques)."""
    def __init__(self, tela):
        super().__init__(tela)
        self.tela = tela
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self.tela._barra_de_status(p)
        p.end()


class TelaAparelho(QWidget):
    def __init__(self, app):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.app = app
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.apps = Aparelho(app)                     # o conteúdo dos apps (loja, jogos, rede, galeria)
        paginas = []
        while self.apps.abas.count():
            paginas.append(self.apps.abas.widget(0))
            self.apps.abas.removeTab(0)
        self.pilha = QStackedWidget(self)
        self.inicio = Inicio(self)
        self.pilha.addWidget(self.inicio)
        self.paginas = []
        for pagina in paginas:
            moldura = QWidget()
            v = QVBoxLayout(moldura)
            v.setContentsMargins(10, 34, 10, 22)
            topo = QHBoxLayout()
            voltar = QPushButton("‹")
            voltar.setObjectName("voltar")
            voltar.setFixedSize(40, 34)
            voltar.clicked.connect(self.inicio_)
            topo.addWidget(voltar)
            titulo = QLabel()
            titulo.setObjectName("tituloApp")
            topo.addWidget(titulo, 1)
            v.addLayout(topo)
            v.addWidget(pagina, 1)
            pagina.setVisible(True)                    # o QTabWidget esconde a página ao tirar a aba
            moldura.titulo = titulo
            self.pilha.addWidget(moldura)
            self.paginas.append(moldura)
        self.barra = Barra(self)
        self._arrasto = None
        self.relogio = QTimer(self)
        self.relogio.timeout.connect(self.update)
        self.relogio.timeout.connect(self.inicio.update)
        self.relogio.timeout.connect(lambda: self.barra.update())
        self.relogio.start(1000)
        self.ajustar()

    # ---------------- forma ----------------

    @property
    def formato(self):
        return self.app.carteira.eletronico if self.app.carteira.eletronico in FORMATOS else "mapple"

    def ajustar(self):
        (w, h), tela, self.raio = FORMATOS[self.formato]
        self.setFixedSize(w, h)
        self.area = tela
        self.pilha.setGeometry(tela.toRect())
        self.barra.setGeometry(0, 0, w, h)
        self.barra.raise_()
        escuro = self.formato == "pc_gamer"
        fundo, texto = ("#121318", "#eeeeee") if escuro else ("#f5f5f7", "#1d1d1f")
        self.pilha.setStyleSheet(f"""
            QWidget {{ color: {texto}; font-size: 13px; }}
            QStackedWidget > QWidget {{ background: {fundo}; border-radius: {self.raio}px; }}
            QLabel#tituloApp {{ font-size: 18px; font-weight: bold; }}
            QPushButton {{ border: 1px solid #c7c7cc; border-radius: 10px; padding: 6px 10px; background: transparent; }}
            QPushButton#voltar {{ font-size: 24px; border: 0; padding: 0; color: #0a84ff; }}
            QPushButton:disabled {{ color: #9e9e9e; }}
        """)
        self.inicio.setStyleSheet("background: transparent;")

    # ---------------- navegação ----------------

    def inicio_(self):
        self.pilha.setCurrentWidget(self.inicio)
        self.update()
        self.barra.update()

    def abrir_app(self, acao):
        a = self.app
        if acao in PAGINAS:
            moldura = self.paginas[PAGINAS[acao]]
            moldura.titulo.setText(TITULOS[acao])
            self.apps.atualizar()
            self.pilha.setCurrentWidget(moldura)
        elif acao == "paciencia":
            a.abrir_paciencia()
        elif acao == "desenhar":
            a.menu_desenho()
            a.tray.icon.showMessage(a.nome, "Vou olhar a tela e desenhar!")
        elif acao == "casinha":
            if a.carteira.casa:
                a.casinha_ctl.ir("ordem")
            else:
                a.tray.icon.showMessage(a.nome, "Ainda não tenho casa... tem na Loja!")
        elif acao == "ajustes":
            a.open_settings()
        self.update()

    def mostrar(self):
        self.ajustar()
        self.inicio_()
        self.apps.atualizar()
        self.show()
        self.raise_()
        self.activateWindow()

    # ---------------- desenho da moldura ----------------

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if self.formato == "mapple":
            corpo = QRectF(2, 2, w - 4, h - 4)
            p.setPen(QPen(QColor("#5b5e66"), 2))
            p.setBrush(QColor("#0d0e10"))
            p.drawRoundedRect(corpo, 50, 50)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#3a3c42"))
            p.drawRoundedRect(QRectF(w - 4, 150, 5, 64), 2, 2)          # botão lateral (bloquear)
            p.drawRoundedRect(QRectF(-1, 130, 5, 40), 2, 2)
            p.drawRoundedRect(QRectF(-1, 180, 5, 40), 2, 2)
        else:
            tampa = QRectF(4, 4, w - 8, h - 70 if self.formato == "notebook" else h - 50)
            p.setPen(QPen(QColor("#4a4d52"), 2))
            p.setBrush(QColor("#1a1b1f"))
            p.drawRoundedRect(tampa, 16, 16)
            if self.formato == "notebook":
                base = QRectF(0, h - 64, w, 22)
                p.setBrush(QColor("#c9cdd2"))
                p.drawRoundedRect(base, 8, 8)
            else:
                hue = int(time.time() * 60) % 360
                p.setPen(QPen(QColor.fromHsv(hue, 230, 255), 3))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(tampa.adjusted(2, 2, -2, -2), 14, 14)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#1a1b1f"))
                p.drawRect(QRectF(w / 2 - 30, h - 46, 60, 26))
                p.drawRoundedRect(QRectF(w / 2 - 120, h - 22, 240, 16), 6, 6)
        p.end()

    def _barra_de_status(self, p):
        a, r = self.area, self.area
        cor = QColor("#ffffff") if self.pilha.currentWidget() is self.inicio or self.formato == "pc_gamer" else QColor("#1d1d1f")
        p.setPen(cor)
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(QRectF(a.left() + 26, a.top() + 8, 80, 20), Qt.AlignLeft, datetime.now().strftime("%H:%M"))
        if self.formato == "mapple":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#000000"))
            p.drawRoundedRect(QRectF(r.center().x() - 50, r.top() + 8, 100, 28), 14, 14)     # ilha da câmera
            p.setPen(cor)
        energia = max(0.0, min(1.0, getattr(self.app.drives, "energy", 1.0)))
        bat = QRectF(a.right() - 54, a.top() + 11, 26, 13)
        p.setPen(QPen(cor, 1.4))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(bat, 3, 3)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#34c759") if energia > 0.25 else QColor("#ff3b30"))
        p.drawRoundedRect(QRectF(bat.left() + 2, bat.top() + 2, (bat.width() - 4) * energia, bat.height() - 4), 2, 2)
        p.setPen(cor)
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        p.drawText(QRectF(a.right() - 150, a.top() + 8, 92, 20), Qt.AlignRight, f"🪙 {self.app.carteira.moedas}")
        if self.formato == "mapple":
            p.setPen(Qt.NoPen)
            p.setBrush(cor)
            p.drawRoundedRect(QRectF(a.center().x() - 60, a.bottom() - 12, 120, 5), 2.5, 2.5)   # barra de início
        if self.pilha.currentWidget() is self.inicio and self.formato != "mapple":
            desenhar_pera(p, a.right() - 24, a.bottom() - 26, 9, QColor(255, 255, 255, 120))

    # ---------------- mouse e teclado ----------------

    def mousePressEvent(self, ev):
        pos = ev.position()
        if ev.button() == Qt.RightButton:
            self.hide()
            return
        if self.formato == "mapple" and pos.x() > self.width() - 8 and 150 <= pos.y() <= 214:
            self.hide()                                   # botão lateral: bloqueia
            return
        if self.formato == "mapple" and abs(pos.y() - (self.area.bottom() - 10)) < 12 \
                and abs(pos.x() - self.area.center().x()) < 70:
            self.inicio_()                                 # barra de início
            return
        if ev.button() == Qt.LeftButton:
            self._arrasto = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, ev):
        if self._arrasto is not None:
            self.move(ev.globalPosition().toPoint() - self._arrasto)

    def mouseReleaseEvent(self, _ev):
        self._arrasto = None

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key_Escape:
            self.hide()
        elif ev.key() == Qt.Key_Backspace:
            self.inicio_()
