"""Tela inicial."""
from __future__ import annotations

import math

import pygame
from pygame.math import Vector2

from jogo import config as cfg
from jogo.desenho import desenhar_ninja, escrever, gradiente, painel
from jogo.naturezas import COR
from jogo.ninjas import ROSTER

CONTROLES = (
    ("WASD / setas", "andar"),
    ("Mouse", "mirar"),
    ("Clique  /  Clique dir.  /  Q  /  E", "jutsus"),
    ("Espaço ou Shift", "esquivar"),
    ("1  2  3", "trocar de ninja"),
    ("P", "pausar"),
)


class TelaTitulo:
    def __init__(self) -> None:
        self.tempo = 0.0
        self.fundo = gradiente(cfg.LARGURA, cfg.ALTURA, (18, 20, 34), (52, 30, 62))

    def evento(self, e) -> str | None:
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                return "sair"
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return "selecao"
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            return "selecao"
        return None

    def atualizar(self, dt: float) -> None:
        self.tempo += dt

    def desenhar(self, tela: pygame.Surface) -> None:
        tela.blit(self.fundo, (0, 0))
        meio = Vector2(cfg.LARGURA / 2, 300)

        # os seis ninjas correndo em roda
        for i, base in enumerate(ROSTER):
            angulo = self.tempo * 0.6 + i * math.tau / len(ROSTER)
            pos = meio + Vector2(math.cos(angulo) * 330, math.sin(angulo) * 120)
            direcao = Vector2(-math.sin(angulo) * 330, math.cos(angulo) * 120)
            pygame.draw.circle(tela, COR[base.natureza], pos + Vector2(0, 4), 30, 2)
            desenhar_ninja(tela, base, pos, direcao, self.tempo + i, escala=1.3, andando=1.0)

        escrever(tela, "ARENA SHINOBI", 92, cfg.DOURADO, negrito=True, center=(meio.x, 250))
        escrever(tela, "Batalhas ninja em tempo real", 26, cfg.BRANCO, center=(meio.x, 320))

        if int(self.tempo * 2) % 2 == 0:
            escrever(tela, "Aperte Enter para começar", 28, cfg.BRANCO, negrito=True, center=(meio.x, 480))

        caixa = pygame.Rect(0, 0, 760, 120)
        caixa.midtop = (meio.x, 540)
        painel(tela, caixa, cor=cfg.PAINEL)
        for i, (tecla, acao) in enumerate(CONTROLES):
            coluna, linha = divmod(i, 3)
            x = caixa.x + 30 + coluna * 380
            y = caixa.y + 18 + linha * 30
            r = escrever(tela, tecla, 18, cfg.AMARELO, negrito=True, topleft=(x, y))
            escrever(tela, f"  {acao}", 18, cfg.CINZA_CLARO, topleft=(r.right, y))
