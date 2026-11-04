"""Personagens que participam da batalha.

Para mudar a dificuldade, mexa nos números de criar_heroi() e criar_inimigo().
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(eq=False)  # eq=False: cada personagem é único (pode ser chave de dicionário)
class Personagem:
    nome: str
    hp_max: int
    mp_max: int
    ataque: int
    defesa: int
    cor: tuple[int, int, int] = (200, 200, 200)
    hp: int = field(init=False)
    mp: int = field(init=False)
    defendendo: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.hp = self.hp_max
        self.mp = self.mp_max

    @property
    def vivo(self) -> bool:
        return self.hp > 0

    def receber_dano(self, quantidade: int) -> int:
        """Tira HP (nunca abaixo de 0) e devolve quanto foi tirado de verdade."""
        antes = self.hp
        self.hp = max(0, self.hp - quantidade)
        return antes - self.hp

    def curar(self, quantidade: int) -> int:
        """Recupera HP (nunca acima do máximo) e devolve quanto foi curado."""
        antes = self.hp
        self.hp = min(self.hp_max, self.hp + quantidade)
        return self.hp - antes

    def gastar_mp(self, quantidade: int) -> None:
        self.mp = max(0, self.mp - quantidade)

    def recuperar_mp(self, quantidade: int) -> int:
        antes = self.mp
        self.mp = min(self.mp_max, self.mp + quantidade)
        return self.mp - antes


def criar_heroi() -> Personagem:
    return Personagem("Herói", hp_max=100, mp_max=30, ataque=18, defesa=8, cor=(80, 140, 230))


def criar_inimigo() -> Personagem:
    return Personagem("Goblin", hp_max=120, mp_max=18, ataque=18, defesa=6, cor=(110, 180, 80))
