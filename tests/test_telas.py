"""Passa por todas as telas sem abrir janela (driver de vídeo "dummy"),
só para garantir que nada quebra ao desenhar."""
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from jogo.ia import DIFICULDADES, IA  # noqa: E402
from jogo.interface import Jogo  # noqa: E402
from jogo.tela_batalha import TelaBatalha  # noqa: E402
from jogo.tela_selecao import TelaSelecao  # noqa: E402


def tecla(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


@pytest.fixture
def jogo():
    j = Jogo()
    yield j
    pygame.quit()


def rodar(jogo, quadros, dt=1 / 60):
    for _ in range(quadros):
        jogo.atual.atualizar(dt)
        jogo.atual.desenhar(jogo.tela)


def test_do_titulo_ate_o_fim_da_luta(jogo):
    rodar(jogo, 5)
    jogo.tratar(jogo.atual.evento(tecla(pygame.K_RETURN)))
    assert isinstance(jogo.atual, TelaSelecao)

    for k in (pygame.K_1, pygame.K_2, pygame.K_3):
        jogo.tratar(jogo.atual.evento(tecla(k)))
    rodar(jogo, 5)
    jogo.tratar(jogo.atual.evento(tecla(pygame.K_RETURN)))
    batalha = jogo.atual
    assert isinstance(batalha, TelaBatalha)

    # uma IA joga no lugar do jogador
    ia = IA(batalha.combate, 0, DIFICULDADES[2], random.Random(0))
    batalha.comando_jogador = ia.comando
    for _ in range(60 * 240):
        rodar(jogo, 1)
        if batalha.fim_visivel:
            break
    assert batalha.combate.terminou

    batalha.evento(tecla(pygame.K_p))  # pausa não deve quebrar no fim
    jogo.tratar(batalha.evento(tecla(pygame.K_r)))
    assert jogo.atual is not batalha  # revanche
    rodar(jogo, 200)

    jogo.atual.evento(tecla(pygame.K_p))
    rodar(jogo, 5)
    jogo.tratar(jogo.atual.evento(tecla(pygame.K_ESCAPE)))
    assert isinstance(jogo.atual, TelaSelecao)
    assert len(jogo.atual.escolhidos) == 3  # lembra o time escolhido
