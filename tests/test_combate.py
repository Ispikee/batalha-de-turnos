"""Testes das regras do combate (sem abrir janela). Rode com: pytest"""
import random
from dataclasses import replace

import pytest
from pygame.math import Vector2

from jogo.combate import (
    ESPERA_APOS_NOCAUTE,
    QUEIMADURA_POR_SEGUNDO,
    TROCA_DURACAO,
    Combate,
    Comando,
)
from jogo.jutsus import Efeito
from jogo.naturezas import FORTE_CONTRA, POUCO_EFETIVO, SUPER_EFETIVO, Natureza, multiplicador
from jogo.ninjas import ROSTER, ninja

DT = 1 / 60


def novo_combate(time_a=("Kaen", "Mizuha", "Ganro"), time_b=("Tetsu", "Fuuga", "Shiden"), semente=1) -> Combate:
    return Combate([ninja(n) for n in time_a], [ninja(n) for n in time_b], rng=random.Random(semente))


def rodar(combate: Combate, segundos: float, a=None, b=None) -> None:
    """Avança o tempo. `a` e `b` são funções que devolvem o Comando de cada lado."""
    for _ in range(round(segundos / DT)):
        combate.atualizar(DT, [a() if a else Comando(), b() if b else Comando()])


def posicionar(combate: Combate, pos_a, pos_b) -> None:
    combate.ativo(0).pos = Vector2(pos_a)
    combate.ativo(1).pos = Vector2(pos_b)


# ---- Naturezas -----------------------------------------------------------------
def test_cada_natureza_tem_uma_vantagem_e_uma_fraqueza():
    elementais = [n for n in Natureza if n is not Natureza.NEUTRO]
    for n in elementais:
        fortes = [d for d in Natureza if multiplicador(n, d) == SUPER_EFETIVO]
        fracos = [d for d in Natureza if multiplicador(n, d) == POUCO_EFETIVO]
        assert fortes == [FORTE_CONTRA[n]]
        assert len(fracos) == 1


def test_neutro_nao_tem_vantagem_nem_fraqueza():
    for n in Natureza:
        assert multiplicador(Natureza.NEUTRO, n) == 1.0
        assert multiplicador(n, Natureza.NEUTRO) == 1.0


def test_agua_e_super_efetiva_contra_fogo():
    combate = novo_combate(("Mizuha",), ("Kaen",))
    mizuha, kaen = combate.ativo(0), combate.ativo(1)
    jato = mizuha.base.jutsus[0]
    combate.rng = random.Random(5)
    super_dano, eficacia, _ = combate.calcular_dano(mizuha, kaen, jato)

    kaen.base = replace(kaen.base, natureza=Natureza.NEUTRO)  # mesmo ninja, mas sem natureza
    combate.rng = random.Random(5)  # mesma sorte
    normal, _, _ = combate.calcular_dano(mizuha, kaen, jato)

    assert eficacia == SUPER_EFETIVO
    assert super_dano == pytest.approx(normal * SUPER_EFETIVO, abs=1)


def test_todos_os_ninjas_tem_quatro_jutsus():
    for base in ROSTER:
        assert len(base.jutsus) == 4, base.nome


# ---- Jutsus --------------------------------------------------------------------
def test_projetil_acerta_o_inimigo():
    combate = novo_combate()
    posicionar(combate, (200, 400), (500, 400))
    alvo = combate.ativo(1)
    rodar(combate, 1.0, a=lambda: Comando(mira=Vector2(alvo.pos), jutsu=0))
    assert alvo.hp < alvo.hp_max


def test_pedra_bloqueia_projetil():
    combate = novo_combate()
    pedra = combate.arena.pedras[1]
    posicionar(combate, (pedra.x - 100, pedra.y), (pedra.x + 100, pedra.y))
    alvo = combate.ativo(1)
    rodar(combate, 1.5, a=lambda: Comando(mira=Vector2(alvo.pos), jutsu=0))
    assert alvo.hp == alvo.hp_max


def test_recarga_impede_usar_de_novo():
    combate = novo_combate()
    kaen = combate.ativo(0)
    combate.atualizar(DT, [Comando(jutsu=0), Comando()])
    assert kaen.recargas[0] > 0
    assert not combate.pode_usar(kaen, 0)
    rodar(combate, kaen.base.jutsus[0].recarga + 0.1)
    assert combate.pode_usar(kaen, 0)


def test_corpo_a_corpo_so_acerta_perto():
    combate = novo_combate(("Tetsu",), ("Ganro",))
    posicionar(combate, (300, 400), (500, 400))
    alvo = combate.ativo(1)
    combate.atualizar(DT, [Comando(mira=Vector2(alvo.pos), jutsu=1), Comando()])
    assert alvo.hp == alvo.hp_max  # longe demais

    posicionar(combate, (300, 400), (350, 400))
    rodar(combate, 1.1, a=lambda: Comando(mira=Vector2(alvo.pos), jutsu=1))
    assert alvo.hp < alvo.hp_max


def test_area_explode_depois_do_atraso():
    combate = novo_combate(("Ganro",), ("Tetsu",))
    posicionar(combate, (300, 400), (500, 400))
    alvo = combate.ativo(1)
    combate.atualizar(DT, [Comando(mira=Vector2(alvo.pos), jutsu=1), Comando()])
    assert len(combate.areas) == 1
    rodar(combate, 0.3)
    assert alvo.hp == alvo.hp_max  # ainda não explodiu
    rodar(combate, 0.6)
    assert alvo.hp < alvo.hp_max
    assert alvo.atordoado


def test_cura_nao_passa_do_maximo():
    combate = novo_combate(("Mizuha",), ("Tetsu",))
    mizuha = combate.ativo(0)
    assert not combate.pode_usar(mizuha, 3)  # HP cheio
    mizuha.hp = mizuha.hp_max - 5
    combate.atualizar(DT, [Comando(jutsu=3), Comando()])
    assert mizuha.hp == mizuha.hp_max


def test_queimadura_tira_hp_aos_poucos_mas_nao_queima_fogo():
    combate = novo_combate(("Kaen",), ("Tetsu",))
    tetsu = combate.ativo(1)
    tetsu.status[Efeito.QUEIMADURA] = 3
    rodar(combate, 1.0)
    esperado = tetsu.hp_max * QUEIMADURA_POR_SEGUNDO
    assert tetsu.hp_max - tetsu.hp == pytest.approx(esperado, rel=0.05)


# ---- Movimento -------------------------------------------------------------------
def test_agua_deixa_lento_quem_nao_e_de_agua():
    combate = novo_combate(("Ganro",), ("Mizuha",))
    lago = combate.arena.lagos[1]
    ganro, mizuha = combate.ativo(0), combate.ativo(1)
    fora = ganro.velocidade_movimento(combate.arena)
    ganro.pos = lago.centro
    assert ganro.velocidade_movimento(combate.arena) < fora

    fora = mizuha.velocidade_movimento(combate.arena)
    mizuha.pos = lago.centro
    assert mizuha.velocidade_movimento(combate.arena) > fora


def test_ninja_nao_atravessa_pedra():
    combate = novo_combate()
    pedra = combate.arena.pedras[0]
    eu = combate.ativo(0)
    eu.pos = Vector2(pedra.x - 120, pedra.y)
    rodar(combate, 2.0, a=lambda: Comando(mover=Vector2(1, 0)))
    assert eu.pos.distance_to(pedra.centro) >= pedra.r + eu.raio - 0.01


def test_esquiva_deixa_invulneravel_e_move_rapido():
    combate = novo_combate()
    eu = combate.ativo(0)
    antes = eu.pos.copy()
    combate.atualizar(DT, [Comando(mover=Vector2(0, -1), esquiva=True), Comando()])
    assert eu.invulneravel > 0
    rodar(combate, 0.2)
    assert antes.distance_to(eu.pos) > 120
    assert not combate.pode_esquivar(eu)  # em recarga


# ---- Trocas e nocaute ----------------------------------------------------------------
def test_trocar_de_ninja_leva_um_tempo():
    combate = novo_combate()
    time = combate.times[0]
    pos = time.ativo.pos.copy()
    combate.atualizar(DT, [Comando(trocar=2), Comando()])
    assert time.ativo_idx == 0 and time.trocando  # ainda chamando
    assert not combate.pode_usar(time.ativo, 0)  # nem dá para atacar enquanto troca
    rodar(combate, TROCA_DURACAO / 2, a=lambda: Comando(mover=Vector2(1, 0)))
    assert time.ativo.pos == pos  # fica parado

    rodar(combate, TROCA_DURACAO / 2 + 0.05)
    assert time.ativo_idx == 2
    assert time.ativo.pos == pos
    assert time.recarga_troca > 0
    combate.atualizar(DT, [Comando(trocar=0), Comando()])
    assert time.ativo_idx == 2 and not time.trocando  # ainda em recarga


def test_troca_e_cancelada_se_o_ninja_cair():
    combate = novo_combate()
    time = combate.times[0]
    combate.atualizar(DT, [Comando(trocar=2), Comando()])
    time.ativo.hp = 0
    combate.atualizar(DT, [Comando(), Comando()])
    assert not time.trocando
    assert time.espera_nocaute > 0


def test_nocaute_traz_o_proximo_ninja():
    combate = novo_combate()
    posicionar(combate, (200, 400), (500, 400))
    alvo = combate.ativo(1)
    alvo.hp = 1
    rodar(combate, 1.0, a=lambda: Comando(mira=Vector2(combate.ativo(1).pos), jutsu=0))
    time_b = combate.times[1]
    assert not alvo.vivo
    assert any(e.tipo == "nocaute" for e in combate.eventos)
    rodar(combate, ESPERA_APOS_NOCAUTE + 0.1)
    assert time_b.ativo is not alvo and time_b.ativo.vivo
    assert not combate.terminou


def test_escolher_quem_entra_depois_do_nocaute():
    combate = novo_combate()
    combate.ativo(1).hp = 0
    combate.atualizar(DT, [Comando(), Comando()])
    rodar(combate, ESPERA_APOS_NOCAUTE + 0.1, b=lambda: Comando(trocar=2))
    assert combate.times[1].ativo_idx == 2


def test_luta_acaba_quando_o_time_todo_cai():
    combate = novo_combate()
    for l in combate.times[1].lutadores:
        l.hp = 0
    combate.atualizar(DT, [Comando(), Comando()])
    assert combate.terminou
    assert combate.vencedor == 0
