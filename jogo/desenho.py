"""Funções de desenho usadas por todas as telas: textos, painéis, barras e os ninjas.

Os ninjas são desenhados com formas simples, vistos de cima. Para usar imagens
(sprites), troque o conteúdo de desenhar_ninja() por um pygame.image.load().
"""
from __future__ import annotations

import math

import pygame
from pygame.math import Vector2

from jogo import config as cfg
from jogo.naturezas import COR, Natureza

PELE = (232, 190, 150)
TECIDO_BANDANA = (40, 50, 90)
METAL = (210, 215, 225)

_fontes: dict[tuple[int, bool], pygame.font.Font] = {}
_sombras: dict[tuple[int, int], pygame.Surface] = {}


def limpar_cache() -> None:
    """Esquece fontes guardadas (elas param de funcionar se o pygame for reiniciado)."""
    _fontes.clear()


def fonte(tamanho: int, negrito: bool = False) -> pygame.font.Font:
    chave = (tamanho, negrito)
    if chave not in _fontes:
        _fontes[chave] = pygame.font.SysFont("segoeui,verdana,dejavusans,arial", tamanho, bold=negrito)
    return _fontes[chave]


def escrever(tela: pygame.Surface, texto: str, tamanho: int, cor, negrito: bool = False,
             sombra: bool = True, alfa: int = 255, **posicao) -> pygame.Rect:
    """Escreve um texto. Ex.: escrever(tela, "Oi", 20, cor, center=(100, 50))."""
    f = fonte(tamanho, negrito)
    superficie = f.render(texto, True, cor)
    retangulo = superficie.get_rect(**posicao)
    if sombra:
        s = f.render(texto, True, cfg.PRETO)
        if alfa < 255:
            s.set_alpha(alfa)
        tela.blit(s, retangulo.move(2, 2))
    if alfa < 255:
        superficie.set_alpha(alfa)
    tela.blit(superficie, retangulo)
    return retangulo


def misturar(cor_a, cor_b, t: float) -> tuple[int, int, int]:
    """Mistura duas cores: t=0 dá cor_a, t=1 dá cor_b."""
    return tuple(round(a + (b - a) * t) for a, b in zip(cor_a[:3], cor_b[:3]))


def escurecer(cor, t: float = 0.4) -> tuple[int, int, int]:
    return misturar(cor, (0, 0, 0), t)


def gradiente(largura: int, altura: int, topo, baixo) -> pygame.Surface:
    sup = pygame.Surface((largura, altura))
    for y in range(altura):
        pygame.draw.line(sup, misturar(topo, baixo, y / max(1, altura - 1)), (0, y), (largura, y))
    return sup


def painel(tela, rect, cor=cfg.PAINEL, borda=cfg.BORDA, raio: int = 12, largura_borda: int = 2) -> None:
    pygame.draw.rect(tela, cor, rect, border_radius=raio)
    if borda is not None and largura_borda > 0:
        pygame.draw.rect(tela, borda, rect, largura_borda, border_radius=raio)


def barra(tela, rect, fracao: float, cor, fundo=cfg.CINZA_ESCURO) -> None:
    rect = pygame.Rect(rect)
    fracao = max(0.0, min(1.0, fracao))
    pygame.draw.rect(tela, fundo, rect, border_radius=rect.h // 2)
    if fracao > 0:
        cheio = rect.copy()
        cheio.w = max(rect.h, round(rect.w * fracao))
        pygame.draw.rect(tela, cor, cheio, border_radius=rect.h // 2)


def cor_hp(fracao: float):
    return cfg.VERDE if fracao > 0.5 else cfg.AMARELO if fracao > 0.25 else cfg.VERMELHO


def selo_natureza(tela, natureza: Natureza, tamanho: int = 15, **posicao) -> pygame.Rect:
    texto = fonte(tamanho, True).render(natureza.value, True, (25, 25, 30))
    retangulo = pygame.Rect(0, 0, texto.get_width() + 16, texto.get_height() + 2)
    setattr(retangulo, *next(iter(posicao.items())))
    pygame.draw.rect(tela, COR[natureza], retangulo, border_radius=retangulo.h // 2)
    tela.blit(texto, texto.get_rect(center=retangulo.center))
    return retangulo


def sombra(tela, centro, largura: float, altura: float) -> None:
    chave = (round(largura), round(altura))
    if chave not in _sombras:
        sup = pygame.Surface(chave, pygame.SRCALPHA)
        pygame.draw.ellipse(sup, (0, 0, 0, 70), sup.get_rect())
        _sombras[chave] = sup
    sup = _sombras[chave]
    tela.blit(sup, sup.get_rect(center=(round(centro[0]), round(centro[1]))))


def desenhar_ninja(tela, base, centro, direcao, tempo: float, escala: float = 1.0,
                   nocauteado: bool = False, piscar: bool = False, andando: float = 0.0) -> None:
    """Desenha um ninja visto de cima, olhando para `direcao`."""
    f = Vector2(direcao)
    f = f.normalize() if f.length_squared() > 0 else Vector2(1, 0)
    lado = Vector2(-f.y, f.x)
    c = Vector2(centro)
    e = escala

    cor, cabelo, pele, tecido = base.cor, base.cabelo, PELE, TECIDO_BANDANA
    if nocauteado:
        cinza = (90, 90, 95)
        cor, cabelo, pele, tecido = (misturar(x, cinza, 0.7) for x in (cor, cabelo, pele, tecido))
    if piscar:
        cor, cabelo, pele, tecido = (misturar(x, cfg.BRANCO, 0.75) for x in (cor, cabelo, pele, tecido))

    sombra(tela, (c.x, c.y + 8 * e), 54 * e, 28 * e)

    # pontas da bandana balançando atrás da cabeça
    onda = math.sin(tempo * 10) * 3 * e
    nuca = c - f * 9 * e
    for s in (-1, 1):
        ponta = nuca - f * 20 * e + lado * (s * 7 * e + onda)
        pygame.draw.line(tela, tecido, nuca + lado * s * 3 * e, ponta, max(2, round(4 * e)))

    # mãos (balançam quando anda)
    balanco = math.sin(tempo * 14) * 5 * e * andando
    for s in (-1, 1):
        mao = c + f * (12 * e + s * balanco) + lado * s * 19 * e
        pygame.draw.circle(tela, pele, mao, 6 * e)
        pygame.draw.circle(tela, escurecer(pele, 0.3), mao, 6 * e, max(1, round(e)))

    # corpo (ombros)
    pygame.draw.circle(tela, cor, c, 21 * e)
    pygame.draw.circle(tela, escurecer(cor), c, 21 * e, max(1, round(2 * e)))

    # cabeça com cabelo espetado
    cabeca = c + f * 3 * e
    for angulo in (-45, 0, 45):
        atras = (-f).rotate(angulo)
        pygame.draw.polygon(tela, cabelo, [
            cabeca + atras * 19 * e,
            cabeca + atras.rotate(28) * 10 * e,
            cabeca + atras.rotate(-28) * 10 * e,
        ])
    pygame.draw.circle(tela, cabelo, cabeca, 13 * e)

    # bandana na testa com a placa de metal
    testa = cabeca + f * 6 * e
    pygame.draw.line(tela, tecido, testa + lado * 11 * e, testa - lado * 11 * e, max(2, round(5 * e)))
    pygame.draw.circle(tela, METAL, testa + f * e, 3.5 * e)

    if nocauteado:  # "X" de nocaute
        for s in (-1, 1):
            pygame.draw.line(tela, cfg.PRETO, cabeca + Vector2(-6, -6 * s) * e, cabeca + Vector2(6, 6 * s) * e,
                             max(2, round(3 * e)))
