"""Janela do jogo e troca entre as telas (título → escolha de time → batalha).

Também cuida da partida online: lê as mensagens do amigo a cada quadro e
leva cada uma para a tela certa.
"""
from __future__ import annotations

import random

import pygame

from jogo import config as cfg
from jogo.desenho import limpar_cache
from jogo.ia import DIFICULDADES
from jogo.ninjas import ROSTER, ninja
from jogo.online import SessaoOnline
from jogo.rede import PORTA, VERSAO_REDE, Conectando, Servidor
from jogo.tela_batalha import TelaBatalha
from jogo.tela_online import TelaCriarPartida, TelaEntrarPartida
from jogo.tela_selecao import TelaSelecao
from jogo.tela_titulo import TelaTitulo


class Jogo:
    def __init__(self) -> None:
        pygame.init()
        limpar_cache()
        pygame.display.set_caption(cfg.TITULO)
        self.tela = pygame.display.set_mode((cfg.LARGURA, cfg.ALTURA))
        self.relogio = pygame.time.Clock()
        self.rodando = True
        self.escolhidos: list[int] = []
        self.dificuldade = 1
        self.batalha_atual: TelaBatalha | None = None
        # online
        self.porta = PORTA
        self.servidor: Servidor | None = None
        self.conectando: Conectando | None = None
        self.sessao: SessaoOnline | None = None
        self.ultimo_ip = ""
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
            self.processar_rede()
            self.atual.atualizar(dt)
            self.atual.desenhar(self.tela)
            pygame.display.flip()
        self.encerrar_online(avisar=True)
        pygame.quit()

    # ---- Ações das telas ----------------------------------------------------------
    def tratar(self, acao: str | None) -> None:
        if acao is None:
            return
        if acao == "sair":
            self.rodando = False
        elif acao == "titulo":
            self.mudar_para(TelaTitulo())
        elif acao == "selecao":
            self.mudar_para(TelaSelecao(self.escolhidos, self.dificuldade))
        elif acao == "lutar":
            selecao = self.atual
            self.escolhidos = list(selecao.escolhidos)
            if self.sessao is not None:
                self.sessao.marcar_pronto([b.nome for b in selecao.time()])
            else:
                self.dificuldade = selecao.dificuldade
                self.iniciar_batalha(selecao.time(), random.sample(ROSTER, cfg.TAMANHO_TIME))
        elif acao == "menu":
            if self.sessao is not None:
                self.sessao.conexao.enviar({"t": "selecao"})
                self.ir_para_selecao_online()
            else:
                self.mudar_para(TelaSelecao(self.escolhidos, self.dificuldade))
        elif acao == "revanche":
            if self.sessao is not None:
                self.sessao.pedir_revanche()
            elif self.batalha_atual is not None:
                self.iniciar_batalha(self.batalha_atual.time_jogador, self.batalha_atual.time_inimigo)
        # online
        elif acao == "criar_online":
            try:
                self.servidor = Servidor(self.porta)
            except OSError as erro:
                self.mudar_para(TelaTitulo(f"Não deu para abrir a porta {self.porta}: {erro.strerror or erro}"))
                return
            self.mudar_para(TelaCriarPartida(self.servidor))
        elif acao == "entrar_online":
            self.mudar_para(TelaEntrarPartida(self.ultimo_ip))
        elif acao == "conectar":
            self.ultimo_ip = self.atual.texto.strip()
            self.atual.status = "Conectando"
            self.conectando = Conectando(self.ultimo_ip)
        elif acao == "cancelar_pronto" and self.sessao is not None:
            self.sessao.desmarcar_pronto()
        elif acao in ("cancelar", "sair_online"):
            self.encerrar_online(avisar=True)
            self.mudar_para(TelaTitulo())

    def iniciar_batalha(self, time_jogador, time_inimigo) -> None:
        self.batalha_atual = TelaBatalha(time_jogador, time_inimigo, DIFICULDADES[self.dificuldade])
        self.mudar_para(self.batalha_atual)

    # ---- Online --------------------------------------------------------------------
    def processar_rede(self) -> None:
        if self.servidor is not None and self.servidor.conexao is not None:
            self.comecar_sessao(self.servidor.conexao, host=True)
            self.servidor = None
        if self.conectando is not None and self.conectando.terminou:
            if self.conectando.conexao is not None:
                self.comecar_sessao(self.conectando.conexao, host=False)
            elif isinstance(self.atual, TelaEntrarPartida):
                self.atual.status, self.atual.erro = None, self.conectando.erro
            self.conectando = None

        sessao = self.sessao
        if sessao is None:
            return
        for msg in sessao.conexao.receber_tudo():
            tipo = msg.get("t")
            if tipo == "ola" and msg.get("versao") != VERSAO_REDE:
                self.perder_conexao("Vocês estão com versões diferentes do jogo. Atualizem os dois.")
                return
            if tipo == "pronto":
                sessao.amigo_pronto, sessao.time_amigo = True, msg["ninjas"]
            elif tipo == "nao_pronto":
                sessao.amigo_pronto = False
            elif tipo == "inicio" and not sessao.host:
                self.iniciar_batalha_online(msg["cliente"], msg["host"], msg["semente"])
            elif tipo == "cmd" and sessao.host and sessao.controle is not None:
                sessao.controle.receber(msg)
            elif tipo == "estado" and not sessao.host and isinstance(self.atual, TelaBatalha):
                sessao.estados.append(msg)
            elif tipo == "revanche":
                sessao.amigo_quer_revanche = True
            elif tipo == "selecao":
                self.ir_para_selecao_online()
            elif tipo == "tchau":
                self.perder_conexao("Seu amigo saiu da partida.")
                return
        if sessao.conexao.fechada:
            self.perder_conexao("A conexão com seu amigo caiu.")
            return

        if sessao.host:  # quem criou a partida decide quando a luta começa
            na_selecao = isinstance(self.atual, TelaSelecao) and sessao.pronto and sessao.amigo_pronto
            revanche = isinstance(self.atual, TelaBatalha) and sessao.quero_revanche and sessao.amigo_quer_revanche
            if na_selecao or revanche:
                semente = random.randrange(1 << 30)
                sessao.conexao.enviar({"t": "inicio", "host": sessao.meu_time, "cliente": sessao.time_amigo,
                                       "semente": semente})
                self.iniciar_batalha_online(sessao.meu_time, sessao.time_amigo, semente)

    def comecar_sessao(self, conexao, host: bool) -> None:
        self.sessao = SessaoOnline(conexao, host)
        self.ir_para_selecao_online()

    def ir_para_selecao_online(self) -> None:
        self.sessao.nova_luta()
        self.mudar_para(TelaSelecao(self.escolhidos, sessao=self.sessao))

    def iniciar_batalha_online(self, meu_time: list[str], time_amigo: list[str], semente: int) -> None:
        self.sessao.meu_time, self.sessao.time_amigo = list(meu_time), list(time_amigo)
        self.sessao.nova_luta()
        self.batalha_atual = TelaBatalha([ninja(n) for n in meu_time], [ninja(n) for n in time_amigo],
                                         semente=semente, sessao=self.sessao)
        self.mudar_para(self.batalha_atual)

    def perder_conexao(self, aviso: str) -> None:
        self.encerrar_online(avisar=False)
        self.mudar_para(TelaTitulo(aviso))

    def encerrar_online(self, avisar: bool) -> None:
        if self.servidor is not None:
            self.servidor.fechar()
            self.servidor = None
        self.conectando = None
        if self.sessao is not None:
            conexao = self.sessao.conexao
            self.sessao = None
            if avisar:
                conexao.enviar({"t": "tchau"})
                pygame.time.wait(50)  # dá um instante para o "tchau" sair antes de fechar
            conexao.fechar()
