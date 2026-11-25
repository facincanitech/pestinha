"""
MEME - ele faz memes: pega um desenho dele (ou o modelo que está estudando) e põe uma legenda
das frases da persona do momento, em cima e embaixo, letra branca com contorno preto.

Guarda em memory/pets/<pet>/memes_criados/. Postar na rede é sempre com o tutor aprovando.
"""

import random
from datetime import datetime

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen

from .. import config

LADO = 420


def _imagens(pasta_do_pet):
    pasta = pasta_do_pet / "desenhos"
    if not pasta.exists():
        return []
    return sorted(pasta.rglob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)


def _legenda(p, texto, area, em_cima):
    fonte = QFont("Impact", 22)
    fonte.setBold(True)
    medida = QFontMetricsF(fonte)
    while medida.horizontalAdvance(texto) > area.width() * 1.9 and fonte.pointSize() > 12:
        fonte.setPointSize(fonte.pointSize() - 1)
        medida = QFontMetricsF(fonte)
    # quebra em até duas linhas
    palavras, linhas, atual = texto.upper().split(), [], ""
    for w in palavras:
        teste = (atual + " " + w).strip()
        if medida.horizontalAdvance(teste) > area.width() - 16 and atual:
            linhas.append(atual)
            atual = w
        else:
            atual = teste
    linhas.append(atual)
    linhas = linhas[:3]
    altura = medida.height()
    y0 = area.top() + 8 + medida.ascent() if em_cima else area.bottom() - 8 - altura * (len(linhas) - 1) - medida.descent()
    for i, linha in enumerate(linhas):
        x = area.center().x() - medida.horizontalAdvance(linha) / 2
        caminho = QPainterPath()
        caminho.addText(x, y0 + i * altura, fonte, linha)
        p.setPen(QPen(QColor("#000000"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawPath(caminho)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawPath(caminho)


def fazer_meme(pasta_do_pet, conteudo, imagem=None):
    """Cria um meme e devolve o caminho do arquivo (ou None se não tiver desenho nem frase)."""
    if imagem is None:
        imagens = _imagens(pasta_do_pet)
        if not imagens:
            return None
        imagem = random.choice(imagens[:12])
    img = QImage(str(imagem))
    if img.isNull():
        return None
    notas = config.Notes(conteudo.notes)
    notas._reload()
    frases = [f for f in notas.lines if f.strip()]
    if not frases:
        frases = ["quando você salva o arquivo", "e o código funciona de primeira"]
    cima = random.choice(frases)
    baixo = random.choice([f for f in frases if f != cima] or frases)
    base = img.scaled(LADO, LADO, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    out = QImage(base.size(), QImage.Format_RGB32)
    out.fill(QColor("#ffffff"))
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    p.drawImage(0, 0, base)
    area = QRectF(0, 0, out.width(), out.height())
    _legenda(p, cima, area, True)
    _legenda(p, baixo, area, False)
    p.end()
    pasta = pasta_do_pet / "memes_criados"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / f"meme_{datetime.now():%Y%m%d_%H%M%S}.png"
    out.save(str(destino), "PNG")
    return destino


def memes_feitos(pasta_do_pet):
    pasta = pasta_do_pet / "memes_criados"
    if not pasta.exists():
        return []
    return sorted(pasta.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
