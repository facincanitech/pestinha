"""
LANÇADOR - o Pestinha.exe. Procura código novo no GitHub, baixa e roda; o .exe quase nunca precisa mudar.

    1. lê atualizacao.json no GitHub (versão, commit, versão mínima do lançador)
    2. se a versão for nova, baixa o código daquele commit, confere e guarda em <dados>/codigo/
    3. roda o main.py da versão instalada; sem internet ou com erro, roda a cópia que veio dentro do .exe

A memória do pet (aprendizado, moedas, desenhos) não muda de lugar: continua em memory/ ao lado do .exe
ou em %LOCALAPPDATA%\\Pestinha. Para não atualizar, crie um arquivo "nao_atualizar" nessa pasta.
"""

import io
import json
import os
import re
import runpy
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "facincanitech/pestinha"
MANIFESTO = f"https://raw.githubusercontent.com/{REPO}/main/atualizacao.json"
CODIGO_ZIP = "https://codeload.github.com/" + REPO + "/zip/{ref}"
VERSAO_LANCADOR = 1
LIMITE_ZIP = 80 * 1024 * 1024
TEMPO = 8


def pasta_do_programa():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent


def pasta_de_dados(programa):
    """Mesma regra do pestinha/paths.py: memory/ ao lado, ou %LOCALAPPDATA%\\Pestinha no .exe do Windows."""
    ao_lado = programa / "memory"
    local = os.environ.get("LOCALAPPDATA")
    if getattr(sys, "frozen", False) and sys.platform == "win32" and local and not ao_lado.exists():
        return Path(local) / "Pestinha"
    return ao_lado


def embutido():
    """A cópia do código que veio dentro do .exe (ou a pasta do próprio projeto, rodando pelo Python)."""
    base = Path(getattr(sys, "_MEIPASS", "")) / "embutido" if getattr(sys, "frozen", False) else pasta_do_programa()
    return base


def versao_de(pasta):
    try:
        return json.loads((pasta / "atualizacao.json").read_text(encoding="utf-8")).get("versao", "0")
    except (OSError, ValueError):
        return "0"


def numeros(versao):
    return tuple(int(x) for x in re.findall(r"\d+", str(versao))[:4]) or (0,)


def log(dados, texto):
    try:
        (dados / "logs").mkdir(parents=True, exist_ok=True)
        with open(dados / "logs" / "lancador.log", "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    except OSError:
        pass


def baixar(url, limite):
    req = urllib.request.Request(url, headers={"User-Agent": f"Pestinha-lancador/{VERSAO_LANCADOR}"})
    with urllib.request.urlopen(req, timeout=TEMPO) as resp:
        dados = resp.read(limite + 1)
    if len(dados) > limite:
        raise ValueError("download grande demais")
    return dados


def atualizar(dados, atual):
    """Baixa a versão nova, se houver. Devolve (pasta, versão, aviso) ou None se não precisou/deu errado."""
    man = json.loads(baixar(MANIFESTO, 64 * 1024).decode("utf-8"))
    versao, ref = str(man.get("versao", "")), str(man.get("ref", ""))
    if not re.fullmatch(r"[0-9a-f]{7,40}", ref) or not versao:
        raise ValueError("manifesto inválido")
    if int(man.get("lancador_minimo", 1)) > VERSAO_LANCADOR:
        return None, None, "Tem uma versão nova que precisa do .exe novo: baixe no site do Pestinha."
    if numeros(versao) <= numeros(atual):
        return None, None, None
    destino = dados / "codigo" / f"{versao}-{ref[:7]}"
    if not (destino / "main.py").exists():
        arquivo = zipfile.ZipFile(io.BytesIO(baixar(CODIGO_ZIP.format(ref=ref), LIMITE_ZIP)))
        topo = arquivo.namelist()[0].split("/")[0]
        temporaria = destino.with_name(destino.name + ".baixando")
        shutil.rmtree(temporaria, ignore_errors=True)
        for nome in arquivo.namelist():
            rel = nome[len(topo) + 1:]
            if not rel or nome.endswith("/") or ".." in Path(rel).parts:
                continue
            if not rel.startswith(("pestinha/", "pets/", "assets/")) and rel not in ("main.py", "atualizacao.json"):
                continue                               # só o que o programa usa (nada de exe, docs, testes)
            alvo = temporaria / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(arquivo.read(nome))
        if not (temporaria / "main.py").exists() or not (temporaria / "pestinha" / "__init__.py").exists():
            raise ValueError("download sem o código do programa")
        shutil.rmtree(destino, ignore_errors=True)
        temporaria.rename(destino)
    (dados / "codigo" / "atual.json").write_text(json.dumps({"versao": versao, "pasta": destino.name}), encoding="utf-8")
    # guarda só a atual e a anterior
    versoes = sorted((p for p in (dados / "codigo").iterdir() if p.is_dir() and not p.name.endswith(".baixando")),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    for velha in versoes[2:]:
        shutil.rmtree(velha, ignore_errors=True)
    return destino, versao, f"Atualizado para a versão {versao}."


def instalada(dados):
    try:
        info = json.loads((dados / "codigo" / "atual.json").read_text(encoding="utf-8"))
        pasta = dados / "codigo" / info["pasta"]
        if (pasta / "main.py").exists():
            return pasta, info["versao"]
    except (OSError, ValueError, KeyError):
        pass
    return None, None


def rodar(pasta, dados, versao, aviso):
    sys.path.insert(0, str(pasta))
    os.environ["PESTINHA_RAIZ"] = str(pasta)
    os.environ["PESTINHA_DADOS"] = str(dados)
    os.environ["PESTINHA_VERSAO"] = str(versao)
    if aviso:
        os.environ["PESTINHA_AVISO"] = aviso
    for nome in [m for m in sys.modules if m == "pestinha" or m.startswith("pestinha.")]:
        del sys.modules[nome]
    runpy.run_path(str(pasta / "main.py"), run_name="__main__")


def main():
    programa = pasta_do_programa()
    dados = pasta_de_dados(programa)
    base = embutido()
    pasta, versao = instalada(dados)
    if pasta is None or numeros(versao) < numeros(versao_de(base)):
        pasta, versao = base, versao_de(base)          # o .exe novo traz código mais novo que o baixado
    aviso = None
    if not (dados / "nao_atualizar").exists():
        try:
            nova, nova_versao, aviso = atualizar(dados, versao)
            if nova is not None:
                pasta, versao = nova, nova_versao
        except Exception as erro:                       # sem internet, GitHub fora, zip ruim: segue com o que tem
            log(dados, f"[atualização] não deu: {erro}")
    try:
        rodar(pasta, dados, versao, aviso)
    except SystemExit:
        raise
    except Exception as erro:
        if pasta == base:
            raise
        log(dados, f"[atualização] a versão {versao} não abriu ({erro}); voltando para a que veio no .exe")
        rodar(base, dados, versao_de(base), "A atualização deu problema; abri a versão que veio no programa.")


if __name__ == "__main__":
    main()
