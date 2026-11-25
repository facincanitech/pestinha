"""
PACIÊNCIA DE ASSOCIAÇÕES - paciência em que os naipes são categorias.

    - em cima, 5 espaços (coroas): cada um recebe uma CARTA DE CATEGORIA (ex.: "Casa")
    - depois, as palavras daquela categoria entram nela ("cama", "janela", "sofá"...)
    - quando todas entram, a categoria se completa e o espaço libera
    - nas colunas, uma palavra vai em cima de outra da MESMA categoria (e arrastam juntas)
    - coluna vazia aceita qualquer carta; o monte vira uma carta por vez
    - cada movimento gasta uma jogada; acabar as jogadas é derrota

Puro: sem Qt. O progresso (nível, sequência diária) fica em memory/pets/<pet>/paciencia.json.
"""

import copy
import random
from dataclasses import dataclass
from datetime import date, timedelta

from ..store import read_json, write_json

# categoria: (figura da categoria, [(palavra, figura), ...])
CATEGORIAS = {
    "Casa": ("🏠", [("cama", "🛏️"), ("janela", "🪟"), ("sofá", "🛋️"), ("porta", "🚪"), ("chuveiro", "🚿"),
                   ("vaso sanitário", "🚽"), ("espelho", "🪞"), ("cadeira", "🪑")]),
    "Cozinha": ("🍳", [("panela", "🍲"), ("garfo", "🍴"), ("colher", "🥄"), ("faca", "🔪"), ("xícara", "☕"),
                      ("prato", "🍽️"), ("tigela", "🥣"), ("garrafa", "🍾")]),
    "Frutas": ("🍎", [("banana", "🍌"), ("uva", "🍇"), ("abacaxi", "🍍"), ("morango", "🍓"), ("melancia", "🍉"),
                     ("limão", "🍋"), ("pêssego", "🍑"), ("cereja", "🍒")]),
    "Bichos": ("🐾", [("cachorro", "🐶"), ("gato", "🐱"), ("cavalo", "🐴"), ("galinha", "🐔"), ("tartaruga", "🐢"),
                     ("coelho", "🐰"), ("porco", "🐷"), ("vaca", "🐮")]),
    "Mar": ("🌊", [("baleia", "🐋"), ("tubarão", "🦈"), ("polvo", "🐙"), ("peixe", "🐟"), ("caranguejo", "🦀"),
                  ("concha", "🐚"), ("golfinho", "🐬"), ("lagosta", "🦞")]),
    "Espaço": ("🌌", [("planeta", "🪐"), ("estrela", "⭐"), ("cometa", "☄️"), ("foguete", "🚀"), ("lua", "🌙"),
                     ("astronauta", "🧑‍🚀"), ("satélite", "🛰️"), ("disco voador", "🛸")]),
    "Música": ("🎵", [("violão", "🎸"), ("bateria", "🥁"), ("piano", "🎹"), ("trompete", "🎺"), ("microfone", "🎤"),
                     ("violino", "🎻"), ("fone", "🎧"), ("saxofone", "🎷")]),
    "Esportes": ("🏅", [("futebol", "⚽"), ("basquete", "🏀"), ("vôlei", "🏐"), ("tênis", "🎾"), ("boliche", "🎳"),
                       ("natação", "🏊"), ("ciclismo", "🚴"), ("boxe", "🥊")]),
    "Computador": ("💻", [("teclado", "⌨️"), ("mouse", "🖱️"), ("monitor", "🖥️"), ("impressora", "🖨️"),
                         ("disquete", "💾"), ("CD", "💿"), ("bateria do note", "🔋"), ("tomada", "🔌")]),
    "Escola": ("🏫", [("caderno", "📓"), ("lápis", "✏️"), ("livro", "📖"), ("régua", "📏"), ("mochila", "🎒"),
                     ("tesoura", "✂️"), ("giz de cera", "🖍️"), ("calculadora", "🧮")]),
    "Clima": ("⛅", [("chuva", "🌧️"), ("trovão", "⛈️"), ("neblina", "🌫️"), ("neve", "❄️"), ("vento", "🌬️"),
                    ("arco-íris", "🌈"), ("sol", "☀️"), ("tornado", "🌪️")]),
    "Corpo": ("🧍", [("olho", "👁️"), ("orelha", "👂"), ("nariz", "👃"), ("boca", "👄"), ("mão", "✋"),
                    ("pé", "🦶"), ("cérebro", "🧠"), ("dente", "🦷")]),
    "Roupas": ("👕", [("camiseta", "👕"), ("calça", "👖"), ("vestido", "👗"), ("meia", "🧦"), ("boné", "🧢"),
                     ("chinelo", "🩴"), ("cachecol", "🧣"), ("luva", "🧤")]),
    "Profissões": ("💼", [("médico", "🧑‍⚕️"), ("pedreiro", "👷"), ("cozinheiro", "🧑‍🍳"), ("bombeiro", "🧑‍🚒"),
                         ("piloto", "🧑‍✈️"), ("juiz", "🧑‍⚖️"), ("policial", "👮"), ("fazendeiro", "🧑‍🌾")]),
    "Transporte": ("🚦", [("ônibus", "🚌"), ("bicicleta", "🚲"), ("metrô", "🚇"), ("avião", "✈️"), ("barco", "⛵"),
                         ("trem", "🚆"), ("moto", "🏍️"), ("helicóptero", "🚁")]),
    "Festa": ("🎉", [("bolo", "🎂"), ("balão", "🎈"), ("confete", "🎊"), ("presente", "🎁"), ("vela", "🕯️"),
                    ("chapéu de festa", "🥳"), ("pirulito", "🍭"), ("fogos", "🎆")]),
    "Jogos": ("🎲", [("xadrez", "♟️"), ("dado", "🎲"), ("baralho", "🃏"), ("videogame", "🎮"), ("quebra-cabeça", "🧩"),
                    ("ioiô", "🪀"), ("pipa", "🪁"), ("bola de gude", "🔮")]),
    "Ferramentas": ("🧰", [("martelo", "🔨"), ("chave inglesa", "🔧"), ("serrote", "🪚"), ("parafuso", "🔩"),
                          ("machado", "🪓"), ("ímã", "🧲"), ("escada", "🪜"), ("balde", "🪣")]),
    "Sentimentos": ("💭", [("alegria", "😄"), ("tristeza", "😢"), ("raiva", "😠"), ("medo", "😨"), ("amor", "😍"),
                          ("sono", "😴"), ("surpresa", "😲"), ("vergonha", "😳")]),
    "Comida": ("🍽️", [("pizza", "🍕"), ("hambúrguer", "🍔"), ("pão", "🍞"), ("queijo", "🧀"), ("ovo", "🥚"),
                      ("taco", "🌮"), ("pipoca", "🍿"), ("sorvete", "🍦")]),
    "Natureza": ("🌳", [("árvore", "🌳"), ("flor", "🌸"), ("cacto", "🌵"), ("cogumelo", "🍄"), ("folha", "🍃"),
                       ("vulcão", "🌋"), ("montanha", "⛰️"), ("girassol", "🌻")]),
    "Pestinha": ("👾", [("casinha", "🏡"), ("celular Mapple", "📱"), ("moedinha", "🪙"), ("chapéu", "🤠"),
                       ("notebook", "💻"), ("bolinha", "🥎"), ("coroa", "👑"), ("desenho", "🖼️")]),
}

ESPACOS = 5
COLUNAS = 5
RECOMPENSA_DIARIA = [20, 30, 40, 50, 70, 90, 150]


@dataclass
class Carta:
    id: int
    texto: str
    categoria: str
    eh_categoria: bool = False
    virada: bool = True          # True = de costas
    figura: str = ""
    modo: str = "ambos"          # "ambos" (figura e palavra), "figura" (só a figura) ou "palavra"
    cadeado: int = 0             # > 0: cadeado que abre com esse número de categorias completas


def dificuldade(nivel):
    """
    Como o nível aperta. Cada faixa traz uma coisa nova:
        1-5    figura + palavra, poucas categorias, jogada sobrando
        6-11   algumas cartas só com figura
        12-19  cadeados nas colunas (abrem quando você completa categorias)
        20-34  mais categorias, mais palavras, quase tudo só figura
        35+    "Lendário": tudo no máximo e jogadas contadas
    """
    n = max(1, nivel)
    cats = min(3 + n // 3, 12)
    palavras = min(3 + n // 4, 8)
    por_coluna = min(2 + n // 3, 6)
    so_figura = 0.0 if n < 6 else min(0.15 + (n - 6) * 0.03, 0.85)
    cadeados = 0 if n < 12 else min(1 + (n - 12) // 6, 3)
    folga = max(2.15, 3.0 - min(n, 40) / 40 * 1.0)
    rotulo = ("Fácil" if n < 6 else "Médio" if n < 12 else "Difícil" if n < 20
              else "Super difícil" if n < 35 else "Lendário")
    return {"cats": cats, "palavras": palavras, "por_coluna": por_coluna, "so_figura": so_figura,
            "cadeados": cadeados, "folga": folga, "rotulo": rotulo}


def eh_bau(nivel):
    """A cada 5 níveis, um baú de moedas."""
    return nivel % 5 == 0


class Partida:
    def __init__(self, nivel, semente=None):
        self.nivel = nivel
        r = random.Random(semente)
        d = dificuldade(nivel)
        self.rotulo = d["rotulo"]
        cats, n_palavras = d["cats"], d["palavras"]
        escolhidas = r.sample(sorted(CATEGORIAS), cats)
        cartas, i = [], 0
        for c in escolhidas:
            fig_cat, itens = CATEGORIAS[c]
            cartas.append(Carta(i, c, c, eh_categoria=True, figura=fig_cat))
            i += 1
            for w, fig in r.sample(itens, n_palavras):
                modo = "figura" if r.random() < d["so_figura"] else "ambos"
                cartas.append(Carta(i, w, c, figura=fig, modo=modo))
                i += 1
        r.shuffle(cartas)
        self.total_categorias = cats
        self.tamanho = {c: n_palavras for c in escolhidas}
        self.colunas = [[] for _ in range(COLUNAS)]
        for col in range(COLUNAS):
            for _ in range(d["por_coluna"]):
                if cartas:
                    self.colunas[col].append(cartas.pop())
        # cadeados: entram no meio de colunas e só abrem com categorias completas
        cols_com_cadeado = r.sample(range(COLUNAS), d["cadeados"])
        for k, col in enumerate(cols_com_cadeado):
            pos = max(1, len(self.colunas[col]) // 2)
            requisito = min(cats - 1, 1 + k + r.randint(0, 1))
            self.colunas[col].insert(pos, Carta(1000 + k, "cadeado", "", virada=False, cadeado=max(1, requisito)))
        for col in self.colunas:
            if col:
                col[-1].virada = False
        self.monte = cartas                 # o topo é o fim da lista
        self.descarte = []
        self.espacos = [None] * ESPACOS     # {"cat", "total", "dentro"}
        self.completas = 0
        self.jogadas = int(len(self.tamanho) * (n_palavras + 1) * d["folga"]) + 10 + 6 * d["cadeados"]
        self.ganhos = []                    # eventos de moeda para a tela: (quanto, motivo)
        self._historico = []

    # ---------------- estado ----------------

    @property
    def venceu(self):
        return self.completas >= self.total_categorias

    @property
    def perdeu(self):
        return not self.venceu and self.jogadas <= 0

    def _guardar(self):
        estado = copy.deepcopy((self.colunas, self.monte, self.descarte, self.espacos, self.completas, self.jogadas))
        self._historico = (self._historico + [estado])[-30:]

    def desfazer(self):
        if not self._historico:
            return False
        self.colunas, self.monte, self.descarte, self.espacos, self.completas, self.jogadas = self._historico.pop()
        return True

    # ---------------- leitura de pilhas ----------------

    def pilha_movel(self, col):
        """Índice de onde começa a pilha que pode ser levada (palavras viradas para cima, mesma categoria)."""
        c = self.colunas[col]
        if not c or c[-1].virada or c[-1].cadeado:
            return None
        i = len(c) - 1
        if c[i].eh_categoria:
            return i
        while (i > 0 and not c[i - 1].virada and not c[i - 1].eh_categoria and not c[i - 1].cadeado
               and c[i - 1].categoria == c[i].categoria):
            i -= 1
        return i

    def cartas_de(self, origem):
        tipo = origem[0]
        if tipo == "descarte":
            return self.descarte[-1:]
        if tipo == "coluna":
            col, idx = origem[1], origem[2]
            inicio = self.pilha_movel(col)
            if inicio is None or idx < inicio:
                return []
            return self.colunas[col][idx:]
        return []

    # ---------------- regras ----------------

    def aceita(self, cartas, destino):
        if not cartas:
            return False
        primeira = cartas[0]
        if destino[0] == "espaco":
            e = self.espacos[destino[1]]
            if e is None:
                return len(cartas) == 1 and primeira.eh_categoria
            return all(not c.eh_categoria and c.categoria == e["cat"] for c in cartas)
        if destino[0] == "coluna":
            alvo = self.colunas[destino[1]]
            if not alvo:
                return True
            topo = alvo[-1]
            if topo.virada or topo.cadeado:
                return False
            if primeira.eh_categoria:
                return False
            return topo.categoria == primeira.categoria
        return False

    def mover(self, origem, destino):
        """Faz o movimento se for válido. Devolve True se moveu."""
        if self.venceu or self.perdeu:
            return False
        cartas = self.cartas_de(origem)
        if not self.aceita(cartas, destino):
            return False
        if origem[0] == "coluna" and destino == ("coluna", origem[1]):
            return False
        self._guardar()
        if origem[0] == "descarte":
            self.descarte.pop()
        else:
            del self.colunas[origem[1]][origem[2]:]
            col = self.colunas[origem[1]]
            if col and col[-1].virada:
                col[-1].virada = False
        if destino[0] == "coluna":
            self.colunas[destino[1]].extend(cartas)
        else:
            j = destino[1]
            if self.espacos[j] is None:
                c = cartas[0]
                self.espacos[j] = {"cat": c.categoria, "total": self.tamanho[c.categoria], "dentro": 0}
            else:
                self.espacos[j]["dentro"] += len(cartas)
                self.ganhos.append((len(cartas), "palavra encaixada"))
                if self.espacos[j]["dentro"] >= self.espacos[j]["total"]:
                    self.ganhos.append((10 + self.espacos[j]["total"] * 2, f"completou {self.espacos[j]['cat']}"))
                    self.espacos[j] = None
                    self.completas += 1
                    self._abrir_cadeados()
                    if self.venceu:
                        self.ganhos.append((30 + 5 * self.nivel + self.jogadas // 2, f"venceu o nível {self.nivel}"))
        self.jogadas -= 1
        return True

    def _abrir_cadeados(self):
        for col in self.colunas:
            for k in range(len(col) - 1, -1, -1):
                if col[k].cadeado and self.completas >= col[k].cadeado:
                    del col[k]
                    self.ganhos.append((5, "abriu um cadeado"))
            if col and col[-1].virada:
                col[-1].virada = False

    def comprar(self):
        """Vira uma carta do monte (ou devolve o descarte para o monte, se ele acabou)."""
        if self.venceu or self.perdeu or (not self.monte and not self.descarte):
            return False
        self._guardar()
        if self.monte:
            c = self.monte.pop()
            c.virada = False
            self.descarte.append(c)
        else:
            self.monte = list(reversed(self.descarte))
            for c in self.monte:
                c.virada = True
            self.descarte = []
        self.jogadas -= 1
        return True

    def para_espaco(self, origem):
        """Clique duplo: manda para o melhor espaço possível."""
        cartas = self.cartas_de(origem)
        if not cartas:
            return False
        ordem = [j for j, e in enumerate(self.espacos) if e is not None] + \
                [j for j, e in enumerate(self.espacos) if e is None]
        for j in ordem:
            if self.aceita(cartas, ("espaco", j)):
                return self.mover(origem, ("espaco", j))
        return False

    def dica(self):
        """Um movimento bom, ou ("monte",) se o melhor é comprar. None se não há nada."""
        origens = [("descarte",)] if self.descarte else []
        for col in range(COLUNAS):
            i = self.pilha_movel(col)
            if i is not None:
                origens.append(("coluna", col, i))
        for o in origens:                                   # 1) algo para os espaços
            cartas = self.cartas_de(o)
            for j in range(ESPACOS):
                if self.espacos[j] is not None and self.aceita(cartas, ("espaco", j)):
                    return o, ("espaco", j)
        for o in origens:                                   # 2) categoria para espaço vazio
            cartas = self.cartas_de(o)
            for j in range(ESPACOS):
                if self.espacos[j] is None and self.aceita(cartas, ("espaco", j)):
                    return o, ("espaco", j)
        for o in origens:                                   # 3) juntar palavras nas colunas (que libere algo)
            cartas = self.cartas_de(o)
            for col in range(COLUNAS):
                if self.colunas[col] and self.aceita(cartas, ("coluna", col)) and not (o[0] == "coluna" and o[1] == col):
                    if o[0] == "descarte" or o[2] > 0:
                        return o, ("coluna", col)
        if self.monte or self.descarte:
            return ("monte",)
        return None


class Progresso:
    """Nível atual, recorde e a sequência de dias da recompensa diária."""
    def __init__(self, caminho):
        self.caminho = caminho
        d = read_json(caminho, default={})
        d = d if isinstance(d, dict) else {}
        n = d.get("nivel")
        self.nivel = n if isinstance(n, int) and 1 <= n < 100000 else 1
        s = d.get("sequencia")
        self.sequencia = s if isinstance(s, int) and 0 <= s < 100000 else 0
        self.ultimo_dia = d.get("ultimo_dia") if isinstance(d.get("ultimo_dia"), str) else ""
        v = d.get("vitorias")
        self.vitorias = v if isinstance(v, int) and v >= 0 else 0

    def recompensa_do_dia(self, hoje=None):
        """Se ainda não pegou hoje: (dia da sequência, moedas). Senão None. Já marca como pego."""
        hoje = hoje or date.today()
        if self.ultimo_dia == hoje.isoformat():
            return None
        ontem = (hoje - timedelta(days=1)).isoformat()
        self.sequencia = self.sequencia + 1 if self.ultimo_dia == ontem else 1
        self.ultimo_dia = hoje.isoformat()
        self.salvar()
        dia = (self.sequencia - 1) % len(RECOMPENSA_DIARIA)
        return self.sequencia, RECOMPENSA_DIARIA[dia]

    def venceu(self):
        self.nivel += 1
        self.vitorias += 1
        self.salvar()

    def salvar(self):
        try:
            write_json(self.caminho, {"nivel": self.nivel, "sequencia": self.sequencia,
                                      "ultimo_dia": self.ultimo_dia, "vitorias": self.vitorias})
        except OSError:
            pass
