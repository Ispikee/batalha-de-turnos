"""Tela da batalha: lê teclado e mouse, roda o combate e desenha tudo.

As regras ficam em combate.py; aqui só mostramos o que acontece
(partículas, números de dano, painel de jutsus, etc.).
"""
from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from jogo import config as cfg
from jogo.arena import Arena
from jogo.combate import ESQUIVA_RECARGA, TROCA_RECARGA, Combate, Comando, Lutador, Time
from jogo.desenho import (
    barra,
    cor_hp,
    desenhar_ninja,
    escrever,
    escurecer,
    fonte,
    misturar,
    painel,
    selo_natureza,
)
from jogo.ia import IA, Dificuldade
from jogo.jutsus import Efeito, Tipo
from jogo.naturezas import COR, Natureza, multiplicador

ROTULOS_JUTSU = ("Clique", "Clique dir.", "Q", "E")
TECLAS_JUTSU = ((pygame.K_j,), (pygame.K_k,), (pygame.K_q,), (pygame.K_e,))
TECLAS_ESQUIVA = (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT)

COR_JOGADOR = (120, 200, 255)
COR_INIMIGO = (255, 110, 100)


class Particula:
    __slots__ = ("pos", "vel", "vida", "total", "cor", "tamanho")

    def __init__(self, pos, vel, vida, cor, tamanho):
        self.pos, self.vel, self.vida, self.total, self.cor, self.tamanho = Vector2(pos), Vector2(vel), vida, vida, cor, tamanho


class TextoFlutuante:
    __slots__ = ("texto", "pos", "cor", "tamanho", "vida", "total", "negrito")

    def __init__(self, texto, pos, cor, tamanho=24, vida=0.9, negrito=True):
        self.texto, self.pos, self.cor, self.tamanho = texto, Vector2(pos), cor, tamanho
        self.vida = self.total = vida
        self.negrito = negrito


class Efeito2D:
    """Anéis de explosão e cortes de golpes corpo a corpo."""

    __slots__ = ("tipo", "pos", "cor", "raio", "angulo", "vida", "total")

    def __init__(self, tipo, pos, cor, raio, angulo=0.0, vida=0.3):
        self.tipo, self.pos, self.cor, self.raio, self.angulo = tipo, Vector2(pos), cor, raio, angulo
        self.vida = self.total = vida


def criar_fundo(arena: Arena) -> pygame.Surface:
    """Desenha o cenário uma vez só: grama, lagos, pedras e a cerca."""
    fundo = pygame.Surface((cfg.LARGURA, cfg.ALTURA))
    fundo.fill(cfg.FUNDO)
    r = arena.retangulo
    sorte = random.Random(7)

    fundo.set_clip(r)
    fundo.fill((92, 145, 74), r)
    for _ in range(2200):  # tufos de grama
        x, y = sorte.randint(r.left, r.right), sorte.randint(r.top, r.bottom)
        cor = misturar((92, 145, 74), sorte.choice([(60, 110, 50), (130, 180, 95)]), sorte.uniform(0.3, 0.7))
        pygame.draw.line(fundo, cor, (x, y), (x + sorte.randint(-2, 2), y - sorte.randint(2, 5)), 2)
    pygame.draw.circle(fundo, (105, 155, 84), r.center, 150, 3)  # círculo central da arena

    for lago in arena.lagos:
        pygame.draw.circle(fundo, (205, 185, 135), lago.centro, lago.r + 8)
    for lago in arena.lagos:
        pygame.draw.circle(fundo, (45, 105, 175), lago.centro, lago.r)
    for lago in arena.lagos:
        pygame.draw.circle(fundo, (65, 135, 205), lago.centro, max(1, lago.r - 12))
    for lago in arena.lagos:
        for k in range(2):
            onda = pygame.Rect(0, 0, lago.r * 0.7, 10)
            onda.center = (lago.x + sorte.uniform(-0.3, 0.3) * lago.r, lago.y + (k - 0.5) * lago.r * 0.6)
            pygame.draw.arc(fundo, (130, 185, 235), onda, 0.3, 2.8, 2)

    for pedra in arena.pedras:
        sombra = pygame.Rect(0, 0, pedra.r * 2.1, pedra.r * 1.4)
        sombra.center = (pedra.x + 6, pedra.y + pedra.r * 0.6)
        pygame.draw.ellipse(fundo, (60, 95, 50), sombra)
        pygame.draw.circle(fundo, (112, 108, 104), pedra.centro, pedra.r)
        pygame.draw.circle(fundo, (148, 143, 135), pedra.centro + Vector2(-0.25, -0.3) * pedra.r, pedra.r * 0.6)
        pygame.draw.circle(fundo, (78, 74, 70), pedra.centro, pedra.r, 2)
        pygame.draw.line(fundo, (85, 80, 76), pedra.centro + Vector2(0.1, -0.1) * pedra.r,
                         pedra.centro + Vector2(0.5, 0.35) * pedra.r, 2)
    fundo.set_clip(None)

    pygame.draw.rect(fundo, (105, 75, 45), r.inflate(16, 16), 8, border_radius=10)  # cerca
    pygame.draw.rect(fundo, (150, 110, 70), r.inflate(16, 16), 2, border_radius=10)
    return fundo


class TelaBatalha:
    def __init__(self, time_jogador, time_inimigo, dificuldade: Dificuldade, semente: int | None = None):
        self.time_jogador = list(time_jogador)
        self.time_inimigo = list(time_inimigo)
        self.dificuldade = dificuldade
        rng = random.Random(semente)
        self.combate = Combate(self.time_jogador, self.time_inimigo, rng=rng)
        self.ia = IA(self.combate, 1, dificuldade, random.Random(rng.random()))
        self.fundo = criar_fundo(self.combate.arena)
        self.camada_baixo = pygame.Surface((cfg.LARGURA, cfg.ALTURA), pygame.SRCALPHA)
        self.camada_cima = pygame.Surface((cfg.LARGURA, cfg.ALTURA), pygame.SRCALPHA)
        self.particulas: list[Particula] = []
        self.textos: list[TextoFlutuante] = []
        self.efeitos: list[Efeito2D] = []
        self.anuncio: tuple[str, tuple, float] | None = None
        self.contagem = 2.1
        self.lutem = 0.0
        self.pausado = False
        self.tempo_fim = 0.0
        self.tremor = 0.0
        self.relogio = 0.0
        self.esquiva_pedida = False
        self.troca_pedida: int | None = None
        self.buffer_jutsu = [0.0] * 4
        self.sorte = random.Random()

    # ---- Entrada -----------------------------------------------------------------
    @property
    def fim_visivel(self) -> bool:
        return self.combate.terminou and self.tempo_fim >= cfg.ATRASO_FIM

    def evento(self, e) -> str | None:
        if e.type == pygame.KEYDOWN:
            if self.fim_visivel:
                if e.key == pygame.K_r:
                    return "revanche"
                if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    return "menu"
                return None
            if e.key == pygame.K_ESCAPE:
                if self.pausado:
                    return "menu"
                self.pausado = True
                return None
            if e.key == pygame.K_p:
                self.pausado = not self.pausado
                return None
            if self.pausado:
                if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    self.pausado = False
                return None
            if e.key in TECLAS_ESQUIVA:
                self.esquiva_pedida = True
            elif pygame.K_1 <= e.key < pygame.K_1 + len(self.time_jogador):
                self.troca_pedida = e.key - pygame.K_1
            for i, teclas in enumerate(TECLAS_JUTSU):
                if e.key in teclas:
                    self.buffer_jutsu[i] = 0.25
        elif e.type == pygame.MOUSEBUTTONDOWN and not self.pausado:
            if e.button == 1:
                self.buffer_jutsu[0] = 0.25
            elif e.button == 3:
                self.buffer_jutsu[1] = 0.25
        return None

    def comando_jogador(self, dt: float) -> Comando:
        teclas = pygame.key.get_pressed()
        x = (teclas[pygame.K_d] or teclas[pygame.K_RIGHT]) - (teclas[pygame.K_a] or teclas[pygame.K_LEFT])
        y = (teclas[pygame.K_s] or teclas[pygame.K_DOWN]) - (teclas[pygame.K_w] or teclas[pygame.K_UP])
        c = Comando(mover=Vector2(x, y), mira=Vector2(pygame.mouse.get_pos()))

        botoes = pygame.mouse.get_pressed()
        segurando = [botoes[0], botoes[2], False, False]
        for i, grupo in enumerate(TECLAS_JUTSU):
            segurando[i] = segurando[i] or any(teclas[t] for t in grupo)
        eu = self.combate.ativo(0)
        for i in range(len(eu.base.jutsus)):
            self.buffer_jutsu[i] = max(0.0, self.buffer_jutsu[i] - dt)
        for i in range(len(eu.base.jutsus)):
            if (segurando[i] or self.buffer_jutsu[i] > 0) and self.combate.pode_usar(eu, i):
                c.jutsu = i
                self.buffer_jutsu[i] = 0.0
                break

        c.esquiva, self.esquiva_pedida = self.esquiva_pedida, False
        c.trocar, self.troca_pedida = self.troca_pedida, None
        return c

    # ---- Atualização ---------------------------------------------------------------
    def atualizar(self, dt: float) -> None:
        self.relogio += dt
        if self.pausado:
            return
        self.atualizar_visuais(dt)
        if self.contagem > 0:
            self.contagem -= dt
            if self.contagem <= 0:
                self.lutem = 0.8
            return
        self.lutem = max(0.0, self.lutem - dt)
        if self.combate.terminou:
            self.tempo_fim += dt
            return
        comandos = [self.comando_jogador(dt), self.ia.comando(dt)]
        self.combate.atualizar(dt, comandos)
        self.processar_eventos()

    def atualizar_visuais(self, dt: float) -> None:
        for p in self.particulas:
            p.vida -= dt
            p.pos += p.vel * dt
            p.vel *= max(0.0, 1 - 3 * dt)
        self.particulas = [p for p in self.particulas if p.vida > 0]
        for t in self.textos:
            t.vida -= dt
            t.pos.y -= 45 * dt
        self.textos = [t for t in self.textos if t.vida > 0]
        for ef in self.efeitos:
            ef.vida -= dt
        self.efeitos = [ef for ef in self.efeitos if ef.vida > 0]
        if self.anuncio is not None:
            texto, cor, vida = self.anuncio
            self.anuncio = (texto, cor, vida - dt) if vida - dt > 0 else None
        self.tremor = max(0.0, self.tremor - dt)

        # rastros
        for p in self.combate.projeteis:
            if self.sorte.random() < 0.8:
                self.particulas.append(Particula(p.pos, -p.vel * 0.05 + self.aleatorio(20), 0.3,
                                                 COR[p.jutsu.natureza], p.raio * 0.6))
        for time in self.combate.times:
            l = time.ativo
            if not l.vivo:
                continue
            if l.tem(Efeito.QUEIMADURA) and self.sorte.random() < 0.4:
                self.particulas.append(Particula(l.pos + self.aleatorio(14), Vector2(0, -60), 0.5, cfg.LARANJA, 4))
            if (l.tem(Efeito.VELOCIDADE) or l.ocupado) and l.vel.length_squared() > 100:
                cor = COR[l.investida.jutsu.natureza] if l.investida else cfg.BRANCO
                self.particulas.append(Particula(l.pos + self.aleatorio(10), Vector2(), 0.25, cor, 8))

    def aleatorio(self, tamanho: float) -> Vector2:
        return Vector2(self.sorte.uniform(-tamanho, tamanho), self.sorte.uniform(-tamanho, tamanho))

    def estourar(self, pos, cor, quantidade: int, velocidade: float = 180, tamanho: float = 5, vida: float = 0.45):
        for _ in range(quantidade):
            direcao = Vector2(1, 0).rotate(self.sorte.uniform(0, 360)) * self.sorte.uniform(0.3, 1) * velocidade
            self.particulas.append(Particula(pos, direcao, vida * self.sorte.uniform(0.6, 1), cor, tamanho))

    def anunciar(self, texto: str, cor) -> None:
        self.anuncio = (texto, cor, 1.6)

    def processar_eventos(self) -> None:
        for ev in self.combate.eventos:
            cor_nat = COR[ev.natureza] if ev.natureza is not None else cfg.BRANCO
            if ev.tipo == "dano":
                cor = cfg.AMARELO if ev.critico else cfg.BRANCO
                tamanho = 30 if ev.eficacia > 1 else 22 if ev.eficacia < 1 else 26
                self.textos.append(TextoFlutuante(f"{ev.valor}{'!' if ev.critico else ''}", ev.pos + Vector2(0, -40), cor, tamanho))
                if ev.eficacia > 1:
                    self.textos.append(TextoFlutuante("Super efetivo!", ev.pos + Vector2(0, -68), cfg.LARANJA, 18, 1.1))
                elif ev.eficacia < 1:
                    self.textos.append(TextoFlutuante("Pouco efetivo...", ev.pos + Vector2(0, -68), cfg.CINZA_CLARO, 16, 1.0))
                self.estourar(ev.pos, cor_nat, 14)
                self.tremor = max(self.tremor, 0.18 if ev.eficacia > 1 or ev.critico else 0.1)
            elif ev.tipo == "queimadura":
                self.textos.append(TextoFlutuante(str(ev.valor), ev.pos + Vector2(14, -34), cfg.LARANJA, 18, 0.7))
            elif ev.tipo == "cura":
                self.textos.append(TextoFlutuante(f"+{ev.valor}", ev.pos + Vector2(0, -40), cfg.VERDE, 28))
                self.estourar(ev.pos, cfg.VERDE, 18, velocidade=120)
            elif ev.tipo == "texto":
                self.textos.append(TextoFlutuante(ev.texto, ev.pos + Vector2(0, -88), cor_nat, 18, 1.1))
            elif ev.tipo == "jutsu":
                self.textos.append(TextoFlutuante(ev.texto, ev.pos + Vector2(0, -52), cor_nat, 16, 0.7, negrito=False))
            elif ev.tipo == "troca":
                self.estourar(ev.pos, (210, 210, 220), 26, velocidade=140, tamanho=10, vida=0.6)
                cor = COR_JOGADOR if ev.lado == 0 else COR_INIMIGO
                self.anunciar(f"{ev.texto} entra na luta!" if ev.lado == 0 else f"O rival manda {ev.texto}!", cor)
            elif ev.tipo == "nocaute":
                self.estourar(ev.pos, cfg.CINZA_CLARO, 30, velocidade=220, tamanho=6, vida=0.7)
                cor = COR_JOGADOR if ev.lado == 0 else COR_INIMIGO
                self.anunciar(f"{ev.texto} foi derrotado!", cor)
                self.tremor = 0.3
            elif ev.tipo == "explosao":
                self.efeitos.append(Efeito2D("anel", ev.pos, cor_nat, ev.raio, vida=0.35))
                self.estourar(ev.pos, cor_nat, max(6, int(ev.raio / 3)), velocidade=ev.raio * 3)
                if ev.raio > 40:
                    self.tremor = max(self.tremor, 0.15)
            elif ev.tipo == "corte":
                self.efeitos.append(Efeito2D("corte", ev.pos, cor_nat, ev.raio, ev.angulo, vida=0.15))
            elif ev.tipo == "esquiva":
                self.estourar(ev.pos, (220, 220, 230), 10, velocidade=90, tamanho=8, vida=0.35)
        self.combate.eventos.clear()

    # ---- Desenho ----------------------------------------------------------------------
    def desenhar(self, tela: pygame.Surface) -> None:
        tela.blit(self.fundo, (0, 0))
        self.camada_baixo.fill((0, 0, 0, 0))
        self.camada_cima.fill((0, 0, 0, 0))

        self.desenhar_areas()
        lutadores = [(time, time.ativo) for time in self.combate.times
                     if time.ativo.vivo or time.espera_nocaute > 0 or self.combate.terminou]
        for time, l in lutadores:
            self.desenhar_marcas_no_chao(l)
        self.desenhar_mira()
        tela.blit(self.camada_baixo, (0, 0))

        for time, l in sorted(lutadores, key=lambda par: par[1].pos.y):
            self.desenhar_lutador(tela, l)
        self.desenhar_projeteis(tela)
        self.desenhar_particulas_e_efeitos()
        tela.blit(self.camada_cima, (0, 0))
        for t in self.textos:
            alfa = int(255 * min(1.0, t.vida / (t.total * 0.5)))
            escrever(tela, t.texto, t.tamanho, t.cor, negrito=t.negrito, alfa=alfa, center=(round(t.pos.x), round(t.pos.y)))

        if self.tremor > 0:
            forca = round(6 * self.tremor / 0.3) + 1
            tela.scroll(self.sorte.randint(-forca, forca), self.sorte.randint(-forca, forca))

        self.desenhar_hud(tela)
        self.desenhar_anuncio(tela)
        if self.contagem > 0 or self.lutem > 0:
            self.desenhar_contagem(tela)
        if self.pausado:
            self.desenhar_pausa(tela)
        elif self.fim_visivel:
            self.desenhar_fim(tela)

    def desenhar_areas(self) -> None:
        for area in self.combate.areas:
            cor = COR[area.jutsu.natureza]
            raio = area.jutsu.raio
            pygame.draw.circle(self.camada_baixo, (*cor, 60), area.pos, raio * area.progresso)
            pygame.draw.circle(self.camada_baixo, (*cor, 220), area.pos, raio, 3)
            if area.restante < 0.2 and int(self.relogio * 30) % 2 == 0:
                pygame.draw.circle(self.camada_baixo, (255, 255, 255, 90), area.pos, raio)

    def desenhar_marcas_no_chao(self, l: Lutador) -> None:
        cor = COR_JOGADOR if l.lado == 0 else COR_INIMIGO
        if not l.vivo:
            return
        pygame.draw.circle(self.camada_baixo, (*COR[l.natureza], 170), l.pos + Vector2(0, 4), 30, 3)
        pygame.draw.circle(self.camada_baixo, (*cor, 110), l.pos + Vector2(0, 4), 34, 2)
        if l.tem(Efeito.LENTIDAO):
            pygame.draw.circle(self.camada_baixo, (90, 160, 255, 90), l.pos + Vector2(0, 4), 30)

    def desenhar_mira(self) -> None:
        eu = self.combate.ativo(0)
        if not eu.vivo or self.combate.terminou or self.pausado:
            return
        mouse = Vector2(pygame.mouse.get_pos())
        direcao = mouse - eu.pos
        if direcao.length_squared() < 1:
            return
        direcao = direcao.normalize()
        for k in range(1, 7):
            ponto = eu.pos + direcao * (30 + k * 16)
            pygame.draw.circle(self.camada_baixo, (255, 255, 255, 150 - k * 18), ponto, 3)
        pygame.draw.circle(self.camada_baixo, (255, 255, 255, 200), mouse, 11, 2)
        pygame.draw.line(self.camada_baixo, (255, 255, 255, 200), mouse - Vector2(16, 0), mouse - Vector2(6, 0), 2)
        pygame.draw.line(self.camada_baixo, (255, 255, 255, 200), mouse + Vector2(6, 0), mouse + Vector2(16, 0), 2)
        pygame.draw.line(self.camada_baixo, (255, 255, 255, 200), mouse - Vector2(0, 16), mouse - Vector2(0, 6), 2)
        pygame.draw.line(self.camada_baixo, (255, 255, 255, 200), mouse + Vector2(0, 6), mouse + Vector2(0, 16), 2)

    def desenhar_lutador(self, tela, l: Lutador) -> None:
        if l.vivo and l.invulneravel > 0 and l.esquiva <= 0 and int(self.relogio * 20) % 2 == 0:
            return  # pisca ao entrar na luta
        andando = min(1.0, l.vel.length() / 200)
        desenhar_ninja(tela, l.base, l.pos, l.mira, self.relogio + l.lado * 0.7, nocauteado=not l.vivo,
                       piscar=l.flash > 0, andando=andando)
        if not l.vivo:
            return
        cor = COR_JOGADOR if l.lado == 0 else COR_INIMIGO
        topo = l.pos + Vector2(0, -38)
        pygame.draw.polygon(tela, cor, [topo + Vector2(-7, -8), topo + Vector2(7, -8), topo])
        if l.atordoado:
            for k in range(3):
                angulo = self.relogio * 6 + k * math.tau / 3
                estrela = l.pos + Vector2(math.cos(angulo) * 18, -30 + math.sin(angulo) * 6)
                pygame.draw.circle(tela, cfg.AMARELO, estrela, 4)
        if l.tem(Efeito.ESCUDO):
            pygame.draw.circle(self.camada_cima, (190, 160, 110, 60), l.pos, 34)
            pygame.draw.circle(self.camada_cima, (230, 200, 140, 200), l.pos, 34, 3)
        if l.tem(Efeito.FORCA):
            pulso = 30 + math.sin(self.relogio * 10) * 4
            pygame.draw.circle(self.camada_cima, (255, 80, 60, 140), l.pos, pulso, 2)

    def desenhar_projeteis(self, tela) -> None:
        for p in self.combate.projeteis:
            cor = COR[p.jutsu.natureza]
            if p.jutsu.natureza is Natureza.TERRA:
                pygame.draw.circle(tela, (120, 95, 70), p.pos, p.raio)
                pygame.draw.circle(tela, (160, 135, 105), p.pos + Vector2(-3, -3), p.raio * 0.5)
                pygame.draw.circle(tela, (70, 55, 40), p.pos, p.raio, 2)
                continue
            pygame.draw.circle(self.camada_cima, (*cor, 90), p.pos, p.raio * 1.9)
            if p.jutsu.natureza is Natureza.NEUTRO:  # kunai
                direcao = p.vel.normalize()
                pygame.draw.line(tela, (60, 60, 70), p.pos - direcao * 12, p.pos + direcao * 8, 4)
                pygame.draw.line(tela, (225, 228, 235), p.pos, p.pos + direcao * 9, 3)
                continue
            pygame.draw.circle(tela, cor, p.pos, p.raio)
            pygame.draw.circle(tela, misturar(cor, cfg.BRANCO, 0.7), p.pos, p.raio * 0.5)

    def desenhar_particulas_e_efeitos(self) -> None:
        for p in self.particulas:
            t = p.vida / p.total
            pygame.draw.circle(self.camada_cima, (*p.cor, int(220 * t)), p.pos, max(1.0, p.tamanho * (0.4 + 0.6 * t)))
        for ef in self.efeitos:
            t = ef.vida / ef.total
            if ef.tipo == "anel":
                raio = ef.raio * (1.15 - 0.35 * t)
                pygame.draw.circle(self.camada_cima, (*ef.cor, int(110 * t)), ef.pos, raio)
                pygame.draw.circle(self.camada_cima, (255, 255, 255, int(220 * t)), ef.pos, raio, 4)
            elif ef.tipo == "corte":
                ret = pygame.Rect(0, 0, ef.raio * 2, ef.raio * 2)
                ret.center = ef.pos
                inicio = math.radians(-ef.angulo - 70)
                fim = math.radians(-ef.angulo + 70)
                pygame.draw.arc(self.camada_cima, (255, 255, 255, int(255 * t)), ret, inicio, fim, 6)
                pygame.draw.arc(self.camada_cima, (*ef.cor, int(255 * t)), ret.inflate(-12, -12), inicio, fim, 4)

    # ---- Painéis ------------------------------------------------------------------------
    def desenhar_hud(self, tela) -> None:
        self.desenhar_painel_time(tela, self.combate.times[0], pygame.Rect(16, 8, 520, 78), espelhado=False)
        self.desenhar_painel_time(tela, self.combate.times[1], pygame.Rect(cfg.LARGURA - 536, 8, 520, 78), espelhado=True)
        minutos, segundos = divmod(int(self.combate.tempo), 60)
        escrever(tela, f"{minutos}:{segundos:02d}", 26, cfg.BRANCO, negrito=True, center=(cfg.LARGURA / 2, 32))
        escrever(tela, self.dificuldade.nome, 15, cfg.CINZA_CLARO, center=(cfg.LARGURA / 2, 62))
        self.desenhar_barra_jutsus(tela)

    def desenhar_painel_time(self, tela, time: Time, r: pygame.Rect, espelhado: bool) -> None:
        l = time.ativo
        cor_lado = COR_INIMIGO if espelhado else COR_JOGADOR
        painel(tela, r, borda=cor_lado)

        retrato = Vector2(r.right - 44 if espelhado else r.x + 44, r.centery)
        pygame.draw.circle(tela, escurecer(COR[l.natureza], 0.55), retrato, 30)
        desenhar_ninja(tela, l.base, retrato, Vector2(-1 if espelhado else 1, 0.4), self.relogio, escala=1.05,
                       nocauteado=not l.vivo)

        x_texto = r.x + 86 if not espelhado else r.right - 86
        lado = "topleft" if not espelhado else "topright"
        nome = escrever(tela, l.nome, 22, cfg.BRANCO, negrito=True, **{lado: (x_texto, r.y + 6)})
        if espelhado:
            selo_natureza(tela, l.natureza, 13, topright=(nome.x - 8, r.y + 12))
        else:
            selo_natureza(tela, l.natureza, 13, topleft=(nome.right + 8, r.y + 12))

        largura_barra = 260
        x_barra = x_texto if not espelhado else x_texto - largura_barra
        barra(tela, (x_barra, r.y + 40, largura_barra, 14), l.fracao_hp, cor_hp(l.fracao_hp))
        texto_hp = f"{l.hp_inteiro}/{l.hp_max}"
        if espelhado:
            escrever(tela, texto_hp, 15, cfg.BRANCO, topright=(x_barra + largura_barra, r.y + 56))
        else:
            escrever(tela, texto_hp, 15, cfg.BRANCO, topleft=(x_barra, r.y + 56))

        icones = [(e, c) for e, c in ((Efeito.QUEIMADURA, cfg.LARANJA), (Efeito.LENTIDAO, cfg.AZUL),
                                       (Efeito.ATORDOAR, cfg.AMARELO), (Efeito.ESCUDO, (220, 190, 130)),
                                       (Efeito.VELOCIDADE, cfg.VERDE), (Efeito.FORCA, cfg.VERMELHO)) if l.tem(e)]
        if espelhado:
            x_icone = x_barra + largura_barra - 70
            for efeito, cor in icones:
                x_icone = escrever(tela, efeito.value, 13, cor, negrito=True, topright=(x_icone, r.y + 57)).x - 10
        else:
            x_icone = x_barra + 70
            for efeito, cor in icones:
                x_icone = escrever(tela, efeito.value, 13, cor, negrito=True, topleft=(x_icone, r.y + 57)).right + 10

        # bolinhas do time (com o número da tecla de troca)
        for k, membro in enumerate(time.lutadores):
            if espelhado:
                centro = Vector2(r.x + 28 + k * 40, r.y + 30)
            else:
                centro = Vector2(r.right - 28 - (len(time.lutadores) - 1 - k) * 40, r.y + 30)
            cor = membro.base.cor if membro.vivo else cfg.CINZA_ESCURO
            pygame.draw.circle(tela, cor, centro, 15)
            if k == time.ativo_idx:
                pygame.draw.circle(tela, cfg.BRANCO, centro, 17, 3)
            if membro.vivo:
                barra(tela, (centro.x - 15, centro.y + 22, 30, 5), membro.fracao_hp, cor_hp(membro.fracao_hp))
            else:
                pygame.draw.line(tela, cfg.VERMELHO, centro - Vector2(8, 8), centro + Vector2(8, 8), 3)
                pygame.draw.line(tela, cfg.VERMELHO, centro + Vector2(-8, 8), centro + Vector2(8, -8), 3)
            if not espelhado:
                escrever(tela, str(k + 1), 15, cfg.BRANCO, negrito=True, center=centro)
        if not espelhado and time.recarga_troca > 0 and time.espera_nocaute <= 0:
            escrever(tela, f"troca em {time.recarga_troca:.1f}s", 13, cfg.CINZA_CLARO,
                     midtop=(r.right - 68, r.y + 60))
        if not espelhado and time.espera_nocaute > 0:
            escrever(tela, "Escolha: 1 2 3", 14, cfg.AMARELO, negrito=True, midtop=(r.right - 68, r.y + 60))

    def desenhar_barra_jutsus(self, tela) -> None:
        eu = self.combate.ativo(0)
        rival = self.combate.ativo(1)
        largura, altura, espaco = 230, 86, 10
        total = len(eu.base.jutsus) * (largura + espaco) + 120
        x = (cfg.LARGURA - total) // 2
        y = cfg.ALTURA - altura - 10

        for i, jutsu in enumerate(eu.base.jutsus):
            r = pygame.Rect(x + i * (largura + espaco), y, largura, altura)
            cor = COR[jutsu.natureza]
            cura_inutil = jutsu.efeito is Efeito.CURA and eu.hp >= eu.hp_max
            disponivel = eu.vivo and eu.recargas[i] <= 0 and not cura_inutil
            painel(tela, r, cor=cfg.PAINEL if disponivel else escurecer(cfg.PAINEL, 0.3), borda=cor if disponivel else cfg.BORDA)
            pygame.draw.rect(tela, cor, (r.x, r.y + 10, 6, r.h - 20), border_radius=3)

            largura_rotulo = fonte(13, True).size(ROTULOS_JUTSU[i])[0]
            tecla = pygame.Rect(r.x + 14, r.y + 8, largura_rotulo + 12, 20)
            pygame.draw.rect(tela, cfg.AMARELO, tecla, border_radius=5)
            escrever(tela, ROTULOS_JUTSU[i], 13, cfg.PRETO, negrito=True, sombra=False, center=tecla.center)

            escrever(tela, jutsu.nome, 18, cfg.BRANCO if disponivel else cfg.CINZA, negrito=True, topleft=(r.x + 14, r.y + 32))
            detalhe = jutsu.tipo.value if not jutsu.causa_dano else f"{jutsu.tipo.value} · {jutsu.poder}"
            if jutsu.tipo is Tipo.SUPORTE:
                detalhe = f"Suporte · {jutsu.efeito.value}"
            escrever(tela, detalhe, 14, cfg.CINZA_CLARO, sombra=False, topleft=(r.x + 14, r.y + 58))

            if eu.recargas[i] > 0:
                fracao = eu.recargas[i] / jutsu.recarga
                cobertura = pygame.Surface((r.w, max(1, round(r.h * fracao))), pygame.SRCALPHA)
                cobertura.fill((0, 0, 0, 150))
                tela.blit(cobertura, (r.x, r.bottom - cobertura.get_height()))
                escrever(tela, f"{eu.recargas[i]:.1f}s", 20, cfg.BRANCO, negrito=True, topright=(r.right - 10, r.y + 5))
            elif jutsu.causa_dano and rival.vivo:  # seta: forte (verde) ou fraco (vermelho) contra o rival
                m = multiplicador(jutsu.natureza, rival.natureza)
                cx, cy = r.right - 18, r.y + 18
                if m > 1:
                    pygame.draw.polygon(tela, cfg.VERDE, [(cx, cy - 8), (cx - 8, cy + 6), (cx + 8, cy + 6)])
                elif m < 1:
                    pygame.draw.polygon(tela, cfg.VERMELHO, [(cx, cy + 8), (cx - 8, cy - 6), (cx + 8, cy - 6)])

        r = pygame.Rect(x + len(eu.base.jutsus) * (largura + espaco), y, 120, altura)
        painel(tela, r)
        tecla = pygame.Rect(r.x + 14, r.y + 8, 62, 20)
        pygame.draw.rect(tela, cfg.AMARELO, tecla, border_radius=5)
        escrever(tela, "Espaço", 13, cfg.PRETO, negrito=True, sombra=False, center=tecla.center)
        escrever(tela, "Esquiva", 19, cfg.BRANCO, negrito=True, topleft=(r.x + 14, r.y + 32))
        if eu.recarga_esquiva > 0:
            fracao = eu.recarga_esquiva / ESQUIVA_RECARGA
            cobertura = pygame.Surface((r.w, max(1, round(r.h * fracao))), pygame.SRCALPHA)
            cobertura.fill((0, 0, 0, 150))
            tela.blit(cobertura, (r.x, r.bottom - cobertura.get_height()))

    def desenhar_anuncio(self, tela) -> None:
        if self.anuncio is None:
            return
        texto, cor, vida = self.anuncio
        alfa = int(255 * min(1.0, vida / 0.4))
        caixa = pygame.Surface((560, 44), pygame.SRCALPHA)
        pygame.draw.rect(caixa, (20, 22, 32, int(alfa * 0.8)), caixa.get_rect(), border_radius=22)
        tela.blit(caixa, caixa.get_rect(center=(cfg.LARGURA / 2, 128)))
        escrever(tela, texto, 24, cor, negrito=True, alfa=alfa, center=(cfg.LARGURA / 2, 128))

    def desenhar_contagem(self, tela) -> None:
        if self.contagem > 0:
            numero = 3 if self.contagem > 1.4 else 2 if self.contagem > 0.7 else 1
            fase = (self.contagem % 0.7) / 0.7
            escrever(tela, str(numero), int(90 + 60 * fase), cfg.BRANCO, negrito=True, center=(cfg.LARGURA / 2, cfg.ALTURA / 2 - 20))
        else:
            alfa = int(255 * min(1.0, self.lutem / 0.3))
            escrever(tela, "LUTEM!", 96, cfg.DOURADO, negrito=True, alfa=alfa, center=(cfg.LARGURA / 2, cfg.ALTURA / 2 - 20))

    def veu(self, tela, alfa: int = 170) -> None:
        cobertura = pygame.Surface((cfg.LARGURA, cfg.ALTURA), pygame.SRCALPHA)
        cobertura.fill((0, 0, 0, alfa))
        tela.blit(cobertura, (0, 0))

    def desenhar_pausa(self, tela) -> None:
        self.veu(tela, 150)
        meio = cfg.LARGURA / 2
        escrever(tela, "PAUSADO", 80, cfg.BRANCO, negrito=True, center=(meio, cfg.ALTURA / 2 - 40))
        escrever(tela, "P ou Enter: continuar  ·  Esc: voltar para a escolha de time", 22, cfg.CINZA_CLARO,
                 center=(meio, cfg.ALTURA / 2 + 30))

    def desenhar_fim(self, tela) -> None:
        self.veu(tela, 175)
        meio_x, meio_y = cfg.LARGURA / 2, cfg.ALTURA / 2
        vencedor = self.combate.vencedor
        if vencedor == 0:
            titulo, cor = "VITÓRIA!", cfg.DOURADO
        elif vencedor == 1:
            titulo, cor = "DERROTA...", cfg.VERMELHO
        else:
            titulo, cor = "EMPATE", cfg.BRANCO
        escrever(tela, titulo, 100, cor, negrito=True, center=(meio_x, meio_y - 120))
        minutos, segundos = divmod(int(self.combate.tempo), 60)
        escrever(tela, f"Tempo de luta: {minutos}:{segundos:02d}", 24, cfg.BRANCO, center=(meio_x, meio_y - 40))

        time = self.combate.times[0]
        for k, l in enumerate(time.lutadores):
            centro = Vector2(meio_x + (k - (len(time.lutadores) - 1) / 2) * 150, meio_y + 40)
            desenhar_ninja(tela, l.base, centro, Vector2(0, 1), self.relogio + k, escala=1.4, nocauteado=not l.vivo)
            escrever(tela, l.nome, 20, cfg.BRANCO, negrito=True, center=(centro.x, centro.y + 50))
            escrever(tela, f"{l.hp_inteiro}/{l.hp_max} HP", 15, cor_hp(l.fracao_hp) if l.vivo else cfg.CINZA,
                     center=(centro.x, centro.y + 72))

        escrever(tela, "R: revanche  ·  Enter: escolher outro time", 24, cfg.CINZA_CLARO,
                 center=(meio_x, meio_y + 170))
