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
    "papelao": ("casa", "Caixa de papelão", 60, 1),
    "casinha": ("casa", "Casinha de madeira", 300, 2),
    "casa": ("casa", "Casa de tijolo", 1200, 3),
    "mapple": ("eletronico", "Celular Mapple", 0, 1),
    "notebook": ("eletronico", "Notebook", 400, 2),
    "pc_gamer": ("eletronico", "PC gamer", 1500, 3),
    "chapeu_cowboy": ("chapeu", "Chapéu de cowboy", 120, 0),
    "bone": ("chapeu", "Boné", 80, 0),
    "coroa": ("chapeu", "Coroa", 2000, 0),
    "cama": ("movel", "Caminha", 90, 0),
    "tv": ("movel", "TV", 250, 0),
    "tapete": ("movel", "Tapete", 40, 0),
    "planta": ("movel", "Plantinha", 60, 0),
    "luminaria": ("movel", "Luminária", 70, 0),
}
CATEGORIAS = {"casa": "Casas", "eletronico": "Eletrônicos", "chapeu": "Chapéus", "movel": "Móveis"}
EQUIPAVEIS = ("casa", "eletronico", "chapeu")     # um de cada por vez; móveis ficam todos na casa


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
        self.itens = {i for i in itens if i in CATALOGO} | {"mapple"}
        eq = d.get("equipado") if isinstance(d.get("equipado"), dict) else {}
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
        if cat == "chapeu" and self.equipado.get("chapeu") == item:
            del self.equipado["chapeu"]          # clicar de novo tira o chapéu
        else:
            self.equipado[cat] = item
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

    def salvar(self):
        try:
            write_json(self.caminho, {"moedas": self.moedas, "ganho_total": self.ganho_total,
                                      "itens": sorted(self.itens), "equipado": self.equipado,
                                      "extrato": self.extrato})
        except OSError:
            pass
