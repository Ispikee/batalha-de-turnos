"""Regras da batalha por turnos.

Este arquivo não usa Pygame: só lógica. Por isso dá para testar tudo
com `pytest` sem abrir janela nenhuma (veja a pasta tests/).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from jogo.personagem import Personagem


class Acao(Enum):
    ATACAR = "Atacar"
    MAGIA = "Magia"
    DEFENDER = "Defender"
    CURAR = "Curar"


# ---- Regras (ajuste à vontade) -------------------------------------------
CUSTO_MP = {Acao.MAGIA: 8, Acao.CURAR: 6}
MULTIPLICADOR_MAGIA = 1.6  # magia bate mais forte e ignora a defesa
CURA_PERCENTUAL = 0.30  # Curar recupera 30% do HP máximo
MP_AO_DEFENDER = 5  # Defender também recupera um pouco de MP
CHANCE_CRITICO = 0.10
MULTIPLICADOR_CRITICO = 1.5
# --------------------------------------------------------------------------


@dataclass
class Resultado:
    """O que aconteceu em uma ação. A interface usa isso para animar."""

    ator: Personagem
    acao: Acao
    mensagens: list[str] = field(default_factory=list)
    alvo: Personagem | None = None
    dano: int = 0
    cura: int = 0
    critico: bool = False


def calcular_dano(
    atacante: Personagem,
    alvo: Personagem,
    rng: random.Random,
    multiplicador: float = 1.0,
    ignora_defesa: bool = False,
) -> tuple[int, bool]:
    """Devolve (dano, foi_critico)."""
    defesa = 0 if ignora_defesa else alvo.defesa / 2
    base = max(1.0, atacante.ataque * multiplicador - defesa)
    dano = base * rng.uniform(0.85, 1.15)  # um pouco de sorte em cada golpe
    critico = rng.random() < CHANCE_CRITICO
    if critico:
        dano *= MULTIPLICADOR_CRITICO
    if alvo.defendendo:
        dano /= 2
    return max(1, round(dano)), critico


class Batalha:
    def __init__(self, heroi: Personagem, inimigo: Personagem, rng: random.Random | None = None):
        self.heroi = heroi
        self.inimigo = inimigo
        self.rng = rng or random.Random()
        self.turno = 1
        self.log: list[str] = [f"Um {inimigo.nome} aparece para lutar!"]

    # ---- Estado ----------------------------------------------------------
    @property
    def terminou(self) -> bool:
        return not self.heroi.vivo or not self.inimigo.vivo

    @property
    def vencedor(self) -> Personagem | None:
        if not self.terminou:
            return None
        return self.heroi if self.heroi.vivo else self.inimigo

    def oponente_de(self, personagem: Personagem) -> Personagem:
        return self.inimigo if personagem is self.heroi else self.heroi

    def pode_usar(self, personagem: Personagem, acao: Acao) -> bool:
        if personagem.mp < CUSTO_MP.get(acao, 0):
            return False
        if acao is Acao.CURAR and personagem.hp >= personagem.hp_max:
            return False
        return True

    # ---- Ações -----------------------------------------------------------
    def executar(self, ator: Personagem, acao: Acao) -> Resultado:
        if self.terminou:
            raise RuntimeError("A batalha já terminou.")
        if not self.pode_usar(ator, acao):
            raise ValueError(f"{ator.nome} não pode usar {acao.value} agora.")

        alvo = self.oponente_de(ator)
        ator.defendendo = False  # a defesa só vale até a próxima ação de quem defendeu
        ator.gastar_mp(CUSTO_MP.get(acao, 0))
        resultado = Resultado(ator, acao)

        if acao is Acao.ATACAR:
            self._golpear(resultado, alvo, "ataca e causa")
        elif acao is Acao.MAGIA:
            self._golpear(resultado, alvo, "lança uma magia e causa", MULTIPLICADOR_MAGIA, ignora_defesa=True)
        elif acao is Acao.DEFENDER:
            ator.defendendo = True
            mp = ator.recuperar_mp(MP_AO_DEFENDER)
            extra = f" e recupera {mp} MP" if mp else ""
            resultado.mensagens.append(f"{ator.nome} se defende{extra}.")
        elif acao is Acao.CURAR:
            resultado.cura = ator.curar(round(ator.hp_max * CURA_PERCENTUAL))
            resultado.mensagens.append(f"{ator.nome} se cura em {resultado.cura} HP.")

        if not alvo.vivo:
            resultado.mensagens.append(f"{alvo.nome} foi derrotado!")
        if ator is self.inimigo:
            self.turno += 1  # o turno fecha depois que o inimigo age

        self.log.extend(resultado.mensagens)
        return resultado

    def _golpear(
        self,
        resultado: Resultado,
        alvo: Personagem,
        verbo: str,
        multiplicador: float = 1.0,
        ignora_defesa: bool = False,
    ) -> None:
        ator = resultado.ator
        dano, critico = calcular_dano(ator, alvo, self.rng, multiplicador, ignora_defesa)
        resultado.alvo = alvo
        resultado.dano = alvo.receber_dano(dano)
        resultado.critico = critico
        prefixo = "Crítico! " if critico else ""
        resultado.mensagens.append(f"{prefixo}{ator.nome} {verbo} {resultado.dano} de dano.")

    # ---- Inteligência do inimigo -------------------------------------------
    def escolher_acao_inimigo(self) -> Acao:
        ini = self.inimigo
        if ini.hp < ini.hp_max * 0.35 and self.pode_usar(ini, Acao.CURAR) and self.rng.random() < 0.7:
            return Acao.CURAR
        if self.pode_usar(ini, Acao.MAGIA) and self.rng.random() < 0.25:
            return Acao.MAGIA
        if self.rng.random() < 0.10:
            return Acao.DEFENDER
        return Acao.ATACAR
