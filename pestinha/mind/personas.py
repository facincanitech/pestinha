"""
PERSONAS - o mesmo pet (mesmo cérebro, memória e cor) troca de jeito de falar conforme o momento.

No pets/<pet>.json:
    "personas": {"trabalho": "jorge", "de_boa": "bryan", "pensativo": "zero"}
Cada persona é o CONTEÚDO de outro personagem (recadinhos, bilhetes tristes, cartazes e memes).
A aparência continua a do pet escolhido: o Zero fica azul mesmo falando como o Jorge.

    trabalho   você está programando ou desenhando
    de_boa     ele está feliz ou contente
    pensativo  curioso, observando ou triste
Fora disso, volta para o próprio conteúdo. A troca só acontece se o momento durar (sem piscar).
"""

import time

from .. import config
from ..log import log

FIRMEZA_S = 20.0            # o momento precisa durar isto para ele mudar de persona


class Personas:
    def __init__(self, app, mapa):
        self.app = app
        validos = set(config.list_pets(app.paths))
        self.mapa = {k: v for k, v in (mapa or {}).items() if v in validos}
        self.base = app.pet_id
        self.atual = app.pet_id
        self.querida = None
        self.desde = 0.0
        self.proximo = 0.0

    @property
    def ativa(self):
        return bool(self.mapa)

    def _desejada(self):
        a = self.app
        if a.activity in ("PROGRAMMING", "DESIGNING") and "trabalho" in self.mapa:
            return self.mapa["trabalho"]
        emocao = a.emotion.current
        if emocao in ("feliz", "contente") and "de_boa" in self.mapa:
            return self.mapa["de_boa"]
        if emocao in ("curioso", "observando", "triste") and "pensativo" in self.mapa:
            return self.mapa["pensativo"]
        return self.base

    def tick(self, now):
        if not self.ativa or now < self.proximo:
            return
        self.proximo = now + 1.0
        alvo = self._desejada()
        if alvo != self.querida:
            self.querida, self.desde = alvo, now
            return
        if alvo != self.atual and now - self.desde >= FIRMEZA_S:
            self.trocar(alvo)

    def trocar(self, pet_id):
        """Troca só o conteúdo (frases, cartazes, memes). Cérebro, memória e cor continuam."""
        a = self.app
        conteudo = a.paths.conteudo(pet_id)
        a.conteudo = conteudo
        a.mischief.paths = conteudo
        a.mischief.notes = config.Notes(conteudo.notes)
        a.mischief.notes_sad = config.Notes(conteudo.notes_sad)
        a.protest.signs_path = conteudo.signs
        a.sad.signs_path = conteudo.signs
        self.atual = pet_id
        nome = config.load_pet(a.paths, pet_id)["nome"]
        log(f"[persona] agora no modo {nome}")
