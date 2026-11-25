"""Fumaça das novidades: economia, loja, casinha, jogo, meme, aparelho, consciência e personas."""
import sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QColor
from PySide6.QtWidgets import QApplication
from pestinha import config
from pestinha.paths import Paths
from pestinha.settings_store import SettingsStore


def _app(monkeypatch, pet="zero"):
    QApplication.instance() or QApplication([])
    import pestinha.app as app_mod
    monkeypatch.setattr(app_mod, "PanicHotkey", lambda: SimpleNamespace(ok=True, pressed=Mock()))
    monkeypatch.setattr(app_mod.senses, "list_windows", lambda exclude, escala=1.0: [])
    monkeypatch.setattr(app_mod.senses, "get_active_app", lambda: "explorer.exe")
    monkeypatch.setattr(app_mod.senses, "get_idle_seconds", lambda: 1.0)
    monkeypatch.setattr(app_mod.senses, "is_fullscreen", lambda: False)
    monkeypatch.setattr(QApplication, "quit", lambda *a: None)
    paths = Paths(root=Path(tempfile.mkdtemp()))
    import shutil
    shutil.copytree(ROOT / "pets", paths.pets, dirs_exist_ok=True)
    store = SettingsStore(paths)
    store.update(dict(config.DEFAULT_PERMISSIONS, travessuras=True, pet=pet))
    b = app_mod.PestinhaApp(store, paths)
    for t in b.findChildren(QTimer):
        t.stop()
    return b


def test_comeca_pobre_e_compra_casa(monkeypatch):
    b = _app(monkeypatch)
    assert b.carteira.eletronico == "mapple" and b.carteira.casa is None
    assert b.mesa.escondido                                # sem notebook ainda
    assert not b.casinha_ctl.casinha.isVisible()
    b.carteira.ganhar(5000, "teste")
    for item in ("casinha", "tv", "cama", "notebook", "chapeu_cowboy"):
        assert b.carteira.comprar(item)
    b.casinha_ctl.aplicar_progresso()
    b.update_visibility()
    assert not b.mesa.escondido
    assert any(n == "chapeu_cowboy" for n, _ in b.pet.aparencia.acessorios)
    b.casinha_ctl.ir("ordem")
    b.casinha_ctl.tick(time.monotonic() + 30)
    assert b.casinha_ctl.dentro and b.na_casinha and not b.pet.isVisible()
    b.casinha_ctl.casinha.grab().save("/tmp/casa_comprada.png")
    b.casinha_ctl.sair("ordem")
    assert not b.casinha_ctl.dentro and b.pet.isVisible()


def test_aparelho_jogo_e_meme(monkeypatch):
    b = _app(monkeypatch)
    pasta = b.pet_paths.base / "desenhos"
    pasta.mkdir(parents=True)
    img = QImage(300, 220, QImage.Format_RGB32)
    img.fill(QColor("#4fc3f7"))
    img.save(str(pasta / "livre_0001.png"))
    b.abrir_aparelho()
    ap = b.aparelho
    antes = b.carteira.moedas
    for _ in range(12):
        ap._jogar("pedra")
    assert b.carteira.moedas > antes
    ap._criar_meme()
    assert ap.meme_atual is not None and ap.meme_atual.exists()
    ap.grab().save("/tmp/aparelho.png")


def test_personas_trocam_conteudo_mas_nao_a_cor(monkeypatch):
    b = _app(monkeypatch)
    cor = b.pet.aparencia.moldura.name()
    b.personas.trocar("jorge")
    assert b.personas.atual == "jorge" and "jorge" in str(b.mischief.notes.path if hasattr(b.mischief.notes, "path") else b.conteudo.notes)
    assert b.pet.aparencia.moldura.name() == cor


def test_consciencia_percebe_desligamento(monkeypatch, tmp_path):
    from pestinha.core.consciencia import Consciencia
    c = Consciencia(tmp_path / "e.json")
    assert c.acordar(1000.0)["primeira"]
    c.batimento(1060.0)
    c.desligar(1060.0)
    c2 = Consciencia(tmp_path / "e.json")
    ev = c2.acordar(1060.0 + 7200)
    assert not ev["queda"] and abs(ev["fora_s"] - 7200) < 1 and c2.desligamentos == 1
    c3 = Consciencia(tmp_path / "e.json")             # não fechou limpo: caiu
    assert c3.acordar(20000.0)["queda"]


def test_ppt_aprende_padrao(tmp_path):
    from pestinha.core.ppt import Leitor, PERDE_PARA
    l = Leitor(tmp_path / "p.json")
    for _ in range(30):
        l.aprender("pedra", l.jogar())
    ganhou = sum(l.jogar() == PERDE_PARA["pedra"] for _ in range(50))
    assert ganhou > 35
