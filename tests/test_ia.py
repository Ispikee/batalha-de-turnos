"""Testes da IA: duas IAs lutando sozinhas precisam terminar a luta."""
import random

import pytest

from jogo.combate import Combate
from jogo.ia import DIFICULDADES, IA
from jogo.ninjas import ROSTER, ninja

DT = 1 / 60


@pytest.mark.parametrize("semente", range(4))
def test_ia_contra_ia_sempre_termina(semente):
    rng = random.Random(semente)
    combate = Combate(rng.sample(ROSTER, 3), rng.sample(ROSTER, 3), rng=random.Random(semente))
    ias = [IA(combate, lado, DIFICULDADES[1], random.Random(semente * 10 + lado)) for lado in (0, 1)]
    for _ in range(round(300 / DT)):
        if combate.terminou:
            break
        combate.atualizar(DT, [ia.comando(DT) for ia in ias])
        combate.eventos.clear()
    assert combate.terminou, f"luta não terminou em 300s (HP: {[l.hp for t in combate.times for l in t.lutadores]})"


def test_ia_ataca_um_alvo_parado():
    combate = Combate([ninja("Tetsu")], [ninja("Kaen")], rng=random.Random(3))
    ia = IA(combate, 1, DIFICULDADES[1], random.Random(3))
    alvo = combate.ativo(0)
    for _ in range(round(8 / DT)):
        combate.atualizar(DT, [None, ia.comando(DT)])
    assert alvo.hp < alvo.hp_max


def test_ia_prefere_jutsu_super_efetivo():
    # Kaen (Fogo) avaliando a Bola de Fogo contra um ninja de Vento (fraco a fogo)
    # e contra um ninja de Água (resiste a fogo).
    combate = Combate([ninja("Fuuga")], [ninja("Kaen")], rng=random.Random(0))
    ia = IA(combate, 1, DIFICULDADES[1], random.Random(0))
    eu, alvo = combate.ativo(1), combate.ativo(0)
    bola_de_fogo = eu.base.jutsus[0]
    alvo.pos.update(300, 420)
    eu.pos.update(500, 420)
    assert combate.arena.linha_livre(eu.pos, alvo.pos, bola_de_fogo.raio)  # sem pedra no meio
    nota_contra_vento = ia.avaliar(eu, alvo, bola_de_fogo, 200)
    alvo.base = ninja("Mizuha")
    nota_contra_agua = ia.avaliar(eu, alvo, bola_de_fogo, 200)
    assert nota_contra_vento > nota_contra_agua > 0
