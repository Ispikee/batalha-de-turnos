"""Os ninjas que podem entrar no time.

Para criar um ninja novo, copie um dos blocos abaixo e mude os números.
Atributos: HP, Ataque (golpes físicos), Ninjutsu (jutsus elementais),
Defesa e Velocidade (o quanto anda rápido).
"""
from __future__ import annotations

from dataclasses import dataclass

from jogo.jutsus import Efeito, Jutsu, Tipo
from jogo.naturezas import Natureza

N = Natureza
T = Tipo
E = Efeito


@dataclass(frozen=True)
class NinjaBase:
    nome: str
    natureza: Natureza
    hp: int
    ataque: int
    ninjutsu: int
    defesa: int
    velocidade: int
    cor: tuple[int, int, int]  # roupa
    cabelo: tuple[int, int, int]
    jutsus: tuple[Jutsu, ...]
    descricao: str = ""


ROSTER: tuple[NinjaBase, ...] = (
    NinjaBase(
        "Kaen", N.FOGO, hp=200, ataque=70, ninjutsu=95, defesa=65, velocidade=75,
        cor=(200, 70, 45), cabelo=(70, 30, 25),
        descricao="Ataca de longe e queima os inimigos.",
        jutsus=(
            Jutsu("Bola de Fogo", N.FOGO, T.PROJETIL, poder=22, recarga=1.1, alcance=520, velocidade=540,
                  raio=14, efeito=E.QUEIMADURA, chance=0.3, duracao=3),
            Jutsu("Chuva de Brasas", N.FOGO, T.LEQUE, poder=11, recarga=2.6, alcance=380, velocidade=620,
                  raio=9, quantidade=3, efeito=E.QUEIMADURA, chance=0.15, duracao=3),
            Jutsu("Coluna de Chamas", N.FOGO, T.AREA, poder=34, recarga=6, alcance=380, raio=75, atraso=0.8,
                  efeito=E.QUEIMADURA, chance=0.6, duracao=3),
            Jutsu("Chute Giratório", N.NEUTRO, T.CORPO, poder=18, recarga=1.0, alcance=70, efeito=E.EMPURRAO),
        ),
    ),
    NinjaBase(
        "Mizuha", N.AGUA, hp=220, ataque=60, ninjutsu=85, defesa=80, velocidade=70,
        cor=(45, 115, 195), cabelo=(25, 40, 85),
        descricao="Resistente, se cura e fica mais rápida na água.",
        jutsus=(
            Jutsu("Jato d'Água", N.AGUA, T.PROJETIL, poder=18, recarga=0.9, alcance=560, velocidade=720, raio=10),
            Jutsu("Chicote d'Água", N.AGUA, T.CORPO, poder=22, recarga=1.6, alcance=125,
                  efeito=E.LENTIDAO, duracao=1.5),
            Jutsu("Onda Gigante", N.AGUA, T.AREA, poder=30, recarga=7, alcance=300, raio=110, atraso=0.9,
                  efeito=E.EMPURRAO),
            Jutsu("Bolha Curativa", N.AGUA, T.SUPORTE, poder=25, recarga=12, efeito=E.CURA),
        ),
    ),
    NinjaBase(
        "Fuuga", N.VENTO, hp=170, ataque=85, ninjutsu=75, defesa=55, velocidade=105,
        cor=(60, 160, 120), cabelo=(225, 225, 215),
        descricao="O mais veloz. Golpes rápidos e investidas.",
        jutsus=(
            Jutsu("Lâmina de Vento", N.VENTO, T.PROJETIL, poder=16, recarga=0.7, alcance=480, velocidade=860, raio=9),
            Jutsu("Leque Cortante", N.VENTO, T.LEQUE, poder=12, recarga=2.2, alcance=340, velocidade=760,
                  raio=8, quantidade=3),
            Jutsu("Corte Veloz", N.NEUTRO, T.INVESTIDA, poder=24, recarga=2.5, alcance=230),
            Jutsu("Passo do Vento", N.VENTO, T.SUPORTE, recarga=10, efeito=E.VELOCIDADE, duracao=4),
        ),
    ),
    NinjaBase(
        "Ganro", N.TERRA, hp=250, ataque=90, ninjutsu=65, defesa=100, velocidade=55,
        cor=(135, 95, 55), cabelo=(50, 40, 30),
        descricao="Lento, mas aguenta muito e bate pesado de perto.",
        jutsus=(
            Jutsu("Rocha Arremessada", N.TERRA, T.PROJETIL, poder=28, recarga=1.8, alcance=450, velocidade=420,
                  raio=18, efeito=E.EMPURRAO),
            Jutsu("Espinhos da Terra", N.TERRA, T.AREA, poder=26, recarga=5, alcance=360, raio=70, atraso=0.7,
                  efeito=E.ATORDOAR, duracao=0.8),
            Jutsu("Punho de Rocha", N.TERRA, T.CORPO, poder=30, recarga=1.4, alcance=75, efeito=E.EMPURRAO),
            Jutsu("Pele de Pedra", N.TERRA, T.SUPORTE, recarga=12, efeito=E.ESCUDO, duracao=4),
        ),
    ),
    NinjaBase(
        "Shiden", N.RAIO, hp=175, ataque=80, ninjutsu=100, defesa=60, velocidade=90,
        cor=(205, 175, 40), cabelo=(35, 35, 45),
        descricao="Muito dano e golpes que atordoam.",
        jutsus=(
            Jutsu("Agulha Elétrica", N.RAIO, T.PROJETIL, poder=15, recarga=0.8, alcance=500, velocidade=920,
                  raio=8, efeito=E.ATORDOAR, chance=0.15, duracao=0.4),
            Jutsu("Relâmpago", N.RAIO, T.AREA, poder=36, recarga=6, alcance=420, raio=60, atraso=0.9,
                  efeito=E.ATORDOAR, chance=0.5, duracao=0.7),
            Jutsu("Investida Relâmpago", N.RAIO, T.INVESTIDA, poder=26, recarga=3, alcance=260,
                  efeito=E.ATORDOAR, chance=0.25, duracao=0.4),
            Jutsu("Sobrecarga", N.RAIO, T.SUPORTE, recarga=12, efeito=E.FORCA, duracao=5),
        ),
    ),
    NinjaBase(
        "Tetsu", N.NEUTRO, hp=230, ataque=105, ninjutsu=50, defesa=85, velocidade=85,
        cor=(140, 140, 155), cabelo=(125, 40, 40),
        descricao="Mestre do taijutsu: sem fraquezas, mas sem vantagens.",
        jutsus=(
            Jutsu("Kunai", N.NEUTRO, T.PROJETIL, poder=10, recarga=0.7, alcance=500, velocidade=900, raio=7),
            Jutsu("Sequência de Socos", N.NEUTRO, T.CORPO, poder=26, recarga=1.0, alcance=75),
            Jutsu("Chute Voador", N.NEUTRO, T.INVESTIDA, poder=30, recarga=2.5, alcance=240, efeito=E.EMPURRAO),
            Jutsu("Foco Interior", N.NEUTRO, T.SUPORTE, recarga=12, efeito=E.FORCA, duracao=5),
        ),
    ),
)


def ninja(nome: str) -> NinjaBase:
    for base in ROSTER:
        if base.nome == nome:
            return base
    raise KeyError(nome)
