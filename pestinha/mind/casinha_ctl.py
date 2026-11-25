"""
CASINHA (controle) - quando ele entra e sai do quarto, e os cosméticos dele.

Entra:
    - você manda (menu "Ir pra casinha"): vai andando até a porta e entra
    - quando dorme: vai dormir na caminha
    - quando você some (ausente): vai ver TV
Sai:
    - você manda (menu, ou clique na porta)
    - acordou / você voltou: sai depois de uns segundos
    - entrou por ordem sua: fica até você chamar (ou até cansar, ~15 min)
Dentro, ele alterna entre TV e notebook. A janela do pet some; ele aparece desenhado na casinha.
"""

import random
import time

from PySide6.QtWidgets import QMenu

from ..body.desenho_rosto import com_acessorio
from ..log import log
from ..world.casinha import Casinha

CHAPEUS = ("chapeu_cowboy", "bone", "coroa")
PRAZO_ANDAR = 12.0          # s andando até a porta; depois disso ele "chega" de qualquer jeito
CANSOU_S = 15 * 60          # entrou por ordem sua: sai sozinho depois disso


class CasinhaController:
    def __init__(self, app):
        self.app = app
        self.dentro = False
        self.indo = None            # (motivo, prazo) enquanto anda até a porta
        self.motivo = None          # por que entrou: "ordem", "sono", "ausente"
        self.entrou_em = 0.0
        self.sair_em = None
        self.atividade = "tv"
        self.troca_em = 0.0
        self.carteira = app.carteira
        self.casinha = Casinha(app, self)
        self.aplicar_progresso()

    # ---------------- cosméticos ----------------

    def aplicar_progresso(self):
        """Aplica o que ele tem: chapéu, casa (sem casa, nada de casinha) e o notebook de fora."""
        a = self.app.pet.aparencia
        for nome in CHAPEUS:
            a = com_acessorio(a, nome, self.carteira.chapeu == nome)
        self.app.pet.aparencia = a
        self.app.pet.update()
        mesa = self.app.mesa
        sem_computador = self.carteira.eletronico not in ("notebook", "pc_gamer")
        if mesa.escondido != sem_computador:
            if mesa.sentado and sem_computador:
                mesa.levantar_arrancado(time.monotonic())
                self.app.pet_state.at_desk = False
            mesa.escondido = sem_computador
            mesa._aplicar_visibilidade()
        if self.atividade == "tv" and not self.carteira.tem("tv"):
            self.atividade = "eletronico"
        if not self.carteira.casa and self.dentro:
            self.sair("sem casa")
        self.set_visible(self.app.pet.isVisible() or self.dentro)
        self.casinha.update()

    def _atividades(self):
        return ["tv", "eletronico"] if self.carteira.tem("tv") else ["eletronico"]

    # ---------------- regras ----------------

    def _ligada(self):
        return self.app.perms.get("casinha", True) and bool(self.carteira.casa)

    def _pode_andar(self):
        a = self.app
        body = a.pet.body
        return (body.grounded and not body.held and not a.in_flight and not a.castigo.dentro
                and a.castigo.fuga is None and not a.behavior.mission)

    def ir(self, motivo, now=None):
        """Manda ele para a casinha: anda até a porta e entra."""
        now = time.monotonic() if now is None else now
        if self.dentro or not self._ligada():
            return
        a = self.app
        if a.mesa.sentado:                       # levanta do notebook de fora primeiro
            a.mesa.levantar_arrancado(now)
            a.mesa.ancora_corpo = None
            a.pet_state.at_desk = False
        porta_x, _ = self.casinha.porta_global()
        self.indo = (motivo, now + PRAZO_ANDAR)
        if a.pet.isVisible():
            a.behavior.mission = ("cross", porta_x, now + PRAZO_ANDAR)
        else:
            self._entrar(motivo, now)

    def _entrar(self, motivo, now):
        a = self.app
        self.indo = None
        self.dentro = True
        self.motivo = motivo
        self.entrou_em = now
        self.sair_em = None
        self.atividade = random.choice(self._atividades())
        self.troca_em = now + random.uniform(30, 70)
        a.behavior.mission = None
        a.behavior.drop_carried()
        a.na_casinha = True
        a.update_visibility()
        log(f"[casinha] entrou ({motivo})")

    def sair(self, motivo="ordem", now=None):
        """Sai pela porta e cai no chão do lado de fora."""
        if not self.dentro:
            self.indo = None
            return
        a = self.app
        if a.asleep and motivo in ("ordem", "porta"):
            a.sleep.wake(startled=False)
        x, y = self.casinha.porta_global()
        body = a.pet.body
        body.x, body.y = x, y - 60
        body.vx = random.choice((-1, 1)) * 120.0
        body.vy = -80.0
        body.grounded = False
        self.dentro = False
        self.motivo = None
        self.sair_em = None
        a.na_casinha = False
        a.update_visibility()
        log(f"[casinha] saiu ({motivo})")

    # ---------------- ciclo (100 ms) ----------------

    def tick(self, now):
        a = self.app
        if not self._ligada():
            if self.dentro:
                self.sair("desligada", now)
            return
        if self.indo:
            motivo, prazo = self.indo
            porta_x, _ = self.casinha.porta_global()
            chegou = abs(a.pet.body.x - porta_x) < 40
            if chegou or now > prazo or not a.behavior.mission:
                self._entrar(motivo, now)
            return
        if self.dentro:
            if not a.asleep and now >= self.troca_em:
                opcoes = self._atividades()
                self.atividade = opcoes[(opcoes.index(self.atividade) + 1) % len(opcoes)] \
                    if self.atividade in opcoes else opcoes[0]
                self.troca_em = now + random.uniform(30, 70)
            querer_sair = (
                (self.motivo == "sono" and not a.asleep)
                or (self.motivo == "ausente" and a.activity != "AWAY")
                or (self.motivo == "ordem" and not a.asleep and now - self.entrou_em > CANSOU_S)
            )
            if querer_sair and self.sair_em is None:
                self.sair_em = now + random.uniform(3, 9)
            if self.sair_em is not None and now >= self.sair_em:
                self.sair(self.motivo or "vontade", now)
            return
        # fora: decide sozinho entrar
        if not a.pet.isVisible() or not self._pode_andar():
            return
        if a.asleep:
            self.ir("sono", now)
        elif a.activity == "AWAY" and random.random() < 0.002:
            self.ir("ausente", now)

    # ---------------- interação ----------------

    def clicou_no_pet(self):
        self.app.menu_caress()

    def menu(self, pos):
        menu = QMenu()
        if self.dentro:
            menu.addAction(f"Chamar o {self.app.nome} pra fora", lambda: self.sair("ordem"))
            menu.addAction("Fazer carinho", self.app.menu_caress)
            if not self.app.asleep and self.carteira.tem("tv"):
                menu.addAction("Ver TV" if self.atividade != "tv" else "Largar a TV",
                               lambda: self._trocar_atividade())
        else:
            menu.addAction(f"Mandar o {self.app.nome} pra casinha", lambda: self.ir("ordem"))
        menu.addAction("Abrir a galeria de desenhos", self.abrir_galeria)
        menu.addAction(f"Abrir o {self.app.nome_do_aparelho()} (loja, jogos, rede)", self.app.abrir_aparelho)
        menu.exec(pos)

    def abrir_galeria(self):
        """Abre no explorador a pasta dos desenhos (uma subpasta por modelo, com todas as tentativas)."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        pasta = self.app.pet_paths.base / "desenhos"
        pasta.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta)))

    def _trocar_atividade(self):
        self.atividade = "eletronico" if self.atividade == "tv" else "tv"
        self.troca_em = time.monotonic() + random.uniform(40, 80)

    def set_visible(self, visivel):
        self.casinha.setVisible(visivel and self._ligada())
