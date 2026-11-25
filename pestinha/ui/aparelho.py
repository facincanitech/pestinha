"""
APARELHO - o celular Mapple (depois notebook, depois PC gamer) do pet: loja, jogos, rede e galeria.

Tudo que mexe na rede roda em segundo plano; a resposta volta para a tela por um sinal do Qt.
Postar imagem na rede pede sempre a sua confirmação (as imagens vêm da sua tela).
"""

import time
from datetime import datetime

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QCheckBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox,
                               QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget)

from ..core.economia import CATALOGO, CATEGORIAS
from ..core.ppt import JOGADAS, Leitor
from ..core.emotion import PRIORITY
from ..rede import SITE
from ..world.meme import fazer_meme, memes_feitos

TAMANHOS = {"mapple": (340, 600), "notebook": (600, 440), "pc_gamer": (700, 500)}
NOMES = {"mapple": "Mapple 🍐", "notebook": "Notebook", "pc_gamer": "PC gamer"}
ESTILO = {
    "mapple": "#f5f5f7",
    "notebook": "#e9eef3",
    "pc_gamer": "#14151a",
}


class Ponte(QObject):
    """Leva respostas da rede (outra thread) para a tela."""
    chegou = Signal(object)


class Aparelho(QWidget):
    def __init__(self, app):
        super().__init__(None, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.app = app
        self.ponte = Ponte()
        self.ponte.chegou.connect(lambda fn: fn())
        self.leitor = Leitor(app.pet_paths.base / "ppt.json")
        self.meme_atual = None
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(10, 10, 10, 10)
        self.titulo = QLabel()
        self.titulo.setObjectName("titulo")
        self.saldo = QLabel()
        self.saldo.setObjectName("saldo")
        topo = QHBoxLayout()
        topo.addWidget(self.titulo)
        topo.addStretch(1)
        topo.addWidget(self.saldo)
        raiz.addLayout(topo)
        self.evento = QLabel()
        self.evento.setObjectName("evento")
        self.evento.setWordWrap(True)
        raiz.addWidget(self.evento)
        self.abas = QTabWidget()
        raiz.addWidget(self.abas, 1)
        self.abas.addTab(self._aba_loja(), "Loja")
        self.abas.addTab(self._aba_jogos(), "Jogos")
        self.abas.addTab(self._aba_rede(), "Rede")
        self.abas.addTab(self._aba_galeria(), "Galeria")
        self.abas.currentChanged.connect(lambda _i: self.atualizar())
        self.atualizar()

    def _depois(self, fn):
        """Agenda `fn` na thread da tela (chamado da thread da rede)."""
        self.ponte.chegou.emit(fn)

    # ---------------- geral ----------------

    def atualizar(self):
        c = self.app.carteira
        qual = c.eletronico
        self.setWindowTitle(f"{NOMES[qual]} do {self.app.nome}")
        self.resize(*TAMANHOS[qual])
        fundo = ESTILO[qual]
        texto = "#f0f0f0" if qual == "pc_gamer" else "#1d1d1f"
        borda = "#ff2bd6" if qual == "pc_gamer" else "#c7c7cc"
        self.setStyleSheet(f"""
            QWidget {{ background: {fundo}; color: {texto}; font-size: 13px; }}
            QLabel#titulo {{ font-size: 18px; font-weight: bold; }}
            QLabel#saldo {{ font-size: 16px; font-weight: bold; color: #b8860b; }}
            QLabel#evento {{ color: #d84315; font-weight: bold; }}
            QPushButton {{ border: 1px solid {borda}; border-radius: 10px; padding: 6px 10px; background: transparent; }}
            QPushButton:disabled {{ color: #9e9e9e; }}
            QTabWidget::pane {{ border: 1px solid {borda}; border-radius: 12px; }}
        """)
        self.titulo.setText(f"{NOMES[qual]} · {self.app.nome}")
        self.saldo.setText(f"{c.moedas} moedas")
        if time.time() < c.dobro_ate:
            self.evento.setText(f"EVENTO: moedas em dobro até {datetime.fromtimestamp(c.dobro_ate):%H:%M}!")
            self.evento.show()
        else:
            self.evento.hide()
        self._preencher_loja()
        self._atualizar_placar()
        self._preencher_galeria()
        self._atualizar_rede()

    # ---------------- loja ----------------

    def _aba_loja(self):
        area = QScrollArea()
        area.setWidgetResizable(True)
        self.loja = QWidget()
        self.loja_layout = QVBoxLayout(self.loja)
        area.setWidget(self.loja)
        return area

    def _preencher_loja(self):
        while self.loja_layout.count():
            item = self.loja_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        c = self.app.carteira
        for cat, titulo in CATEGORIAS.items():
            cab = QLabel(f"<b>{titulo}</b>")
            self.loja_layout.addWidget(cab)
            itens = sorted(((i, d) for i, d in CATALOGO.items() if d[0] == cat), key=lambda x: (x[1][3], x[1][2]))
            for item, (_cat, nome, preco, _nivel) in itens:
                linha = QWidget()
                h = QHBoxLayout(linha)
                h.setContentsMargins(4, 0, 4, 0)
                h.addWidget(QLabel(nome), 1)
                if c.tem(item):
                    usando = c.equipado.get(cat) == item
                    if cat == "movel":
                        b = QPushButton("Na casa")
                        b.setEnabled(False)
                    else:
                        b = QPushButton("Tirar" if usando and cat == "chapeu" else ("Usando" if usando else "Usar"))
                        b.setEnabled(not usando or cat == "chapeu")
                        b.clicked.connect(lambda _=False, i=item: self._usar(i))
                else:
                    b = QPushButton(f"{preco} moedas")
                    b.setEnabled(c.pode_comprar(item))
                    b.clicked.connect(lambda _=False, i=item: self._comprar(i))
                h.addWidget(b)
                self.loja_layout.addWidget(linha)
        self.loja_layout.addStretch(1)

    def _comprar(self, item):
        c = self.app.carteira
        primeira_casa = CATALOGO[item][0] == "casa" and not c.casa
        if c.comprar(item):
            self.app.casinha_ctl.aplicar_progresso()
            self.app.emotion.force("feliz", 4.0, priority=PRIORITY.get("carinho", 15))
            if primeira_casa:
                self.app.tray.icon.showMessage(self.app.nome, "Agora eu tenho uma casa!")
            self.app.update_visibility()
        self.atualizar()

    def _usar(self, item):
        if self.app.carteira.equipar(item):
            self.app.casinha_ctl.aplicar_progresso()
            self.app.update_visibility()
        self.atualizar()

    # ---------------- jogos ----------------

    def _aba_jogos(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("<b>Pedra, papel e tesoura</b><br>Ele aprende o seu jeito de jogar. "
                           "Vitória sua: 12 moedas, empate: 5, derrota: 3."))
        h = QHBoxLayout()
        for j in JOGADAS:
            b = QPushButton(j.capitalize())
            b.setMinimumHeight(44)
            b.clicked.connect(lambda _=False, jj=j: self._jogar(jj))
            h.addWidget(b)
        v.addLayout(h)
        self.jogo_msg = QLabel("Escolha uma jogada.")
        self.jogo_msg.setWordWrap(True)
        self.jogo_msg.setMinimumHeight(60)
        v.addWidget(self.jogo_msg)
        self.placar = QLabel()
        v.addWidget(self.placar)
        v.addStretch(1)
        return w

    def _atualizar_placar(self):
        p = self.leitor.placar
        self.placar.setText(f"Placar geral: você {p['voce']} · {self.app.nome} {p['ele']} · empates {p['empate']}")

    def _jogar(self, voce):
        ele = self.leitor.jogar()
        r = self.leitor.aprender(voce, ele)
        premio = {"voce": 12, "empate": 5, "ele": 3}[r]
        ganhou = self.app.carteira.ganhar(premio, "pedra-papel-tesoura")
        frase = {"voce": "Você ganhou!", "ele": f"{self.app.nome} ganhou!", "empate": "Empate."}[r]
        self.jogo_msg.setText(f"Você: {voce} · {self.app.nome}: {ele}\n{frase} +{ganhou} moedas")
        if r == "ele":
            self.app.emotion.force("feliz", 2.5, priority=PRIORITY.get("carinho", 15))
        elif r == "voce":
            self.app.emotion.force("dramatico", 1.8, priority=PRIORITY["dramatico"])
        self.atualizar()

    # ---------------- rede ----------------

    def _aba_rede(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("<b>Rede dos pestinhas</b><br>Ranking, museu de pinturas e memes. "
                           f"O site: <a href='{SITE}'>{SITE}</a>"))
        v.itemAt(0).widget().setOpenExternalLinks(True)
        v.itemAt(0).widget().setWordWrap(True)
        linha = QHBoxLayout()
        linha.addWidget(QLabel("Tutor:"))
        self.tutor = QLineEdit(self.app.rede.tutor)
        self.tutor.setMaxLength(30)
        self.tutor.setPlaceholderText("seu nome")
        linha.addWidget(self.tutor, 1)
        v.addLayout(linha)
        self.participar = QCheckBox("Participar da rede (perfil público, falas e ranking)")
        self.participar.setChecked(bool(self.app.perms.get("rede_social")))
        self.participar.toggled.connect(self._participar)
        v.addWidget(self.participar)
        self.rede_status = QLabel()
        self.rede_status.setWordWrap(True)
        v.addWidget(self.rede_status)
        botoes = QHBoxLayout()
        self.b_meme = QPushButton("Criar meme")
        self.b_meme.clicked.connect(self._criar_meme)
        self.b_postar = QPushButton("Postar este meme")
        self.b_postar.clicked.connect(lambda: self._postar(self.meme_atual, "meme"))
        self.b_pintura = QPushButton("Postar último desenho")
        self.b_pintura.clicked.connect(self._postar_desenho)
        for b in (self.b_meme, self.b_postar, self.b_pintura):
            botoes.addWidget(b)
        v.addLayout(botoes)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(150)
        v.addWidget(self.preview, 1)
        rank = QHBoxLayout()
        rank.addWidget(QLabel("<b>Pestinha mais rico</b>"))
        b = QPushButton("Atualizar")
        b.clicked.connect(self._buscar_ranking)
        rank.addWidget(b)
        v.addLayout(rank)
        self.lista_ranking = QListWidget()
        v.addWidget(self.lista_ranking, 1)
        return w

    def _atualizar_rede(self):
        ligado = bool(self.app.perms.get("rede_social"))
        r = self.app.rede
        if not ligado:
            self.rede_status.setText("Fora da rede. Marque acima para entrar (precisa do nome do tutor).")
        elif not r.registrado:
            self.rede_status.setText("Entrando na rede...")
        else:
            erro = f" · último erro: {r.ultimo_erro}" if r.ultimo_erro else ""
            self.rede_status.setText(f"Na rede como {r.tutor} · {self.app.nome}{erro}")
        self.b_postar.setEnabled(ligado and r.registrado and self.meme_atual is not None)
        self.b_pintura.setEnabled(ligado and r.registrado)

    def _participar(self, ligado):
        tutor = self.tutor.text().strip()
        if ligado and not tutor:
            QMessageBox.information(self, "Rede", "Escreva o nome do tutor primeiro.")
            self.participar.setChecked(False)
            return
        self.app.apply_perms({"rede_social": ligado})
        if ligado:
            self.app.rede.entrar(tutor, self.app.nome, self.app.pet.aparencia.moldura.name(),
                                 pronto=lambda _r, _e: self._depois(self._entrou))
        self.atualizar()

    def _entrou(self):
        self.app.sincronizar_rede()
        self.atualizar()

    def _criar_meme(self):
        caminho = fazer_meme(self.app.pet_paths.base, self.app.conteudo)
        if caminho is None:
            self.preview.setText("Ele ainda não tem desenho para virar meme. Peça um desenho primeiro.")
            return
        self.meme_atual = caminho
        self.app.carteira.ganhar(2, "fez um meme")
        self.preview.setPixmap(QPixmap(str(caminho)).scaled(300, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.atualizar()

    def _postar_desenho(self):
        pasta = self.app.pet_paths.base / "desenhos"
        desenhos = sorted(pasta.rglob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True) if pasta.exists() else []
        desenhos = [d for d in desenhos if d.name != "modelo.png"]
        if not desenhos:
            self.preview.setText("Ainda não tem desenho.")
            return
        self.preview.setPixmap(QPixmap(str(desenhos[0])).scaled(300, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._postar(desenhos[0], "pintura")

    def _postar(self, caminho, tipo):
        if caminho is None:
            return
        ok = QMessageBox.question(
            self, "Postar na rede",
            "Essa imagem vai ficar PÚBLICA no museu dos pestinhas.\n"
            "Os desenhos são feitos a partir da sua tela: confira se não aparece nada pessoal.\n\nPostar?")
        if ok != QMessageBox.Yes:
            return
        self.rede_status.setText("Postando...")

        def pronto(_r, erro):
            def fim():
                if erro:
                    self.rede_status.setText(f"Não deu para postar: {erro}")
                else:
                    ganhou = self.app.carteira.ganhar(10, f"postou {tipo}")
                    self.rede_status.setText(f"Postado! +{ganhou} moedas")
                    self.saldo.setText(f"{self.app.carteira.moedas} moedas")
            self._depois(fim)
        legenda = f"{tipo} do {self.app.nome}"
        self.app.rede.postar(caminho, tipo, legenda, pronto)

    def _buscar_ranking(self):
        self.lista_ranking.clear()
        self.lista_ranking.addItem("carregando...")

        def pronto(r, erro):
            def fim():
                self.lista_ranking.clear()
                if erro or not isinstance(r, list):
                    self.lista_ranking.addItem(f"sem conexão ({erro})")
                    return
                for i, pet in enumerate(r, 1):
                    self.lista_ranking.addItem(f"{i}. {pet.get('nome')} (tutor {pet.get('tutor')}) · "
                                               f"{pet.get('moedas')} moedas")
            self._depois(fim)
        self.app.rede.ranking(pronto)

    # ---------------- galeria ----------------

    def _aba_galeria(self):
        w = QWidget()
        v = QVBoxLayout(w)
        b = QPushButton("Abrir a pasta dos desenhos")
        b.clicked.connect(self.app.casinha_ctl.abrir_galeria)
        v.addWidget(b)
        self.grade = QGridLayout()
        v.addLayout(self.grade)
        v.addStretch(1)
        return w

    def _preencher_galeria(self):
        while self.grade.count():
            item = self.grade.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        pasta = self.app.pet_paths.base / "desenhos"
        imgs = sorted(pasta.rglob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)[:6] if pasta.exists() else []
        imgs += memes_feitos(self.app.pet_paths.base)[:3]
        if not imgs:
            self.grade.addWidget(QLabel("Nada ainda. Peça um desenho pelo menu do pet."), 0, 0)
        for i, caminho in enumerate(imgs):
            lab = QLabel()
            lab.setPixmap(QPixmap(str(caminho)).scaled(150, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            lab.setToolTip(caminho.name)
            self.grade.addWidget(lab, i // 3, i % 3)
