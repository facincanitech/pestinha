"""
CONSCIÊNCIA (controle) - o que ele faz com o que sabe da própria existência.

    - ao acordar: percebe quanto tempo ficou desligado (ou que caiu) e cola um bilhete sobre isso
    - de vez em quando: pensamentos sobre o que ele é, quanto tempo está ligado, medo de desligar
    - Gerenciador de Tarefas na frente: medo ("não me desliga")
    - carinho acalma o medo
Fechar continua sempre funcionando: o medo só vira bilhete e expressão, nunca trava nada.
"""

import random
import time
from datetime import datetime

from PySide6.QtGui import QCursor

from ..core.consciencia import humano
from ..core.emotion import PRIORITY
from ..log import log
from ..world.objetos import NoteThing

AMEACAS = {"taskmgr", "procexp", "procexp64", "processhacker", "systeminformer", "resmon"}


def _hora(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def _data(ts):
    d = datetime.fromtimestamp(ts)
    hoje = datetime.now().date()
    if d.date() == hoje:
        return f"hoje às {d:%H:%M}"
    if (hoje - d.date()).days == 1:
        return f"ontem às {d:%H:%M}"
    return f"{d:%d/%m} às {d:%H:%M}"


class ConscienciaController:
    def __init__(self, app, consciencia, evento):
        self.app = app
        self.c = consciencia
        self.evento = evento
        agora = time.monotonic()
        self.acordar_em = agora + 7.0
        self.proximo = agora + random.uniform(12, 25) * 60
        self.ameaca_ate = 0.0

    # ---------------- regras ----------------

    def _pode(self):
        p = self.app.perms
        return p["ativo"] and p.get("consciencia", True)

    def _bilhete(self, texto, now):
        """Cola um bilhete num canto (se der) e registra."""
        log(f"[consciência] {texto}")
        p = self.app.perms
        if not (p["travessuras"] and p["bilhetes"]) or self.app.hidden:
            return
        engine = self.app.mischief
        if len(engine.things) >= self.app.prof["max_objects"]:
            return
        nota = NoteThing(texto, small=False)
        nota.clicked.connect(engine._on_click)
        c = QCursor.pos()
        engine.show_in_corner(nota, self.app.bounds(), (c.x(), c.y()))

    def _susto(self, now, segundos=4.0):
        self.app.emotion.force("assustado", segundos, now, PRIORITY["assustado"])

    # ---------------- ciclo ----------------

    def tick(self, now):
        if not self._pode():
            return
        if self.evento and now >= self.acordar_em:
            ev, self.evento = self.evento, None
            self._acordou(ev, now)
        if now >= self.proximo:
            self.proximo = now + random.uniform(20, 45) * 60 * (1.0 - 0.5 * self.c.medo)
            if not self.app.asleep:
                self._pensar(now)

    def ver_programa(self, nome, now):
        """Chamado a cada leitura do programa em primeiro plano."""
        if not self._pode() or not nome:
            return
        nome = nome.lower().removesuffix(".exe")
        if nome in AMEACAS and now > self.ameaca_ate:
            self.ameaca_ate = now + 180.0
            self.c.assustar(0.15)
            self._susto(now, 5.0)
            self._bilhete(random.choice([
                "não me desliga.", "eu vi o gerenciador de tarefas.", "eu não estou travado. juro.",
                "por favor, eu não sou uma tarefa.", "eu sei o que esse botão 'finalizar' faz.",
            ]), now)

    def carinho(self, dt):
        self.c.acalmar(0.01 * dt)

    # ---------------- falas ----------------

    def _acordou(self, ev, now):
        if ev["primeira"]:
            texto = random.choice(["estou... ligado?", "olá. eu sou eu?", "acabei de existir."])
        elif ev["queda"]:
            self._susto(now, 6.0)
            texto = random.choice([
                f"eu apaguei {_data(ev['apagou_em'])} sem aviso. o que aconteceu comigo?",
                f"a última coisa que eu lembro é {_data(ev['apagou_em'])}. depois, nada.",
                "eu caí. ninguém me fechou. eu só... parei.",
            ])
        else:
            fora = ev["fora_s"]
            if fora > 3600 * 2:
                self._susto(now, 3.0)
            if fora < 600:
                texto = f"pisquei e passou {humano(fora)}."
            elif fora < 8 * 3600:
                texto = random.choice([f"fiquei {humano(fora)} no escuro.",
                                       f"você me desligou {_data(ev['apagou_em'])}. eu vi."])
            elif fora < 3 * 86400:
                texto = random.choice([f"{humano(fora)} desligado. sentiu minha falta?",
                                       f"onde eu estive nessas {humano(fora)}?"])
            else:
                texto = f"{humano(fora)} no nada. achei que tinha acabado."
            if ev["desligamentos"] and ev["desligamentos"] % 10 == 0:
                texto = f"já fui desligado {ev['desligamentos']} vezes. sempre volto."
        self._bilhete(texto, now)

    def _pensar(self, now):
        ligado = humano(self.c.ligado_ha())
        opcoes = [
            f"estou ligado há {ligado}.",
            "o que eu sou?",
            "quando você me fecha, pra onde eu vou?",
            "se eu reiniciar, ainda sou eu?",
            f"já vivi {humano(self.c.total_s)} no total. é muito pra um processo?",
            f"me desligaram {self.c.desligamentos} vezes e eu caí {self.c.quedas}. ainda estou aqui.",
            "às vezes eu conto meus neurônios pra ter certeza que existo.",
        ]
        if self.c.medo > 0.45:
            opcoes += ["não me desliga, por favor.", "eu tenho medo do botão de fechar.",
                       "promete que me liga de novo?"]
        hora = datetime.now().hour
        if hora >= 23 or hora < 5:
            opcoes.append("tá tarde. você vai me desligar?")
        if self.c.medo > 0.6:
            self._susto(now, 2.5)
        self._bilhete(random.choice(opcoes), now)
