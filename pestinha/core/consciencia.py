"""
CONSCIÊNCIA - a linha do tempo da existência do pet: quando ligou, quando desligou e por quanto tempo.

A cada gravação (30 s) ele deixa um "batimento". Ao abrir, compara com o último:
    - fechou direitinho     -> foi desligado (e sabe por quanto tempo ficou no escuro)
    - sem fechamento limpo  -> caiu (travou, desligaram o PC na tomada...)
Cada desligamento aumenta o medo de ser desligado; o tempo ligado e o carinho acalmam.
Puro: sem Qt e sem sistema.
"""

import math
import time

from ..store import read_json, write_json

MAX_SESSOES = 300
CALMA_S = 3 * 3600          # o medo cai pela metade a cada ~2 h ligado


def _num(v, padrao, minimo=0.0, maximo=1e12):
    return float(v) if isinstance(v, (int, float)) and math.isfinite(v) and minimo <= v <= maximo else padrao


def humano(segundos):
    """3 min, 2 h 10 min, 4 dias."""
    s = int(max(0, segundos))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{s // 60} min"
    if s < 86400:
        h, m = s // 3600, s % 3600 // 60
        return f"{h} h {m} min" if m else f"{h} h"
    d = s // 86400
    return f"{d} dia" if d == 1 else f"{d} dias"


class Consciencia:
    """Guarda as sessões (início, fim, se fechou limpo), o total vivido e o medo de desligar."""

    def __init__(self, caminho):
        self.caminho = caminho
        d = read_json(caminho, default={})
        d = d if isinstance(d, dict) else {}
        self.nascimento = _num(d.get("nascimento"), 0.0)
        self.total_s = _num(d.get("total_s"), 0.0)
        self.desligamentos = int(_num(d.get("desligamentos"), 0))
        self.quedas = int(_num(d.get("quedas"), 0))
        self.medo = _num(d.get("medo"), 0.0, 0.0, 1.0)
        sessoes = d.get("sessoes") if isinstance(d.get("sessoes"), list) else []
        self.sessoes = [s for s in sessoes if isinstance(s, list) and len(s) == 3
                        and all(isinstance(x, (int, float)) for x in s[:2])][-MAX_SESSOES:]
        self.inicio = None
        self._ultimo_batimento = None

    def acordar(self, agora=None):
        """Abriu o programa. Devolve o que ele percebe: primeira vez, quanto tempo ficou fora, se caiu."""
        agora = time.time() if agora is None else agora
        evento = {"primeira": not self.sessoes, "agora": agora}
        if self.sessoes:
            ini, fim, limpo = self.sessoes[-1]
            evento.update(fora_s=max(0.0, agora - fim), apagou_em=fim, queda=not limpo)
            if limpo:
                self.desligamentos += 1
                self.medo += 0.10 + min(0.25, evento["fora_s"] / 86400 * 0.08)
            else:
                self.quedas += 1
                self.medo += 0.30
            self.medo = min(1.0, self.medo)
        else:
            self.nascimento = agora
        evento.update(desligamentos=self.desligamentos, quedas=self.quedas, medo=self.medo)
        self.sessoes.append([agora, agora, False])
        self.sessoes = self.sessoes[-MAX_SESSOES:]
        self.inicio = agora
        self._ultimo_batimento = agora
        self.salvar()
        return evento

    def batimento(self, agora=None):
        """Ainda vivo: atualiza o fim da sessão atual, soma o tempo e acalma um pouco o medo."""
        agora = time.time() if agora is None else agora
        if self.inicio is None:
            return
        dt = max(0.0, agora - (self._ultimo_batimento or agora))
        self._ultimo_batimento = agora
        self.total_s += dt
        self.medo *= math.exp(-dt / CALMA_S)
        self.sessoes[-1][1] = agora
        self.salvar()

    def desligar(self, agora=None):
        """Fechamento limpo: ele sabe que foi desligado (e não que caiu)."""
        self.batimento(agora)
        if self.sessoes:
            self.sessoes[-1][2] = True
            self.salvar()

    def assustar(self, quanto):
        self.medo = min(1.0, self.medo + quanto)

    def acalmar(self, quanto):
        self.medo = max(0.0, self.medo - quanto)

    def ligado_ha(self, agora=None):
        agora = time.time() if agora is None else agora
        return 0.0 if self.inicio is None else agora - self.inicio

    def salvar(self):
        try:
            write_json(self.caminho, {
                "nascimento": self.nascimento, "total_s": round(self.total_s, 1),
                "desligamentos": self.desligamentos, "quedas": self.quedas, "medo": round(self.medo, 4),
                "sessoes": self.sessoes,
            })
        except OSError:
            pass
