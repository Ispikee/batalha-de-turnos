"""Naturezas de chakra e a tabela de vantagens.

Cada natureza é forte contra uma e fraca contra outra, formando um ciclo:

    Água > Fogo > Vento > Terra > Raio > Água

(a água apaga o fogo, o fogo consome o ar, o vento desgasta a terra,
a terra aterra o raio e o raio eletrifica a água).
Neutro (taijutsu e armas) não tem vantagem nem fraqueza.
"""
from __future__ import annotations

from enum import Enum


class Natureza(Enum):
    FOGO = "Fogo"
    AGUA = "Água"
    VENTO = "Vento"
    TERRA = "Terra"
    RAIO = "Raio"
    NEUTRO = "Neutro"


FORTE_CONTRA = {
    Natureza.AGUA: Natureza.FOGO,
    Natureza.FOGO: Natureza.VENTO,
    Natureza.VENTO: Natureza.TERRA,
    Natureza.TERRA: Natureza.RAIO,
    Natureza.RAIO: Natureza.AGUA,
}

SUPER_EFETIVO = 1.6
POUCO_EFETIVO = 0.6

COR = {
    Natureza.FOGO: (240, 105, 50),
    Natureza.AGUA: (65, 145, 240),
    Natureza.VENTO: (120, 220, 175),
    Natureza.TERRA: (180, 130, 80),
    Natureza.RAIO: (250, 220, 70),
    Natureza.NEUTRO: (195, 195, 205),
}


def multiplicador(ataque: Natureza, defesa: Natureza) -> float:
    """Quanto um golpe da natureza `ataque` rende contra um ninja da natureza `defesa`."""
    if FORTE_CONTRA.get(ataque) is defesa:
        return SUPER_EFETIVO
    if FORTE_CONTRA.get(defesa) is ataque:
        return POUCO_EFETIVO
    return 1.0


def forte_contra(natureza: Natureza) -> Natureza | None:
    return FORTE_CONTRA.get(natureza)


def fraco_contra(natureza: Natureza) -> Natureza | None:
    """A natureza que vence esta (nos dois sentidos: bate forte nela e apanha pouco dela)."""
    return next((a for a, d in FORTE_CONTRA.items() if d is natureza), None)
