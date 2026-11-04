"""Telas para começar uma partida online: criar (e esperar o amigo) ou entrar pelo IP."""
from __future__ import annotations

import pygame

from jogo import config as cfg
from jogo.desenho import escrever, gradiente, painel
from jogo.rede import Servidor, meus_ips

CARACTERES_IP = set("0123456789.:abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-")


def _fundo() -> pygame.Surface:
    return gradiente(cfg.LARGURA, cfg.ALTURA, (18, 20, 34), (30, 40, 62))


class TelaCriarPartida:
    def __init__(self, servidor: Servidor):
        self.servidor = servidor
        self.ips = meus_ips()
        self.tempo = 0.0
        self.fundo = _fundo()

    def evento(self, e) -> str | None:
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            return "cancelar"
        return None

    def atualizar(self, dt: float) -> None:
        self.tempo += dt

    def desenhar(self, tela: pygame.Surface) -> None:
        tela.blit(self.fundo, (0, 0))
        meio = cfg.LARGURA / 2
        escrever(tela, "Criar partida online", 44, cfg.BRANCO, negrito=True, center=(meio, 70))

        caixa = pygame.Rect(0, 0, 760, 300)
        caixa.midtop = (meio, 130)
        painel(tela, caixa)
        escrever(tela, "Passe um destes IPs para seu amigo:", 22, cfg.CINZA_CLARO, center=(meio, caixa.y + 34))
        if not self.ips:
            escrever(tela, "Não achei nenhum IP de rede neste PC.", 24, cfg.VERMELHO, center=(meio, caixa.y + 110))
        for k, (ip, descricao) in enumerate(self.ips[:5]):
            y = caixa.y + 80 + k * 44
            principal = k == 0
            escrever(tela, ip, 34 if principal else 28, cfg.DOURADO if principal else cfg.BRANCO, negrito=True,
                     midright=(meio + 20, y))
            escrever(tela, descricao, 18, cfg.CINZA_CLARO, midleft=(meio + 40, y))
        escrever(tela, f"Porta: {self.servidor.porta}", 18, cfg.CINZA, center=(meio, caixa.bottom - 22))

        pontos = "." * (int(self.tempo * 2) % 4)
        escrever(tela, f"Esperando seu amigo entrar{pontos}", 30, cfg.BRANCO, negrito=True, center=(meio, 480))
        escrever(tela, "Se o Windows perguntar, clique em \"Permitir acesso\" (marque as redes privadas e públicas).",
                 17, cfg.AMARELO, center=(meio, 540))
        escrever(tela, "Pela internet: os dois entram na mesma rede do Radmin VPN e usam o IP que começa com 26.",
                 17, cfg.CINZA_CLARO, center=(meio, 570))
        escrever(tela, "Esc: voltar", 18, cfg.CINZA, center=(meio, cfg.ALTURA - 40))


class TelaEntrarPartida:
    def __init__(self, texto: str = ""):
        self.texto = texto
        self.status: str | None = None  # "Conectando..."
        self.erro: str | None = None
        self.tempo = 0.0
        self.fundo = _fundo()
        self.caixa = pygame.Rect(0, 0, 520, 64)
        self.caixa.center = (cfg.LARGURA // 2, 300)

    def evento(self, e) -> str | None:
        if e.type != pygame.KEYDOWN:
            return None
        if e.key == pygame.K_ESCAPE:
            return "cancelar"
        if self.status:  # já está conectando
            return None
        if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.texto.strip():
                self.erro = None
                return "conectar"
        elif e.key == pygame.K_BACKSPACE:
            self.texto = self.texto[:-1]
        elif e.key == pygame.K_v and e.mod & pygame.KMOD_CTRL:
            self.colar()
        elif e.unicode and e.unicode in CARACTERES_IP and len(self.texto) < 40:
            self.texto += e.unicode
        return None

    def colar(self) -> None:
        try:
            colado = pygame.scrap.get_text() or ""
        except (pygame.error, AttributeError, NotImplementedError):
            return
        self.texto = "".join(c for c in colado.strip() if c in CARACTERES_IP)[:40]

    def atualizar(self, dt: float) -> None:
        self.tempo += dt

    def desenhar(self, tela: pygame.Surface) -> None:
        tela.blit(self.fundo, (0, 0))
        meio = cfg.LARGURA / 2
        escrever(tela, "Entrar em partida online", 44, cfg.BRANCO, negrito=True, center=(meio, 90))
        escrever(tela, "Digite o IP que seu amigo passou (ele precisa estar na tela \"Criar partida\"):", 20,
                 cfg.CINZA_CLARO, center=(meio, 220))

        painel(tela, self.caixa, cor=cfg.PAINEL_CLARO, borda=cfg.DOURADO, largura_borda=3)
        cursor = "|" if int(self.tempo * 2) % 2 == 0 and not self.status else ""
        r = escrever(tela, self.texto + cursor, 34, cfg.BRANCO, negrito=True, midleft=(self.caixa.x + 20, self.caixa.centery))
        if not self.texto:
            escrever(tela, "ex.: 26.123.45.67", 26, cfg.CINZA, sombra=False, midleft=(r.right + 6, self.caixa.centery))

        if self.status:
            pontos = "." * (int(self.tempo * 2) % 4)
            escrever(tela, f"{self.status}{pontos}", 26, cfg.AMARELO, negrito=True, center=(meio, 390))
        elif self.erro:
            escrever(tela, self.erro, 20, cfg.VERMELHO, negrito=True, center=(meio, 390))
        else:
            escrever(tela, "Enter: conectar  ·  Ctrl+V: colar", 20, cfg.CINZA_CLARO, center=(meio, 390))
        escrever(tela, "Esc: voltar", 18, cfg.CINZA, center=(meio, cfg.ALTURA - 40))
