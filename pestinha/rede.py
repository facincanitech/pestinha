"""
REDE - a rede social dos pestinhas (Supabase), bem simples.

    - perfil público: tutor, nome do pet, cor, moedas, desenhos, dias vivo (ranking)
    - falas: frases curtinhas que ele "fala" na rede (no site aparecem na língua dos pestinhas)
    - posts: memes e pinturas, SÓ quando o tutor aprova (as imagens vêm da tela dele)

Cada pet tem uma senha secreta que fica só no seu PC (memory/pets/<pet>/rede.json); o servidor
só aceita mudanças no perfil, falas e posts de quem tem a senha.
Tudo roda em segundo plano: a rede caída nunca trava o pet.
"""

import json
import threading
import urllib.error
import urllib.request
import uuid

from .log import log
from .store import read_json, write_json

URL = "https://zwkuokmwmtssnboutvko.supabase.co"
CHAVE = "sb_publishable_Bij5CAjn0cnXrOVL677Dig_W8P9Wlhd"     # chave pública (só leitura e as funções do pet)
VERSAO = "0.9.0"
SITE = "https://facincanitech.github.io/pestinha/"
TEMPO = 12


def _pedido(metodo, caminho, corpo=None, tipo="application/json", extra=None):
    dados = corpo if isinstance(corpo, (bytes, type(None))) else json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(URL + caminho, data=dados, method=metodo)
    req.add_header("apikey", CHAVE)
    req.add_header("Authorization", f"Bearer {CHAVE}")
    if dados is not None:
        req.add_header("Content-Type", tipo)
    for k, v in (extra or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=TEMPO) as resp:
        texto = resp.read().decode("utf-8") or "null"
        return json.loads(texto) if texto.strip() else None


def _rpc(nome, args):
    return _pedido("POST", f"/rest/v1/rpc/{nome}", args)


class Rede:
    def __init__(self, pasta_do_pet):
        self.arquivo = pasta_do_pet / "rede.json"
        d = read_json(self.arquivo, default={})
        self.dados = d if isinstance(d, dict) else {}
        self.ultimo_erro = None
        self._trava = threading.Lock()

    # ---------------- estado ----------------

    @property
    def registrado(self):
        return bool(self.dados.get("id") and self.dados.get("segredo"))

    @property
    def tutor(self):
        return self.dados.get("tutor", "")

    def _salvar(self):
        try:
            write_json(self.arquivo, self.dados)
        except OSError as error:
            log(f"[rede] não salvou: {error}")

    def _fundo(self, fn, pronto=None):
        """Roda `fn` numa thread; `pronto(resultado, erro)` é chamado no fim (na thread)."""
        def rodar():
            try:
                with self._trava:
                    r = fn()
                self.ultimo_erro = None
                if pronto:
                    pronto(r, None)
            except (urllib.error.URLError, OSError, ValueError) as error:
                detalhe = error.read().decode("utf-8", "replace")[:200] if isinstance(error, urllib.error.HTTPError) else ""
                self.ultimo_erro = f"{error} {detalhe}".strip()
                log(f"[rede] erro: {self.ultimo_erro}")
                if pronto:
                    pronto(None, self.ultimo_erro)
        threading.Thread(target=rodar, daemon=True).start()

    # ---------------- ações ----------------

    def entrar(self, tutor, nome, cor, pronto=None):
        """Cria o perfil (uma vez) ou atualiza o nome do tutor."""
        def fn():
            if not self.registrado:
                r = _rpc("pst_registrar", {"p_tutor": tutor, "p_nome": nome, "p_cor": cor})
                self.dados.update(id=r["id"], segredo=r["segredo"])
            self.dados["tutor"] = tutor
            self._salvar()
            _rpc("pst_atualizar", {"p_id": self.dados["id"], "p_segredo": self.dados["segredo"],
                                   "p_dados": {"tutor": tutor, "nome": nome, "cor": cor}})
            return self.dados["id"]
        self._fundo(fn, pronto)

    def atualizar(self, stats, pronto=None):
        if not self.registrado:
            return
        stats = dict(stats, versao=VERSAO)
        self._fundo(lambda: _rpc("pst_atualizar", {"p_id": self.dados["id"], "p_segredo": self.dados["segredo"],
                                                   "p_dados": stats}), pronto)

    def falar(self, texto, pronto=None):
        if not self.registrado:
            return
        self._fundo(lambda: _rpc("pst_falar", {"p_id": self.dados["id"], "p_segredo": self.dados["segredo"],
                                               "p_texto": texto[:140]}), pronto)

    def postar(self, caminho_png, tipo, legenda, pronto=None):
        """Envia a imagem e cria o post. Só chame depois que o tutor aprovou."""
        if not self.registrado:
            return

        def fn():
            dados = caminho_png.read_bytes()
            if len(dados) > 700 * 1024:
                raise ValueError("imagem grande demais (máx. 700 KB)")
            nome = f"posts/{self.dados['id']}/{uuid.uuid4().hex[:16]}.png"
            _pedido("POST", f"/storage/v1/object/pestinha/{nome}", dados, tipo="image/png",
                    extra={"x-upsert": "false"})
            return _rpc("pst_postar", {"p_id": self.dados["id"], "p_segredo": self.dados["segredo"],
                                       "p_tipo": tipo, "p_legenda": legenda[:140], "p_imagem": nome})
        self._fundo(fn, pronto)

    def ranking(self, pronto):
        self._fundo(lambda: _pedido(
            "GET", "/rest/v1/pst_pets?select=tutor,nome,cor,moedas,desenhos,dias_vivo&order=moedas.desc&limit=20"), pronto)
