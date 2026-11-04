"""Janela do jogo e troca entre as telas (título → escolha de time → batalha)."""
from __future__ import annotations

import random

import pygame

from jogo import config as cfg
from jogo.ia import DIFICULDADES
from jogo.ninjas import ROSTER
from jogo.tela_batalha import TelaBatalha
from jogo.tela_selecao import TelaSelecao
from jogo.tela_titulo import TelaTitulo


class Jogo:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(cfg.TITULO)
        self.tela = pygame.display.set_mode((cfg.LARGURA, cfg.ALTURA))
        self.relogio = pygame.time.Clock()
        self.rodando = True
        self.escolhidos: list[int] = []
        self.dificuldade = 1
        self.batalha_atual: TelaBatalha | None = None
        self.mudar_para(TelaTitulo())

    def mudar_para(self, tela) -> None:
        self.atual = tela
        pygame.mouse.set_visible(not isinstance(tela, TelaBatalha))  # na luta, a mira substitui o cursor

    def executar(self) -> None:
        while self.rodando:
            dt = min(self.relogio.tick(cfg.FPS) / 1000, 0.05)
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    self.rodando = False
                else:
                    self.tratar(self.atual.evento(evento))
            self.atual.atualizar(dt)
            self.atual.desenhar(self.tela)
            pygame.display.flip()
        pygame.quit()

    def tratar(self, acao: str | None) -> None:
        if acao is None:
            return
        if acao == "sair":
            self.rodando = False
        elif acao == "titulo":
            self.mudar_para(TelaTitulo())
        elif acao in ("selecao", "menu"):
            self.mudar_para(TelaSelecao(self.escolhidos, self.dificuldade))
        elif acao == "lutar":
            selecao = self.atual
            self.escolhidos = list(selecao.escolhidos)
            self.dificuldade = selecao.dificuldade
            self.iniciar_batalha(selecao.time(), random.sample(ROSTER, cfg.TAMANHO_TIME))
        elif acao == "revanche" and self.batalha_atual is not None:
            self.iniciar_batalha(self.batalha_atual.time_jogador, self.batalha_atual.time_inimigo)

    def iniciar_batalha(self, time_jogador, time_inimigo) -> None:
        self.batalha_atual = TelaBatalha(time_jogador, time_inimigo, DIFICULDADES[self.dificuldade])
        self.mudar_para(self.batalha_atual)
