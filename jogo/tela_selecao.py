"""Tela de escolha do time (3 ninjas) e da dificuldade."""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from jogo import config as cfg
from jogo.desenho import barra, desenhar_ninja, escrever, escurecer, gradiente, misturar, painel, selo_natureza
from jogo.ia import DIFICULDADES
from jogo.naturezas import COR, forte_contra, fraco_contra
from jogo.ninjas import ROSTER

ATRIBUTOS = (("HP", "hp", 260), ("Ataque", "ataque", 110), ("Ninjutsu", "ninjutsu", 110),
             ("Defesa", "defesa", 110), ("Velocidade", "velocidade", 110))
COLUNAS = 3


class TelaSelecao:
    """Com `sessao` (partida online), o botão vira "PRONTO!" e mostra se o amigo já escolheu."""

    def __init__(self, escolhidos: list[int] | None = None, dificuldade: int = 1, sessao=None):
        self.escolhidos: list[int] = list(escolhidos or [])
        self.dificuldade = dificuldade
        self.sessao = sessao
        self.online = sessao is not None
        self.cursor = self.escolhidos[0] if self.escolhidos else 0
        self.tempo = 0.0
        self.fundo = gradiente(cfg.LARGURA, cfg.ALTURA, (18, 20, 34), (40, 28, 55))
        self.cartoes = [
            pygame.Rect(40 + (i % COLUNAS) * 405, 80 + (i // COLUNAS) * 242, 390, 232) for i in range(len(ROSTER))
        ]
        self.area_time = pygame.Rect(40, 572, 470, 134)
        self.area_dificuldade = pygame.Rect(525, 572, 330, 134)
        self.botao_menos = pygame.Rect(self.area_dificuldade.x + 20, self.area_dificuldade.y + 58, 44, 44)
        self.botao_mais = pygame.Rect(self.area_dificuldade.right - 64, self.area_dificuldade.y + 58, 44, 44)
        self.botao_lutar = pygame.Rect(870, 572, 370, 134)
        self.botao_aleatorio = pygame.Rect(1060, 20, 180, 40)

    @property
    def pronto(self) -> bool:
        return len(self.escolhidos) == cfg.TAMANHO_TIME

    def time(self):
        return [ROSTER[i] for i in self.escolhidos]

    def alternar(self, i: int) -> None:
        if i in self.escolhidos:
            self.escolhidos.remove(i)
        elif len(self.escolhidos) < cfg.TAMANHO_TIME:
            self.escolhidos.append(i)

    def aleatorio(self) -> None:
        self.escolhidos = random.sample(range(len(ROSTER)), cfg.TAMANHO_TIME)

    def mudar_dificuldade(self, passo: int) -> None:
        self.dificuldade = (self.dificuldade + passo) % len(DIFICULDADES)

    @property
    def aguardando(self) -> bool:
        """Online: já apertou PRONTO e está esperando o amigo."""
        return self.online and self.sessao.pronto

    # ---- Entrada --------------------------------------------------------------
    def evento(self, e) -> str | None:
        if self.aguardando:  # time travado: só dá para cancelar ou sair
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return "sair_online"
            cancelar = (e.type == pygame.KEYDOWN and e.key in (pygame.K_BACKSPACE, pygame.K_RETURN, pygame.K_KP_ENTER)) or (
                e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.botao_lutar.collidepoint(e.pos))
            return "cancelar_pronto" if cancelar else None
        if e.type == pygame.MOUSEMOTION:
            for i, cartao in enumerate(self.cartoes):
                if cartao.collidepoint(e.pos):
                    self.cursor = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, cartao in enumerate(self.cartoes):
                if cartao.collidepoint(e.pos):
                    self.alternar(i)
            if self.botao_menos.collidepoint(e.pos) and not self.online:
                self.mudar_dificuldade(-1)
            elif self.botao_mais.collidepoint(e.pos) and not self.online:
                self.mudar_dificuldade(1)
            elif self.botao_aleatorio.collidepoint(e.pos):
                self.aleatorio()
            elif self.botao_lutar.collidepoint(e.pos) and self.pronto:
                return "lutar"
        elif e.type == pygame.KEYDOWN:
            total = len(ROSTER)
            if e.key == pygame.K_ESCAPE:
                return "sair_online" if self.online else "titulo"
            if e.key in (pygame.K_LEFT, pygame.K_a):
                self.cursor = (self.cursor - 1) % total
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self.cursor = (self.cursor + 1) % total
            elif e.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self.cursor = (self.cursor + COLUNAS) % total
            elif e.key == pygame.K_SPACE:
                self.alternar(self.cursor)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.pronto:
                    return "lutar"
                self.alternar(self.cursor)
            elif e.key == pygame.K_BACKSPACE and self.escolhidos:
                self.escolhidos.pop()
            elif e.key == pygame.K_r:
                self.aleatorio()
            elif e.key == pygame.K_TAB and not self.online:
                self.mudar_dificuldade(1)
            elif pygame.K_1 <= e.key < pygame.K_1 + total:
                self.alternar(e.key - pygame.K_1)
        return None

    def atualizar(self, dt: float) -> None:
        self.tempo += dt

    # ---- Desenho --------------------------------------------------------------
    def desenhar(self, tela: pygame.Surface) -> None:
        tela.blit(self.fundo, (0, 0))
        titulo = "Escolha seu time  ·  online" if self.online else "Escolha seu time"
        escrever(tela, titulo, 34, cfg.BRANCO, negrito=True, topleft=(40, 14))
        dica = "Enter quando estiver pronto · Esc sai da partida" if self.online else "Enter para lutar"
        escrever(tela, f"Clique ou Espaço para escolher 3 ninjas · o primeiro começa a luta · {dica}",
                 16, cfg.CINZA_CLARO, topleft=(42, 54))

        painel(tela, self.botao_aleatorio, cor=cfg.PAINEL_CLARO)
        escrever(tela, "Aleatório (R)", 18, cfg.BRANCO, negrito=True, center=self.botao_aleatorio.center)

        for i, (base, cartao) in enumerate(zip(ROSTER, self.cartoes)):
            self.desenhar_cartao(tela, i, base, cartao)
        self.desenhar_time(tela)
        self.desenhar_dificuldade(tela)
        self.desenhar_botao_lutar(tela)

    def desenhar_cartao(self, tela, i: int, base, r: pygame.Rect) -> None:
        cor_nat = COR[base.natureza]
        focado = i == self.cursor
        escolhido = i in self.escolhidos
        painel(tela, r, cor=misturar(cfg.PAINEL, cor_nat, 0.08 if not focado else 0.16),
               borda=cor_nat if escolhido else (cfg.BRANCO if focado else cfg.BORDA),
               largura_borda=4 if escolhido else 2)

        # retrato
        centro = Vector2(r.x + 68, r.y + 82)
        pygame.draw.circle(tela, escurecer(cor_nat, 0.6), centro, 54)
        pygame.draw.circle(tela, cor_nat, centro, 54, 3)
        giro = math.sin(self.tempo * 2.5) * 25 if focado else 0
        desenhar_ninja(tela, base, centro, Vector2(0, 1).rotate(giro), self.tempo, escala=1.75)
        selo_natureza(tela, base.natureza, 15, midtop=(centro.x, r.y + 146))

        forte, fraco = forte_contra(base.natureza), fraco_contra(base.natureza)
        if forte is None:
            escrever(tela, "Sem vantagens", 14, cfg.CINZA_CLARO, center=(centro.x, r.y + 183))
            escrever(tela, "Sem fraquezas", 14, cfg.CINZA_CLARO, center=(centro.x, r.y + 203))
        else:
            escrever(tela, f"Forte: {forte.value}", 14, COR[forte], negrito=True, center=(centro.x, r.y + 183))
            escrever(tela, f"Fraco: {fraco.value}", 14, COR[fraco], negrito=True, center=(centro.x, r.y + 203))

        # nome e atributos
        x = r.x + 140
        escrever(tela, base.nome, 26, cfg.BRANCO, negrito=True, topleft=(x, r.y + 6))
        for k, (rotulo, atributo, maximo) in enumerate(ATRIBUTOS):
            y = r.y + 46 + k * 19
            valor = getattr(base, atributo)
            escrever(tela, rotulo, 14, cfg.CINZA_CLARO, sombra=False, topleft=(x, y - 2))
            barra(tela, (x + 82, y + 3, 120, 8), valor / maximo, cor_nat)
            escrever(tela, str(valor), 14, cfg.BRANCO, sombra=False, topright=(r.right - 12, y - 2))

        # jutsus
        for k, jutsu in enumerate(base.jutsus):
            y = r.y + 146 + k * 20
            pygame.draw.circle(tela, COR[jutsu.natureza], (x + 5, y + 10), 5)
            escrever(tela, jutsu.nome, 15, cfg.BRANCO, sombra=False, topleft=(x + 15, y))
            escrever(tela, jutsu.tipo.value, 13, cfg.CINZA, sombra=False, topright=(r.right - 12, y + 2))

        if escolhido:
            numero = self.escolhidos.index(i) + 1
            bolinha = (r.right - 22, r.y + 22)
            pygame.draw.circle(tela, cor_nat, bolinha, 16)
            escrever(tela, str(numero), 20, cfg.PRETO, negrito=True, sombra=False, center=bolinha)

    def desenhar_time(self, tela) -> None:
        r = self.area_time
        painel(tela, r)
        escrever(tela, "Seu time", 18, cfg.CINZA_CLARO, negrito=True, topleft=(r.x + 16, r.y + 8))
        for k in range(cfg.TAMANHO_TIME):
            vaga = pygame.Rect(r.x + 16 + k * 150, r.y + 36, 138, 86)
            pygame.draw.rect(tela, cfg.PAINEL_CLARO, vaga, border_radius=10)
            if k < len(self.escolhidos):
                base = ROSTER[self.escolhidos[k]]
                pygame.draw.rect(tela, COR[base.natureza], vaga, 2, border_radius=10)
                desenhar_ninja(tela, base, (vaga.x + 34, vaga.centery), Vector2(1, 0), self.tempo + k, escala=1.0)
                escrever(tela, base.nome, 18, cfg.BRANCO, negrito=True, midleft=(vaga.x + 64, vaga.centery - 10))
                escrever(tela, base.natureza.value, 14, COR[base.natureza], midleft=(vaga.x + 64, vaga.centery + 12))
            else:
                escrever(tela, f"Vaga {k + 1}", 16, cfg.CINZA, center=vaga.center)

    def desenhar_dificuldade(self, tela) -> None:
        r = self.area_dificuldade
        painel(tela, r)
        if self.online:  # no lugar da dificuldade: como está o amigo
            escrever(tela, "Seu amigo", 18, cfg.CINZA_CLARO, negrito=True, topleft=(r.x + 16, r.y + 8))
            if self.sessao.amigo_pronto:
                escrever(tela, "PRONTO!", 30, cfg.VERDE, negrito=True, center=(r.centerx, r.y + 62))
                escrever(tela, "Esperando você...", 16, cfg.CINZA_CLARO, center=(r.centerx, r.y + 100))
            else:
                pontos = "." * (int(self.tempo * 2) % 4)
                escrever(tela, f"escolhendo{pontos}", 26, cfg.AMARELO, negrito=True, center=(r.centerx, r.y + 70))
            return
        escrever(tela, "Dificuldade (Tab)", 18, cfg.CINZA_CLARO, negrito=True, topleft=(r.x + 16, r.y + 8))
        for botao, seta in ((self.botao_menos, -1), (self.botao_mais, 1)):
            painel(tela, botao, cor=cfg.PAINEL_CLARO, raio=10)
            cx, cy = botao.center
            pygame.draw.polygon(tela, cfg.BRANCO, [(cx + 8 * seta, cy), (cx - 6 * seta, cy - 10), (cx - 6 * seta, cy + 10)])
        dificuldade = DIFICULDADES[self.dificuldade]
        cor = (cfg.VERDE, cfg.AMARELO, cfg.VERMELHO)[self.dificuldade % 3]
        escrever(tela, dificuldade.nome, 30, cor, negrito=True, center=(r.centerx, self.botao_menos.centery))

    def desenhar_botao_lutar(self, tela) -> None:
        r = self.botao_lutar
        if self.aguardando:
            painel(tela, r, cor=cfg.PAINEL_CLARO, borda=cfg.VERDE, largura_borda=3)
            pontos = "." * (int(self.tempo * 2) % 4)
            escrever(tela, f"Esperando o amigo{pontos}", 26, cfg.BRANCO, negrito=True, center=(r.centerx, r.centery - 10))
            escrever(tela, "Enter ou clique para mudar o time", 15, cfg.CINZA_CLARO, center=(r.centerx, r.bottom - 22))
        elif self.pronto:
            brilho = (math.sin(self.tempo * 4) + 1) / 2
            painel(tela, r, cor=misturar((170, 60, 40), (215, 90, 50), brilho), borda=cfg.DOURADO, largura_borda=3)
            escrever(tela, "PRONTO!" if self.online else "LUTAR!", 44, cfg.BRANCO, negrito=True,
                     center=(r.centerx, r.centery - 8))
            escrever(tela, "Enter", 16, cfg.DOURADO, center=(r.centerx, r.bottom - 20))
        else:
            painel(tela, r, cor=cfg.PAINEL)
            falta = cfg.TAMANHO_TIME - len(self.escolhidos)
            escrever(tela, f"Escolha mais {falta}", 28, cfg.CINZA, negrito=True, center=r.center)
