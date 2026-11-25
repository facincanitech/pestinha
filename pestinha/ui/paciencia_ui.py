"""
PACIÊNCIA (tela) - a paciência de associações do pet, com cara de jogo de celular.

Clique numa carta (ou pilha) e depois onde quer pôr. Clique duplo manda direto para as coroas.
Clique no monte para virar uma carta. Dica e Desfazer: 3 grátis por nível, depois custam moedinhas.
"""

import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from ..body.desenho_rosto import draw_face
from ..core.emotion import PRIORITY
from ..core.paciencia import COLUNAS, ESPACOS, RECOMPENSA_DIARIA, Partida, Progresso, eh_bau

W, H = 480, 820
CW, CH = 82, 112
GAP = (W - 5 * CW) / 6
Y_TOPO, Y_ESPACOS, Y_COLUNAS = 74, 210, 350
PASSO_COSTAS, PASSO_FRENTE = 16, 30
GRATIS = 3
VERDE, VERDE_ESC = QColor("#159a49"), QColor("#0b6e31")


def _x(i):
    return GAP + i * (CW + GAP)


def caber(p, r, texto, maximo, minimo=7, alinhar=Qt.AlignCenter):
    """Escreve `texto` dentro de `r` com a maior fonte que couber (quebra linha só entre palavras)."""
    flags = alinhar | Qt.TextWordWrap
    for tam in range(maximo, minimo - 1, -1):
        fonte = QFont("Segoe UI", tam, QFont.Bold)
        m = QFontMetricsF(fonte)
        maior_palavra = max((m.horizontalAdvance(w) for w in texto.split()), default=0)
        caixa = m.boundingRect(r, int(flags), texto)
        if maior_palavra <= r.width() and caixa.height() <= r.height():
            break
    p.setFont(fonte)
    p.drawText(r, flags, texto)


def figura(p, r, emoji, tam):
    p.setFont(QFont("Segoe UI Emoji", tam))
    p.drawText(r, Qt.AlignCenter, emoji)


class Paciencia(QWidget):
    def __init__(self, app):
        super().__init__(None, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.app = app
        self.setWindowTitle(f"Paciência de associações · {app.nome}")
        self.setFixedSize(W, H)
        self.progresso = Progresso(app.pet_paths.base / "paciencia.json")
        self.selecao = None
        self.flutuantes = []          # [(texto, x, y, até)]
        self.aviso = None             # ("diaria"|"venceu"|"perdeu", dados)
        self.dica_marcada = None
        self.novo_nivel()
        diaria = self.progresso.recompensa_do_dia()
        if diaria:
            dia, moedas = diaria
            ganhou = app.carteira.ganhar(moedas, f"recompensa diária (dia {dia})")
            self.aviso = ("diaria", (dia, ganhou))
        self.relogio = QTimer(self)
        self.relogio.timeout.connect(self.update)
        self.relogio.start(60)

    def novo_nivel(self):
        self.partida = Partida(self.progresso.nivel)
        self.dicas = self.desfeitos = 0
        self.selecao = None
        self.dica_marcada = None

    # ---------------- geometria ----------------

    def _ret_coluna(self, col, idx):
        y = Y_COLUNAS
        for c in self.partida.colunas[col][:idx]:
            y += PASSO_COSTAS if c.virada else PASSO_FRENTE
        return QRectF(_x(col), y, CW, CH)

    def _alvo(self, pos):
        """O que está sob o mouse: ("monte",), ("descarte",), ("espaco", j), ("coluna", col, idx|None), ("botao", nome)."""
        x, y = pos.x(), pos.y()
        if QRectF(_x(4), Y_TOPO, CW, CH).contains(pos):
            return ("monte",)
        if QRectF(_x(3), Y_TOPO, CW, CH).contains(pos):
            return ("descarte",)
        for j in range(ESPACOS):
            if QRectF(_x(j), Y_ESPACOS, CW, CH).contains(pos):
                return ("espaco", j)
        for nome, r in self._botoes().items():
            if r.contains(pos):
                return ("botao", nome)
        for col in range(COLUNAS):
            if _x(col) <= x <= _x(col) + CW and y >= Y_COLUNAS:
                cartas = self.partida.colunas[col]
                for idx in range(len(cartas) - 1, -1, -1):
                    if self._ret_coluna(col, idx).contains(pos):
                        return ("coluna", col, idx)
                return ("coluna", col, None)
        return None

    def _botoes(self):
        return {"dica": QRectF(40, H - 92, 120, 64), "desfazer": QRectF(180, H - 92, 120, 64),
                "reiniciar": QRectF(320, H - 92, 120, 64)}

    # ---------------- mouse ----------------

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return
        if self.aviso:
            self._fechar_aviso()
            return
        alvo = self._alvo(ev.position())
        self.dica_marcada = None
        if alvo is None:
            self.selecao = None
        elif alvo[0] == "botao":
            self._botao(alvo[1])
        elif alvo[0] == "monte":
            self.selecao = None
            self.partida.comprar()
        elif self.selecao is None:
            self._selecionar(alvo)
        else:
            destino = ("espaco", alvo[1]) if alvo[0] == "espaco" else ("coluna", alvo[1]) if alvo[0] == "coluna" else None
            if destino is None or not self.partida.mover(self.selecao, destino):
                self.selecao = None
                self._selecionar(alvo)
            else:
                self.selecao = None
        self._depois_da_jogada()
        self.update()

    def mouseDoubleClickEvent(self, ev):
        alvo = self._alvo(ev.position())
        origem = None
        if alvo and alvo[0] == "descarte" and self.partida.descarte:
            origem = ("descarte",)
        elif alvo and alvo[0] == "coluna" and alvo[2] is not None:
            origem = ("coluna", alvo[1], alvo[2])
        if origem and self.partida.para_espaco(origem):
            self.selecao = None
            self._depois_da_jogada()
        self.update()

    def _selecionar(self, alvo):
        if alvo[0] == "descarte" and self.partida.descarte:
            self.selecao = ("descarte",)
        elif alvo[0] == "coluna" and alvo[2] is not None:
            inicio = self.partida.pilha_movel(alvo[1])
            if inicio is not None and alvo[2] >= inicio:
                self.selecao = ("coluna", alvo[1], alvo[2])

    def _botao(self, nome):
        c = self.app.carteira
        if nome == "dica":
            if self.dicas >= GRATIS and c.moedas < 5:
                return
            d = self.partida.dica()
            if d is None:
                return
            if self.dicas >= GRATIS:
                c.moedas -= 5
                c.salvar()
            self.dicas += 1
            self.dica_marcada = d
        elif nome == "desfazer":
            if self.desfeitos >= GRATIS and c.moedas < 3:
                return
            if self.partida.desfazer():
                if self.desfeitos >= GRATIS:
                    c.moedas -= 3
                    c.salvar()
                self.desfeitos += 1
        elif nome == "reiniciar":
            self.novo_nivel()

    def _depois_da_jogada(self):
        p = self.partida
        for quanto, motivo in p.ganhos:
            ganhou = self.app.carteira.ganhar(quanto, f"paciência: {motivo}")
            n = len(self.flutuantes)
            self.flutuantes.append((f"+{ganhou}", W / 2 + (n % 3 - 1) * 70, Y_ESPACOS + 40 + (n // 3) * 26,
                                    time.monotonic() + 1.2 + n * 0.15))
            if motivo.startswith("completou"):
                self.app.emotion.force("feliz", 2.5, priority=PRIORITY.get("carinho", 15))
        p.ganhos.clear()
        if p.venceu and not self.aviso:
            self.progresso.venceu()
            bau = 0
            if eh_bau(p.nivel):
                bau = self.app.carteira.ganhar(50 + p.nivel * 5, f"baú do nível {p.nivel}")
            self.aviso = ("venceu", (p.nivel, bau))
            self.app.emotion.force("feliz", 5.0, priority=PRIORITY.get("carinho", 15))
        elif p.perdeu and not self.aviso:
            self.aviso = ("perdeu", p.nivel)
            self.app.emotion.force("triste", 3.0)

    def _fechar_aviso(self):
        tipo = self.aviso[0]
        self.aviso = None
        if tipo in ("venceu", "perdeu"):
            self.novo_nivel()

    # ---------------- desenho ----------------

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), VERDE)
        self._barra(p)
        self._monte(p)
        self._espacos(p)
        self._colunas(p)
        self._botoes_desenho(p)
        self._mascote(p)
        agora = time.monotonic()
        self.flutuantes = [f for f in self.flutuantes if f[3] > agora]
        for texto, x, y, ate in self.flutuantes:
            subida = max(0.0, 1.2 - (ate - agora)) * 40
            p.setPen(QColor("#ffe082"))
            p.setFont(QFont("Segoe UI", 20, QFont.Black))
            p.drawText(QRectF(x - 60, y - subida, 120, 30), Qt.AlignCenter, texto)
        if self.aviso:
            self._aviso(p)
        p.end()

    def _pilula(self, p, r, texto, cor_fundo="#0b5d29"):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(cor_fundo))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Segoe UI", 13, QFont.Bold))
        p.drawText(r, Qt.AlignCenter, texto)

    def _barra(self, p):
        self._pilula(p, QRectF(14, 16, 130, 38), f"🪙 {self.app.carteira.moedas}")
        pt = self.partida
        self._pilula(p, QRectF(154, 16, 170, 38), f"Nível {pt.nivel} · {pt.rotulo}",
                     "#6a1b9a" if pt.rotulo in ("Super difícil", "Lendário") else "#0b5d29")
        cor = "#b71c1c" if pt.jogadas <= 10 else "#0b5d29"
        self._pilula(p, QRectF(334, 16, 132, 38), f"Jogadas {max(0, pt.jogadas)}", cor)
        p.setPen(QColor("#d7f5df"))
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(QRectF(14, Y_TOPO, 240, 22), Qt.AlignLeft,
                   f"Categorias: {pt.completas}/{pt.total_categorias}")

    def _costas(self, p, r):
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.setBrush(QColor("#2f7de1"))
        p.drawRoundedRect(r, 9, 9)
        p.setPen(QPen(QColor(255, 255, 255, 60), 2))
        passo = 14
        p.save()
        p.setClipRect(r.adjusted(4, 4, -4, -4))
        for k in range(-int(r.height()), int(r.width() + r.height()), passo):
            p.drawLine(QPointF(r.left() + k, r.top()), QPointF(r.left() + k - r.height(), r.bottom()))
            p.drawLine(QPointF(r.left() + k, r.top()), QPointF(r.left() + k + r.height(), r.bottom()))
        p.restore()

    def _coroa(self, p, cx, cy, s, cor):
        p.setPen(Qt.NoPen)
        p.setBrush(cor)
        p.drawPolygon(QPolygonF([QPointF(cx - s, cy + s * .6), QPointF(cx - s, cy - s * .4), QPointF(cx - s * .5, cy),
                                 QPointF(cx, cy - s * .7), QPointF(cx + s * .5, cy), QPointF(cx + s, cy - s * .4),
                                 QPointF(cx + s, cy + s * .6)]))

    def _frente(self, p, r, carta, selecionada=False, dica=False, coberta=False):
        if carta.cadeado:
            self._cadeado(p, r, carta, coberta)
            return
        borda = QColor("#ffb300") if carta.eh_categoria else QColor("#e8dcc4")
        if selecionada:
            borda = QColor("#29b6f6")
        if dica:
            borda = QColor("#ff4081")
        p.setPen(QPen(borda, 4 if (selecionada or dica or carta.eh_categoria) else 1.5))
        p.setBrush(QColor("#fffaf0"))
        p.drawRoundedRect(r, 9, 9)
        p.setPen(QColor("#5d4037"))
        so_figura = carta.modo == "figura" and not carta.eh_categoria
        if coberta:                                     # só aparece a faixa de cima
            x = r.left() + 6
            if carta.eh_categoria:
                self._coroa(p, r.left() + 13, r.top() + 14, 7, QColor("#ffb300"))
                x = r.left() + 22
            if carta.figura:
                figura(p, QRectF(x - 2, r.top() + 3, 20, 22), carta.figura, 11)
                x += 18
            if not so_figura:
                caber(p, QRectF(x, r.top() + 4, r.right() - x - 4, 22), carta.texto, 9, 6,
                      Qt.AlignLeft | Qt.AlignVCenter)
            return
        if carta.eh_categoria:
            self._coroa(p, r.left() + 16, r.top() + 16, 9, QColor("#ffb300"))
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            p.drawText(QRectF(r.left(), r.top() + 6, r.width() - 8, 20), Qt.AlignRight,
                       f"0/{self.partida.tamanho[carta.categoria]}")
        if so_figura:
            figura(p, r.adjusted(2, 8, -2, -4), carta.figura, 34)
            return
        if carta.figura:
            figura(p, QRectF(r.left(), r.top() + 22, r.width(), 40), carta.figura, 24)
            caber(p, QRectF(r.left() + 4, r.top() + 64, r.width() - 8, r.height() - 70), carta.texto, 13)
        else:
            caber(p, r.adjusted(4, 18, -4, -6), carta.texto, 13)

    def _cadeado(self, p, r, carta, coberta):
        p.setPen(QPen(QColor("#e65100"), 3))
        p.setBrush(QColor("#5c6bc0"))
        p.drawRoundedRect(r, 9, 9)
        cx = r.center().x()
        cy = r.top() + 16 if coberta else r.center().y()
        p.setPen(QPen(QColor("#ffca28"), 4))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(cx - 11, cy - 22, 22, 24), 0, 180 * 16)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ffb300"))
        p.drawRoundedRect(QRectF(cx - 16, cy - 10, 32, 26), 6, 6)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Segoe UI", 10, QFont.Black))
        p.drawText(QRectF(cx - 16, cy - 10, 32, 26), Qt.AlignCenter,
                   f"{min(self.partida.completas, carta.cadeado)}/{carta.cadeado}")

    def _monte(self, p):
        pt = self.partida
        r = QRectF(_x(4), Y_TOPO, CW, CH)
        if pt.monte:
            self._costas(p, r)
            self._pilula(p, QRectF(r.right() - 34, r.top() + 4, 30, 20), str(len(pt.monte)), "#ffffff")
            p.setPen(QColor("#1565c0"))
            p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.drawText(QRectF(r.right() - 34, r.top() + 4, 30, 20), Qt.AlignCenter, str(len(pt.monte)))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 120), 2, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 9, 9)
            p.setPen(QColor("#d7f5df"))
            p.setFont(QFont("Segoe UI", 20, QFont.Bold))
            p.drawText(r, Qt.AlignCenter, "↻" if pt.descarte else "")
        rd = QRectF(_x(3), Y_TOPO, CW, CH)
        if pt.descarte:
            dica = self.dica_marcada and self.dica_marcada[0] == ("descarte",)
            self._frente(p, rd, pt.descarte[-1], self.selecao == ("descarte",), bool(dica))
        if self.dica_marcada == ("monte",):
            p.setPen(QPen(QColor("#ff4081"), 4))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r, 9, 9)

    def _espacos(self, p):
        for j in range(ESPACOS):
            r = QRectF(_x(j), Y_ESPACOS, CW, CH)
            e = self.partida.espacos[j]
            dica = self.dica_marcada and len(self.dica_marcada) == 2 and self.dica_marcada[1] == ("espaco", j)
            if e is None:
                p.setPen(QPen(QColor("#ff4081"), 3) if dica else Qt.NoPen)
                p.setBrush(VERDE_ESC)
                p.drawRoundedRect(r, 9, 9)
                self._coroa(p, r.center().x(), r.center().y(), 20, QColor("#13843f"))
            else:
                p.setPen(QPen(QColor("#ff4081") if dica else QColor("#ffb300"), 4))
                p.setBrush(QColor("#fff3c4"))
                p.drawRoundedRect(r, 9, 9)
                self._coroa(p, r.left() + 16, r.top() + 16, 9, QColor("#ffb300"))
                p.setPen(QColor("#5d4037"))
                p.setFont(QFont("Segoe UI", 9, QFont.Bold))
                p.drawText(QRectF(r.left(), r.top() + 6, r.width() - 8, 20), Qt.AlignRight, f"{e['dentro']}/{e['total']}")
                from ..core.paciencia import CATEGORIAS
                figura(p, QRectF(r.left(), r.top() + 24, r.width(), 38), CATEGORIAS[e["cat"]][0], 22)
                caber(p, QRectF(r.left() + 4, r.top() + 64, r.width() - 8, r.height() - 70), e["cat"], 12)

    def _colunas(self, p):
        pt = self.partida
        for col in range(COLUNAS):
            cartas = pt.colunas[col]
            if not cartas:
                p.setPen(QPen(QColor(255, 255, 255, 90), 2, Qt.DashLine))
                p.setBrush(Qt.NoBrush)
                p.drawRoundedRect(QRectF(_x(col), Y_COLUNAS, CW, CH), 9, 9)
                continue
            for idx, carta in enumerate(cartas):
                r = self._ret_coluna(col, idx)
                if carta.virada:
                    self._costas(p, r)
                else:
                    sel = self.selecao and self.selecao[0] == "coluna" and self.selecao[1] == col and idx >= self.selecao[2]
                    d = self.dica_marcada
                    dica = d and d != ("monte",) and d[0][0] == "coluna" and d[0][1] == col and idx >= d[0][2]
                    self._frente(p, r, carta, bool(sel), bool(dica), coberta=idx < len(cartas) - 1)

    def _botoes_desenho(self, p):
        rotulos = {
            "dica": f"Dica ({max(0, GRATIS - self.dicas)})" if self.dicas < GRATIS else "Dica · 5",
            "desfazer": f"Desfazer ({max(0, GRATIS - self.desfeitos)})" if self.desfeitos < GRATIS else "Desfazer · 3",
            "reiniciar": "Recomeçar",
        }
        cores = {"dica": "#2f7de1", "desfazer": "#9e9e9e", "reiniciar": "#f9a825"}
        for nome, r in self._botoes().items():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 50))
            p.drawRoundedRect(r.translated(0, 4), 16, 16)
            p.setBrush(QColor(cores[nome]))
            p.drawRoundedRect(r, 16, 16)
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Segoe UI", 12, QFont.Bold))
            p.drawText(r, Qt.AlignCenter, rotulos[nome])

    def _mascote(self, p):
        """O pet olhando o jogo, no canto."""
        st = self.app.pet_state
        p.save()
        p.translate(70, Y_TOPO + 76)
        p.scale(0.6, 0.6)
        draw_face(p, st.shape, (0.8, 0.4), 0.08 if (time.monotonic() % 4) < 0.12 else 1.0, st.emotion,
                  carinho=st.feliz_fechado(), aparencia=self.app.pet.aparencia)
        p.restore()

    def _aviso(self, p):
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))
        r = QRectF(40, 230, W - 80, 300)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#fff4dc"))
        p.drawRoundedRect(r, 26, 26)
        tipo, dados = self.aviso
        p.setPen(QColor("#5d4037"))
        if tipo == "diaria":
            dia, moedas = dados
            titulo, corpo = "Recompensa diária", f"Dia {dia} seguido\n+{moedas} moedas"
            p.setFont(QFont("Segoe UI", 11, QFont.Bold))
            for k, valor in enumerate(RECOMPENSA_DIARIA):
                caixa = QRectF(r.left() + 18 + k * 50, r.bottom() - 70, 44, 44)
                feito = k < ((dia - 1) % len(RECOMPENSA_DIARIA)) + 1
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#ffca28") if feito else QColor("#e0d3b8"))
                p.drawRoundedRect(caixa, 10, 10)
                p.setPen(QColor("#5d4037"))
                p.drawText(caixa, Qt.AlignCenter, str(valor))
        elif tipo == "venceu":
            nivel, bau = dados
            titulo = "Venceu!"
            corpo = f"Nível {nivel} completo.\n{self.app.nome} está orgulhoso."
            if bau:
                corpo += f"\nBaú aberto: +{bau} moedas!"
            else:
                proximo = (nivel // 5 + 1) * 5
                corpo += f"\nPróximo baú no nível {proximo}."
        else:
            titulo, corpo = "Acabaram as jogadas", "Quase! Toque para tentar de novo."
        p.setPen(QColor("#5d4037"))
        p.setFont(QFont("Segoe UI", 24, QFont.Black))
        p.drawText(QRectF(r.left(), r.top() + 24, r.width(), 44), Qt.AlignCenter, titulo)
        p.setFont(QFont("Segoe UI", 15, QFont.Bold))
        p.drawText(QRectF(r.left(), r.top() + 84, r.width(), 90), Qt.AlignCenter, corpo)
        p.setFont(QFont("Segoe UI", 11))
        p.drawText(QRectF(r.left(), r.bottom() - 22, r.width(), 18), Qt.AlignCenter, "toque para continuar")
