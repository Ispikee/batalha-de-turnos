"""Testes das regras da batalha. Rode com: pytest"""
import random

import pytest

from jogo.batalha import CUSTO_MP, Acao, Batalha, calcular_dano
from jogo.personagem import criar_heroi, criar_inimigo


def nova_batalha(semente: int = 42) -> Batalha:
    return Batalha(criar_heroi(), criar_inimigo(), rng=random.Random(semente))


def test_ataque_tira_hp_do_inimigo():
    batalha = nova_batalha()
    resultado = batalha.executar(batalha.heroi, Acao.ATACAR)
    assert resultado.dano > 0
    assert batalha.inimigo.hp == batalha.inimigo.hp_max - resultado.dano


def test_defender_corta_o_dano_pela_metade():
    atacante, alvo = criar_inimigo(), criar_heroi()
    normal, _ = calcular_dano(atacante, alvo, random.Random(7))
    alvo.defendendo = True
    defendendo, _ = calcular_dano(atacante, alvo, random.Random(7))
    assert defendendo == pytest.approx(normal / 2, abs=1)


def test_magia_gasta_mp():
    batalha = nova_batalha()
    batalha.executar(batalha.heroi, Acao.MAGIA)
    assert batalha.heroi.mp == batalha.heroi.mp_max - CUSTO_MP[Acao.MAGIA]


def test_sem_mp_nao_pode_usar_magia():
    batalha = nova_batalha()
    batalha.heroi.mp = 0
    assert not batalha.pode_usar(batalha.heroi, Acao.MAGIA)
    with pytest.raises(ValueError):
        batalha.executar(batalha.heroi, Acao.MAGIA)


def test_nao_pode_curar_com_hp_cheio():
    batalha = nova_batalha()
    assert not batalha.pode_usar(batalha.heroi, Acao.CURAR)
    batalha.heroi.hp = 50
    assert batalha.pode_usar(batalha.heroi, Acao.CURAR)


def test_cura_nao_passa_do_maximo():
    batalha = nova_batalha()
    batalha.heroi.hp = batalha.heroi.hp_max - 3
    resultado = batalha.executar(batalha.heroi, Acao.CURAR)
    assert resultado.cura == 3
    assert batalha.heroi.hp == batalha.heroi.hp_max


def test_inimigo_ferido_prefere_curar():
    batalha = nova_batalha()
    batalha.inimigo.hp = 10
    escolhas = [batalha.escolher_acao_inimigo() for _ in range(200)]
    assert escolhas.count(Acao.CURAR) > 100


@pytest.mark.parametrize("semente", range(20))
def test_batalha_sempre_termina_com_um_vencedor(semente):
    batalha = nova_batalha(semente)
    sorteio = random.Random(semente)
    for _ in range(500):
        if batalha.terminou:
            break
        opcoes = [a for a in Acao if batalha.pode_usar(batalha.heroi, a)]
        batalha.executar(batalha.heroi, sorteio.choice(opcoes))
        if batalha.terminou:
            break
        batalha.executar(batalha.inimigo, batalha.escolher_acao_inimigo())

    assert batalha.terminou
    perdedor = batalha.oponente_de(batalha.vencedor)
    assert perdedor.hp == 0
    assert batalha.heroi.hp >= 0 and batalha.inimigo.hp >= 0
