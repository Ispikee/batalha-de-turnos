"""O campo de batalha: limites, pedras (bloqueiam passagem e projéteis) e lagos.

Nos lagos, ninjas de Água ficam mais rápidos e os outros ficam lentos.
"""
from __future__ import annotations

from dataclasses import dataclass

import pygame
from pygame.math import Vector2

from jogo import config as cfg


@dataclass(frozen=True)
class Circulo:
    x: float
    y: float
    r: float

    @property
    def centro(self) -> Vector2:
        return Vector2(self.x, self.y)

    def contem(self, ponto: Vector2, margem: float = 0.0) -> bool:
        return (ponto.x - self.x) ** 2 + (ponto.y - self.y) ** 2 <= (self.r + margem) ** 2


def distancia_ponto_segmento(p: Vector2, a: Vector2, b: Vector2) -> float:
    ab = b - a
    tamanho = ab.length_squared()
    if tamanho == 0:
        return p.distance_to(a)
    t = max(0.0, min(1.0, (p - a).dot(ab) / tamanho))
    return p.distance_to(a + ab * t)


class Arena:
    def __init__(self, retangulo, pedras: list[Circulo], lagos: list[Circulo]):
        self.retangulo = pygame.Rect(retangulo)
        self.pedras = pedras
        self.lagos = lagos

    def dentro(self, p: Vector2) -> bool:
        return self.retangulo.collidepoint(p.x, p.y)

    def na_agua(self, p: Vector2) -> bool:
        return any(lago.contem(p) for lago in self.lagos)

    def colide_pedra(self, p: Vector2, raio: float) -> bool:
        return any(pedra.contem(p, raio) for pedra in self.pedras)

    def linha_livre(self, a: Vector2, b: Vector2, margem: float = 0.0) -> bool:
        """True se nenhuma pedra está entre os pontos a e b."""
        return all(distancia_ponto_segmento(pedra.centro, a, b) >= pedra.r + margem for pedra in self.pedras)

    def limitar(self, p: Vector2, margem: float = 0.0) -> Vector2:
        r = self.retangulo
        return Vector2(min(max(p.x, r.left + margem), r.right - margem), min(max(p.y, r.top + margem), r.bottom - margem))

    def resolver_colisao(self, p: Vector2, raio: float) -> Vector2:
        """Empurra um círculo para fora das pedras e para dentro da arena."""
        p = Vector2(p)
        for pedra in self.pedras:
            d = p - pedra.centro
            distancia = d.length()
            minimo = pedra.r + raio
            if distancia < minimo:
                if distancia < 1e-6:
                    d, distancia = Vector2(1, 0), 1.0
                p = pedra.centro + d / distancia * minimo
        return self.limitar(p, raio)

    def inicio(self, lado: int) -> Vector2:
        r = self.retangulo
        return Vector2(r.left + 160, r.centery) if lado == 0 else Vector2(r.right - 160, r.centery)


def criar_arena() -> Arena:
    x, y, largura, altura = cfg.ARENA
    cx, cy = x + largura / 2, y + altura / 2
    pedras = [
        Circulo(cx, cy, 40),
        Circulo(cx - 210, cy - 115, 26),
        Circulo(cx + 210, cy + 115, 26),
        Circulo(cx - 210, cy + 120, 22),
        Circulo(cx + 210, cy - 120, 22),
    ]
    topo = [Circulo(cx - 70, y + 62, 55), Circulo(cx, y + 50, 72), Circulo(cx + 68, y + 64, 50)]
    baixo = [Circulo(2 * cx - c.x, 2 * cy - c.y, c.r) for c in topo]  # espelhado: a arena é justa
    return Arena((x, y, largura, altura), pedras, topo + baixo)
