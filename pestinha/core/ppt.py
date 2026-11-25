"""
PEDRA, PAPEL E TESOURA - ele aprende o seu padrão.

Guarda quantas vezes você jogou cada coisa depois das suas duas últimas jogadas
(cadeia de Markov de ordem 2, com recuo para ordem 1 e 0) e joga o que ganha da sua
jogada mais provável. No começo é sorte; depois de umas partidas ele começa a te ler.
Puro: sem Qt. Grava em memory/pets/<pet>/ppt.json.
"""

import random

from ..store import read_json, write_json

JOGADAS = ("pedra", "papel", "tesoura")
GANHA_DE = {"pedra": "tesoura", "papel": "pedra", "tesoura": "papel"}
PERDE_PARA = {v: k for k, v in GANHA_DE.items()}


def resultado(voce, ele):
    """'voce', 'ele' ou 'empate'."""
    if voce == ele:
        return "empate"
    return "voce" if GANHA_DE[voce] == ele else "ele"


class Leitor:
    def __init__(self, caminho):
        self.caminho = caminho
        d = read_json(caminho, default={})
        d = d if isinstance(d, dict) else {}
        self.contagem = d.get("contagem") if isinstance(d.get("contagem"), dict) else {}
        self.historico = [j for j in d.get("historico", []) if j in JOGADAS][-2:] if isinstance(d.get("historico"), list) else []
        placar = d.get("placar") if isinstance(d.get("placar"), dict) else {}
        self.placar = {k: int(placar.get(k, 0)) if isinstance(placar.get(k, 0), int) else 0
                       for k in ("voce", "ele", "empate")}

    def _conta(self, chave):
        c = self.contagem.get(chave)
        return c if isinstance(c, dict) else {}

    def palpite(self):
        """O que ele acha que você vai jogar (ou None, se ainda não sabe)."""
        for n in (2, 1, 0):
            if len(self.historico) < n:
                continue
            chave = "|".join(self.historico[len(self.historico) - n:]) if n else "-"
            c = self._conta(chave)
            if sum(c.values()) >= 2:
                return max(JOGADAS, key=lambda j: (c.get(j, 0), random.random()))
        return None

    def jogar(self):
        p = self.palpite()
        if p is None or random.random() < 0.12:          # às vezes chuta, para não ficar previsível
            return random.choice(JOGADAS)
        return PERDE_PARA[p]

    def aprender(self, voce, ele):
        for n in (2, 1, 0):
            if len(self.historico) < n:
                continue
            chave = "|".join(self.historico[len(self.historico) - n:]) if n else "-"
            c = dict(self._conta(chave))
            c[voce] = c.get(voce, 0) + 1
            self.contagem[chave] = c
        self.historico = (self.historico + [voce])[-2:]
        r = resultado(voce, ele)
        self.placar[r] += 1
        try:
            write_json(self.caminho, {"contagem": self.contagem, "historico": self.historico, "placar": self.placar})
        except OSError:
            pass
        return r
