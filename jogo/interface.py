"""Tudo que é tela, desenho, teclado e mouse fica aqui.

As regras da luta ficam em batalha.py; este arquivo só mostra o que acontece.
Os lutadores são desenhados com formas simples: troque por sprites (imagens)
quando quiser, na função desenhar_lutador().
"""
from __future__ import annotations

import math
import random
from enum import Enum, auto

import pygame

from jogo import config as cfg
from jogo.batalha import CUSTO_MP, Acao, Batalha, Resultado
from jogo.personagem import Personagem, criar_heroi, criar_inimigo


class Estado(Enum):
    ESCOLHENDO = auto()  # esperando você escolher uma ação
    VEZ_DO_INIMIGO = auto()  # pequena pausa antes do inimigo agir
    FIM = auto()  # alguém venceu


OPCOES = [Acao.ATACAR, Acao.MAGIA, Acao.DEFENDER, Acao.CURAR]

# Centro de cada lutador na tela
POS_HEROI = (250, 305)
POS_INIMIGO = (700, 170)

# Áreas da parte de baixo da tela
AREA_MENU = pygame.Rect(20, 420, 300, 160)
AREA_LOG = pygame.Rect(340, 420, 600, 160)


class Jogo:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(cfg.TITULO)
        self.tela = pygame.display.set_mode((cfg.LARGURA, cfg.ALTURA))
        self.relogio = pygame.time.Clock()

        self.fonte_titulo = pygame.font.Font(None, 96)
        self.fonte_numero = pygame.font.Font(None, 52)
        self.fonte = pygame.font.Font(None, 34)
        self.fonte_media = pygame.font.Font(None, 28)
        self.fonte_pequena = pygame.font.Font(None, 22)

        self.fundo = self.criar_fundo()
        self.botoes_menu = [
            pygame.Rect(AREA_MENU.x + 12, AREA_MENU.y + 10 + i * 30, AREA_MENU.w - 24, 28)
            for i in range(len(OPCOES))
        ]
        self.rodando = True
        self.reiniciar()

    def reiniciar(self) -> None:
        self.heroi = criar_heroi()
        self.inimigo = criar_inimigo()
        self.batalha = Batalha(self.heroi, self.inimigo)
        self.estado = Estado.ESCOLHENDO
        self.opcao = 0
        self.inimigo_age_em = 0
        self.fim_em = 0
        # Valores "mostrados" nas barras: deslizam até o valor real (animação)
        self.barras = {p: {"hp": float(p.hp), "mp": float(p.mp)} for p in (self.heroi, self.inimigo)}
        self.tremendo_ate = {self.heroi: 0, self.inimigo: 0}
        self.numeros: list[dict] = []  # números de dano/cura que sobem e somem

    # ---- Laço principal ------------------------------------------------------
    def executar(self) -> None:
        while self.rodando:
            dt = self.relogio.tick(cfg.FPS)
            self.tratar_eventos()
            self.atualizar(dt)
            self.desenhar()
            pygame.display.flip()
        pygame.quit()

    # ---- Entrada (teclado e mouse) --------------------------------------------
    def tratar_eventos(self) -> None:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.rodando = False
            elif evento.type == pygame.KEYDOWN:
                self.tecla_pressionada(evento.key)
            elif evento.type == pygame.MOUSEMOTION and self.estado is Estado.ESCOLHENDO:
                indice = self.opcao_no_ponto(evento.pos)
                if indice is not None:
                    self.opcao = indice
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if self.estado is Estado.ESCOLHENDO:
                    indice = self.opcao_no_ponto(evento.pos)
                    if indice is not None:
                        self.opcao = indice
                        self.confirmar()
                elif self.fim_visivel():
                    self.reiniciar()

    def tecla_pressionada(self, tecla: int) -> None:
        if tecla == pygame.K_ESCAPE:
            self.rodando = False
        elif self.estado is Estado.FIM:
            if self.fim_visivel() and tecla in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                self.reiniciar()
        elif self.estado is Estado.ESCOLHENDO:
            if tecla in (pygame.K_UP, pygame.K_w):
                self.opcao = (self.opcao - 1) % len(OPCOES)
            elif tecla in (pygame.K_DOWN, pygame.K_s):
                self.opcao = (self.opcao + 1) % len(OPCOES)
            elif tecla in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.confirmar()
            elif pygame.K_1 <= tecla < pygame.K_1 + len(OPCOES):
                self.opcao = tecla - pygame.K_1
                self.confirmar()

    def opcao_no_ponto(self, ponto: tuple[int, int]) -> int | None:
        for i, botao in enumerate(self.botoes_menu):
            if botao.collidepoint(ponto):
                return i
        return None

    def confirmar(self) -> None:
        acao = OPCOES[self.opcao]
        if not self.batalha.pode_usar(self.heroi, acao):
            if acao is Acao.CURAR and self.heroi.hp >= self.heroi.hp_max:
                aviso = "Seu HP já está cheio."
            else:
                aviso = f"MP insuficiente para {acao.value}."
            if self.batalha.log[-1] != aviso:
                self.batalha.log.append(aviso)
            return

        self.animar(self.batalha.executar(self.heroi, acao))
        if self.batalha.terminou:
            self.encerrar()
        else:
            self.estado = Estado.VEZ_DO_INIMIGO
            self.inimigo_age_em = pygame.time.get_ticks() + cfg.ATRASO_INIMIGO

    # ---- Atualização ----------------------------------------------------------
    def atualizar(self, dt: int) -> None:
        agora = pygame.time.get_ticks()

        if self.estado is Estado.VEZ_DO_INIMIGO and agora >= self.inimigo_age_em:
            acao = self.batalha.escolher_acao_inimigo()
            self.animar(self.batalha.executar(self.inimigo, acao))
            if self.batalha.terminou:
                self.encerrar()
            else:
                self.estado = Estado.ESCOLHENDO

        # Barras deslizam suavemente até o valor real
        passo = min(1.0, dt * 0.008)
        for personagem, barra in self.barras.items():
            barra["hp"] += (personagem.hp - barra["hp"]) * passo
            barra["mp"] += (personagem.mp - barra["mp"]) * passo

        self.numeros = [n for n in self.numeros if agora - n["inicio"] < 1000]

    def encerrar(self) -> None:
        self.estado = Estado.FIM
        self.fim_em = pygame.time.get_ticks() + cfg.ATRASO_FIM

    def fim_visivel(self) -> bool:
        return self.estado is Estado.FIM and pygame.time.get_ticks() >= self.fim_em

    def animar(self, resultado: Resultado) -> None:
        agora = pygame.time.get_ticks()
        if resultado.alvo is not None and resultado.dano:
            self.tremendo_ate[resultado.alvo] = agora + 350
            texto = f"-{resultado.dano}" + ("!" if resultado.critico else "")
            cor = cfg.AMARELO if resultado.critico else cfg.VERMELHO
            self.numeros.append({"texto": texto, "pos": self.posicao(resultado.alvo), "cor": cor, "inicio": agora})
        if resultado.cura:
            self.numeros.append(
                {"texto": f"+{resultado.cura}", "pos": self.posicao(resultado.ator), "cor": cfg.VERDE, "inicio": agora}
            )

    def posicao(self, personagem: Personagem) -> tuple[int, int]:
        return POS_HEROI if personagem is self.heroi else POS_INIMIGO

    # ---- Desenho --------------------------------------------------------------
    def desenhar(self) -> None:
        self.tela.blit(self.fundo, (0, 0))
        self.desenhar_lutador(self.inimigo, olhando_para=-1)
        self.desenhar_lutador(self.heroi, olhando_para=1)
        self.desenhar_numeros()
        self.desenhar_status(self.inimigo, (40, 36), mostrar_mp=False)
        self.desenhar_status(self.heroi, (590, 290), mostrar_mp=True)
        self.escrever(f"Turno {self.batalha.turno}", self.fonte_media, cfg.PRETO, topright=(cfg.LARGURA - 20, 16))
        self.desenhar_menu()
        self.desenhar_log()
        if self.fim_visivel():
            self.desenhar_fim()

    def criar_fundo(self) -> pygame.Surface:
        """Desenha o cenário uma vez só (céu, chão e plataformas)."""
        fundo = pygame.Surface((cfg.LARGURA, cfg.ALTURA))
        horizonte, chao_fim = 230, 410
        for y in range(chao_fim):
            if y < horizonte:
                cor = misturar(cfg.CEU_TOPO, cfg.CEU_BAIXO, y / horizonte)
            else:
                cor = misturar(cfg.CHAO_TOPO, cfg.CHAO_BAIXO, (y - horizonte) / (chao_fim - horizonte))
            pygame.draw.line(fundo, cor, (0, y), (cfg.LARGURA, y))
        pygame.draw.rect(fundo, cfg.PRETO, (0, chao_fim, cfg.LARGURA, cfg.ALTURA - chao_fim))

        for (x, y), largura in ((POS_INIMIGO, 260), (POS_HEROI, 300)):
            plataforma = pygame.Rect(0, 0, largura, largura // 4)
            plataforma.center = (x, y + 60)
            pygame.draw.ellipse(fundo, cfg.PLATAFORMA, plataforma)
        return fundo

    def desenhar_lutador(self, p: Personagem, olhando_para: int) -> None:
        agora = pygame.time.get_ticks()
        cx, cy = self.posicao(p)

        if not p.vivo:  # derrotado: fica "achatado" no chão
            corpo = pygame.Rect(0, 0, 130, 36)
            corpo.center = (cx, cy + 45)
            pygame.draw.ellipse(self.tela, misturar(p.cor, cfg.CINZA_ESCURO, 0.6), corpo)
            return

        if agora < self.tremendo_ate[p]:  # levou dano: treme e pisca
            if (agora // 60) % 2 == 0:
                return
            cx += random.randint(-6, 6)
        fase = 0.0 if p is self.heroi else 1.5
        cy += round(math.sin(agora / 250 + fase) * 4)  # "respiração"

        if p is self.inimigo:  # orelhas pontudas
            for lado in (-1, 1):
                pygame.draw.polygon(
                    self.tela, p.cor, [(cx + lado * 40, cy - 30), (cx + lado * 85, cy - 55), (cx + lado * 50, cy)]
                )
        else:  # espada
            punho = (cx + 52, cy + 15)
            pygame.draw.line(self.tela, cfg.BRANCO, punho, (cx + 82, cy - 60), 6)
            pygame.draw.line(self.tela, cfg.DOURADO, (cx + 38, cy + 5), (cx + 66, cy + 20), 6)

        corpo = pygame.Rect(0, 0, 110, 110)
        corpo.center = (cx, cy)
        pygame.draw.ellipse(self.tela, p.cor, corpo)
        pygame.draw.ellipse(self.tela, misturar(p.cor, cfg.PRETO, 0.4), corpo, 3)

        for lado in (-1, 1):  # olhos olhando para o oponente
            olho = (cx + lado * 20 + olhando_para * 8, cy - 14)
            pygame.draw.circle(self.tela, cfg.BRANCO, olho, 12)
            pygame.draw.circle(self.tela, cfg.PRETO, (olho[0] + olhando_para * 4, olho[1]), 5)

        if p.defendendo:  # escudo
            pygame.draw.circle(self.tela, cfg.AZUL_CLARO, (cx, cy), 78, 4)

    def desenhar_numeros(self) -> None:
        agora = pygame.time.get_ticks()
        for n in self.numeros:
            t = (agora - n["inicio"]) / 1000
            x, y = n["pos"]
            alfa = max(0, int(255 * (1 - t)))
            self.escrever(n["texto"], self.fonte_numero, n["cor"], alfa=alfa, center=(x, y - 75 - int(40 * t)))

    def desenhar_status(self, p: Personagem, canto: tuple[int, int], mostrar_mp: bool) -> None:
        x, y = canto
        painel = pygame.Rect(x, y, 330, 100 if mostrar_mp else 74)
        pygame.draw.rect(self.tela, cfg.PAINEL, painel, border_radius=12)
        pygame.draw.rect(self.tela, cfg.BORDA, painel, 3, border_radius=12)

        self.escrever(p.nome, self.fonte, cfg.BRANCO, topleft=(x + 16, y + 12))
        self.escrever(f"HP {p.hp}/{p.hp_max}", self.fonte_pequena, cfg.BRANCO, topright=(x + 314, y + 16))
        fracao_hp = self.barras[p]["hp"] / p.hp_max
        cor_hp = cfg.VERDE if fracao_hp > 0.5 else cfg.AMARELO if fracao_hp > 0.25 else cfg.VERMELHO
        desenhar_barra(self.tela, pygame.Rect(x + 16, y + 44, 298, 14), fracao_hp, cor_hp)

        if mostrar_mp:
            self.escrever(f"MP {p.mp}/{p.mp_max}", self.fonte_pequena, cfg.AZUL_CLARO, topleft=(x + 16, y + 68))
            desenhar_barra(self.tela, pygame.Rect(x + 110, y + 70, 204, 10), self.barras[p]["mp"] / p.mp_max, cfg.AZUL)

    def desenhar_menu(self) -> None:
        pygame.draw.rect(self.tela, cfg.PAINEL, AREA_MENU, border_radius=12)
        pygame.draw.rect(self.tela, cfg.BORDA, AREA_MENU, 3, border_radius=12)
        minha_vez = self.estado is Estado.ESCOLHENDO

        for i, (acao, botao) in enumerate(zip(OPCOES, self.botoes_menu)):
            disponivel = self.batalha.pode_usar(self.heroi, acao)
            selecionado = minha_vez and i == self.opcao
            if selecionado:
                pygame.draw.rect(self.tela, cfg.CINZA_ESCURO, botao, border_radius=8)
                seta_x, meio = botao.x + 10, botao.centery
                pygame.draw.polygon(self.tela, cfg.DOURADO, [(seta_x, meio - 7), (seta_x, meio + 7), (seta_x + 10, meio)])
            cor = cfg.BRANCO if (disponivel and minha_vez) else cfg.CINZA
            self.escrever(f"{i + 1}. {acao.value}", self.fonte_media, cor, midleft=(botao.x + 30, botao.centery))
            if acao in CUSTO_MP:
                cor_mp = cfg.AZUL_CLARO if disponivel else cfg.CINZA
                self.escrever(f"{CUSTO_MP[acao]} MP", self.fonte_pequena, cor_mp, midright=(botao.right - 12, botao.centery))

        if not minha_vez and self.estado is Estado.VEZ_DO_INIMIGO:
            self.escrever("Vez do inimigo...", self.fonte_pequena, cfg.AMARELO, midbottom=(AREA_MENU.centerx, AREA_MENU.bottom - 6))

    def desenhar_log(self) -> None:
        pygame.draw.rect(self.tela, cfg.PAINEL, AREA_LOG, border_radius=12)
        pygame.draw.rect(self.tela, cfg.BORDA, AREA_LOG, 3, border_radius=12)
        ultimas = self.batalha.log[-5:]
        for i, mensagem in enumerate(ultimas):
            mais_recente = i == len(ultimas) - 1
            cor = cfg.BRANCO if mais_recente else misturar(cfg.BRANCO, cfg.PAINEL, 0.45)
            self.escrever(mensagem, self.fonte_media, cor, topleft=(AREA_LOG.x + 18, AREA_LOG.y + 16 + i * 28))

    def desenhar_fim(self) -> None:
        veu = pygame.Surface((cfg.LARGURA, cfg.ALTURA), pygame.SRCALPHA)
        veu.fill((0, 0, 0, 175))
        self.tela.blit(veu, (0, 0))

        venceu = self.batalha.vencedor is self.heroi
        titulo, cor = ("VITÓRIA!", cfg.DOURADO) if venceu else ("DERROTA...", cfg.VERMELHO)
        meio_x, meio_y = cfg.LARGURA // 2, cfg.ALTURA // 2
        self.escrever(titulo, self.fonte_titulo, cor, center=(meio_x, meio_y - 40))
        self.escrever(f"Batalha decidida no turno {self.batalha.turno}", self.fonte, cfg.BRANCO, center=(meio_x, meio_y + 25))
        self.escrever("R para jogar de novo  ·  Esc para sair", self.fonte_media, cfg.CINZA, center=(meio_x, meio_y + 70))

    def escrever(self, texto: str, fonte: pygame.font.Font, cor, alfa: int = 255, **posicao) -> None:
        """Escreve um texto com sombra. Ex.: escrever("Oi", fonte, cor, center=(100, 50))."""
        superficie = fonte.render(texto, True, cor)
        sombra = fonte.render(texto, True, cfg.PRETO)
        if alfa < 255:
            superficie.set_alpha(alfa)
            sombra.set_alpha(alfa)
        retangulo = superficie.get_rect(**posicao)
        self.tela.blit(sombra, retangulo.move(2, 2))
        self.tela.blit(superficie, retangulo)


def desenhar_barra(tela: pygame.Surface, area: pygame.Rect, fracao: float, cor) -> None:
    fracao = max(0.0, min(1.0, fracao))
    pygame.draw.rect(tela, cfg.CINZA_ESCURO, area, border_radius=area.h // 2)
    if fracao > 0:
        cheio = area.copy()
        cheio.w = max(area.h, round(area.w * fracao))
        pygame.draw.rect(tela, cor, cheio, border_radius=area.h // 2)


def misturar(cor_a, cor_b, t: float) -> tuple[int, int, int]:
    """Mistura duas cores: t=0 dá cor_a, t=1 dá cor_b."""
    return tuple(round(a + (b - a) * t) for a, b in zip(cor_a, cor_b))
