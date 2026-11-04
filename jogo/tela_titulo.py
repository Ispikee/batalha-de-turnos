"""Tela inicial com o menu."""
from __future__ import annotations

import math

import pygame
from pygame.math import Vector2

from jogo import config as cfg
from jogo.desenho import desenhar_ninja, escrever, gradiente, painel
from jogo.naturezas import COR
from jogo.ninjas import ROSTER

OPCOES = (
    ("Contra o computador", "selecao"),
    ("Criar partida online", "criar_online"),
    ("Entrar em partida online", "entrar_online"),
    ("Sair", "sair"),
)

CONTROLES = (
    ("WASD / setas", "andar"),
    ("Mouse", "mirar"),
    ("Clique  /  Clique dir.  /  Q  /  E", "jutsus"),
    ("Espaço ou Shift", "esquivar"),
    ("1  2  3", "trocar de ninja"),
    ("P", "pausar"),
)


class TelaTitulo:
    def __init__(self, aviso: str | None = None) -> None:
        self.tempo = 0.0
        self.aviso = aviso  # ex.: "A conexão com seu amigo caiu."
        self.opcao = 0
        self.fundo = gradiente(cfg.LARGURA, cfg.ALTURA, (18, 20, 34), (52, 30, 62))
        self.botoes = []
        for i in range(len(OPCOES)):
            botao = pygame.Rect(0, 0, 380, 46)
            botao.center = (cfg.LARGURA // 2, 318 + i * 54)
            self.botoes.append(botao)

    def evento(self, e) -> str | None:
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                return "sair"
            if e.key in (pygame.K_UP, pygame.K_w):
                self.opcao = (self.opcao - 1) % len(OPCOES)
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.opcao = (self.opcao + 1) % len(OPCOES)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return OPCOES[self.opcao][1]
        elif e.type == pygame.MOUSEMOTION:
            for i, botao in enumerate(self.botoes):
                if botao.collidepoint(e.pos):
                    self.opcao = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, botao in enumerate(self.botoes):
                if botao.collidepoint(e.pos):
                    return OPCOES[i][1]
        return None

    def atualizar(self, dt: float) -> None:
        self.tempo += dt

    def desenhar(self, tela: pygame.Surface) -> None:
        tela.blit(self.fundo, (0, 0))
        meio = Vector2(cfg.LARGURA / 2, 150)

        # os seis ninjas correndo em roda em volta do título
        for i, base in enumerate(ROSTER):
            angulo = self.tempo * 0.6 + i * math.tau / len(ROSTER)
            pos = meio + Vector2(math.cos(angulo) * 360, math.sin(angulo) * 95)
            direcao = Vector2(-math.sin(angulo) * 360, math.cos(angulo) * 95)
            pygame.draw.circle(tela, COR[base.natureza], pos + Vector2(0, 4), 30, 2)
            desenhar_ninja(tela, base, pos, direcao, self.tempo + i, escala=1.3, andando=1.0)

        escrever(tela, "ARENA SHINOBI", 88, cfg.DOURADO, negrito=True, center=(meio.x, 135))
        escrever(tela, "Batalhas ninja em tempo real", 24, cfg.BRANCO, center=(meio.x, 200))

        for i, ((texto, _), botao) in enumerate(zip(OPCOES, self.botoes)):
            focado = i == self.opcao
            painel(tela, botao, cor=cfg.PAINEL_CLARO if focado else cfg.PAINEL,
                   borda=cfg.DOURADO if focado else cfg.BORDA, largura_borda=3 if focado else 2)
            escrever(tela, texto, 22, cfg.BRANCO if focado else cfg.CINZA_CLARO, negrito=focado, center=botao.center)

        if self.aviso:
            escrever(tela, self.aviso, 20, cfg.AMARELO, negrito=True, center=(meio.x, 258))

        caixa = pygame.Rect(0, 0, 760, 108)
        caixa.midbottom = (meio.x, cfg.ALTURA - 14)
        painel(tela, caixa, cor=cfg.PAINEL)
        for i, (tecla, acao) in enumerate(CONTROLES):
            coluna, linha = divmod(i, 3)
            x = caixa.x + 30 + coluna * 380
            y = caixa.y + 14 + linha * 28
            r = escrever(tela, tecla, 17, cfg.AMARELO, negrito=True, topleft=(x, y))
            escrever(tela, f"  {acao}", 17, cfg.CINZA_CLARO, topleft=(r.right, y))
