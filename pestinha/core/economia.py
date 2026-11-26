"""
ECONOMIA - moedinhas, o que ele tem e o que está usando.

Ele começa pobre: sem casa e só com um celular Mapple (a pera mordida).
Ganha moedas com carinho, tempo ligado, desenhos e joguinhos, e compra na loja:
    casas       caixa de papelão -> casinha de madeira -> casa de tijolo
    eletrônicos celular Mapple -> notebook -> PC gamer
    chapéus e móveis
Puro: sem Qt. Grava em memory/pets/<pet>/carteira.json.
"""

import math
import time

from ..store import read_json, write_json

MOEDAS_INICIAIS = 50

# id: (categoria, nome, preço, nível) - o nível ordena a evolução de casas e eletrônicos
CATALOGO = {
    "barraca": ("casa", "Barraca de camping", 150, 1),
    "casinha": ("casa", "Quarto", 400, 2),
    "mapple": ("eletronico", "Celular Mapple", 0, 1),
    "notebook": ("eletronico", "Notebook", 400, 2),
    "pc_gamer": ("eletronico", "PC gamer", 1500, 3),
    "fliperama": ("videogame", "Fliperama", 350, 1),
    "console_retro": ("videogame", "Console retrô", 500, 2),
    "console": ("videogame", "Console de última geração", 900, 3),
    "cama": ("movel", "Caminha", 90, 0),
    "tv": ("movel", "TV", 250, 0),
    "sofa": ("movel", "Sofá", 220, 0),
    "poltrona": ("movel", "Poltrona", 130, 0),
    "estante": ("movel", "Estante de livros", 160, 0),
    "caixa_som": ("movel", "Caixa de som", 180, 0),
    "tapete": ("movel", "Tapete", 40, 0),
    "planta": ("movel", "Plantinha", 60, 0),
    "luminaria": ("movel", "Luminária", 70, 0),
    "cortina_azul": ("cortina", "Cortina azul", 50, 0),
    "cortina_vermelha": ("cortina", "Cortina vermelha", 50, 0),
    "cortina_listrada": ("cortina", "Cortina listrada", 80, 0),
    "cortina_estrelas": ("cortina", "Cortina de estrelas", 120, 0),
    "bone": ("chapeu", "Boné", 80, 0),
    "gorro": ("chapeu", "Gorro", 90, 0),
    "chapeu_cowboy": ("chapeu", "Chapéu de cowboy", 120, 0),
    "cartola": ("chapeu", "Cartola", 300, 0),
    "coroa": ("chapeu", "Coroa", 2000, 0),
}
FIGURAS = {
    "barraca": "⛺", "casinha": "🛏️",
    "mapple": "📱", "notebook": "💻", "pc_gamer": "🖥️", "fliperama": "🕹️", "console_retro": "👾", "console": "🎮",
    "cama": "🛏️", "tv": "📺", "sofa": "🛋️", "poltrona": "🪑", "estante": "📚", "caixa_som": "🔊", "tapete": "🟦",
    "planta": "🪴", "luminaria": "💡", "cortina_azul": "🟦", "cortina_vermelha": "🟥", "cortina_listrada": "🎏",
    "cortina_estrelas": "✨", "bone": "🧢", "gorro": "🎅", "chapeu_cowboy": "🤠", "cartola": "🎩", "coroa": "👑",
}
CATEGORIAS = {"casa": "Casas", "eletronico": "Eletrônicos", "videogame": "Videogames", "movel": "Móveis",
              "cortina": "Cortinas", "chapeu": "Chapéus"}
FIGURA_CATEGORIA = {"casa": "🏡", "eletronico": "💻", "videogame": "🎮", "movel": "🛋️", "cortina": "🪟", "chapeu": "🎩"}
EQUIPAVEIS = ("casa", "eletronico", "chapeu", "cortina")     # um de cada por vez; o resto fica todo na casa
ANTIGOS = {"papelao": "barraca", "praia": "casinha", "casa": "casinha", "mansao": "casinha"}   # casas que saíram

# Decorar: cores e estilos do quarto (mudar custa ESTILO_PRECO moedas)
ESTILO_PRECO = 10
ESTILOS = {
    "parede": ("Parede", ["#f3e2c7", "#d7f1f5", "#f8d7e3", "#dfe8c9", "#e3dcf5", "#3b3f4a"]),
    "parede_estilo": ("Estilo da parede", ["liso", "listrado", "tijolinho", "madeira"]),
    "chao": ("Chão", ["#a8734a", "#7b5233", "#c9a06b", "#8d8d8d", "#5d7a99", "#3e2f2a"]),
    "chao_estilo": ("Estilo do chão", ["tábuas", "quadriculado", "carpete"]),
    "cama": ("Cama", ["#e55b5b", "#5c8ee5", "#5bbf7a", "#f2b84b", "#a66be0", "#333333"]),
    "sofa": ("Sofá", ["#00897b", "#c62828", "#3949ab", "#6d4c41", "#ef6c00", "#424242"]),
    "tapete": ("Tapete", ["#5f8fd6", "#e57373", "#81c784", "#ffd54f", "#ba68c8", "#90a4ae"]),
}
ESTILO_PADRAO = {k: v[1][0] for k, v in ESTILOS.items()}


def _inteiro(v, padrao=0):
    return int(v) if isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v < 1e12 else padrao


class Carteira:
    def __init__(self, caminho):
        self.caminho = caminho
        d = read_json(caminho, default=None)
        novo = not isinstance(d, dict)
        d = {} if novo else d
        self.moedas = _inteiro(d.get("moedas"), MOEDAS_INICIAIS if novo else 0)
        self.ganho_total = _inteiro(d.get("ganho_total"), self.moedas)
        itens = d.get("itens") if isinstance(d.get("itens"), list) else []
        itens = [ANTIGOS.get(i, i) for i in itens if isinstance(i, str)]
        self.itens = {i for i in itens if i in CATALOGO} | {"mapple"}
        eq = d.get("equipado") if isinstance(d.get("equipado"), dict) else {}
        eq = {c: ANTIGOS.get(i, i) for c, i in eq.items() if isinstance(i, str)}
        est = d.get("estilo") if isinstance(d.get("estilo"), dict) else {}
        self.estilo = dict(ESTILO_PADRAO)
        self.estilo.update({k: v for k, v in est.items() if k in ESTILOS and v in ESTILOS[k][1]})
        self.equipado = {c: i for c, i in eq.items() if c in EQUIPAVEIS and i in self.itens
                         and CATALOGO[i][0] == c}
        self.equipado.setdefault("eletronico", "mapple")
        self.extrato = d.get("extrato") if isinstance(d.get("extrato"), list) else []
        self.dobro_ate = 0.0                 # evento: moedas em dobro até este instante (time.time)
        if novo:
            self.salvar()

    # ---------------- ganhar e gastar ----------------

    def ganhar(self, quanto, motivo):
        if quanto <= 0:
            return 0
        if time.time() < self.dobro_ate:
            quanto *= 2
        quanto = int(round(quanto))
        self.moedas += quanto
        self.ganho_total += quanto
        self.extrato = (self.extrato + [[int(time.time()), quanto, str(motivo)[:40]]])[-60:]
        self.salvar()
        return quanto

    def pode_comprar(self, item):
        return item in CATALOGO and item not in self.itens and self.moedas >= CATALOGO[item][2]

    def comprar(self, item):
        """Compra e já equipa (se for de equipar). Devolve True se deu certo."""
        if not self.pode_comprar(item):
            return False
        cat, _nome, preco, _nivel = CATALOGO[item]
        self.moedas -= preco
        self.itens.add(item)
        self.extrato = (self.extrato + [[int(time.time()), -preco, f"comprou {item}"]])[-60:]
        if cat in EQUIPAVEIS:
            self.equipado[cat] = item
        self.salvar()
        return True

    def equipar(self, item):
        if item not in self.itens:
            return False
        cat = CATALOGO[item][0]
        if cat not in EQUIPAVEIS:
            return False
        if cat in ("chapeu", "cortina") and self.equipado.get(cat) == item:
            del self.equipado[cat]               # clicar de novo tira o chapéu (ou a cortina)
        else:
            self.equipado[cat] = item
        self.salvar()
        return True

    def mudar_estilo(self, chave, valor):
        """Troca uma cor ou estilo do quarto. Custa ESTILO_PRECO moedas. Devolve True se trocou."""
        if chave not in ESTILOS or valor not in ESTILOS[chave][1] or self.estilo.get(chave) == valor:
            return False
        if self.moedas < ESTILO_PRECO:
            return False
        self.moedas -= ESTILO_PRECO
        self.estilo[chave] = valor
        self.salvar()
        return True

    def tem(self, item):
        return item in self.itens

    # ---------------- leitura ----------------

    @property
    def casa(self):
        return self.equipado.get("casa")

    @property
    def eletronico(self):
        return self.equipado.get("eletronico", "mapple")

    @property
    def chapeu(self):
        return self.equipado.get("chapeu")

    @property
    def cortina(self):
        return self.equipado.get("cortina")

    def salvar(self):
        try:
            write_json(self.caminho, {"moedas": self.moedas, "ganho_total": self.ganho_total,
                                      "itens": sorted(self.itens), "equipado": self.equipado, "estilo": self.estilo,
                                      "extrato": self.extrato})
        except OSError:
            pass
