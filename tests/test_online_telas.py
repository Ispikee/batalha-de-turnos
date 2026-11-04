"""Dois jogos inteiros (host e amigo) no mesmo processo, conversando por 127.0.0.1:
criar/entrar, escolher time, lutar, revanche e sair. Sem abrir janela."""
import os
import random
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from jogo.ia import DIFICULDADES, IA  # noqa: E402
from jogo.interface import Jogo  # noqa: E402
from jogo.tela_batalha import TelaBatalha  # noqa: E402
from jogo.tela_online import TelaCriarPartida, TelaEntrarPartida  # noqa: E402
from jogo.tela_selecao import TelaSelecao  # noqa: E402
from jogo.tela_titulo import TelaTitulo  # noqa: E402

DT = 1 / 60


def tecla(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, unicode="", mod=0)


def quadro(*jogos):
    for j in jogos:
        j.processar_rede()
        j.atual.atualizar(DT)
        j.atual.desenhar(j.tela)
    time.sleep(0.001)  # dá tempo para a rede entregar


def rodar_ate(condicao, *jogos, limite=600):
    for _ in range(limite):
        if condicao():
            return True
        quadro(*jogos)
    return condicao()


def escolher_time(jogo, teclas):
    for k in teclas:
        jogo.tratar(jogo.atual.evento(tecla(k)))
    jogo.tratar(jogo.atual.evento(tecla(pygame.K_RETURN)))  # PRONTO!


def test_partida_online_do_comeco_ao_fim():
    host, amigo = Jogo(), Jogo()
    host.porta = 0  # porta livre qualquer
    try:
        host.tratar(host.atual.evento(tecla(pygame.K_DOWN)))
        host.tratar(host.atual.evento(tecla(pygame.K_RETURN)))  # "Criar partida online"
        assert isinstance(host.atual, TelaCriarPartida)
        porta = host.atual.servidor.porta

        amigo.tratar("entrar_online")
        assert isinstance(amigo.atual, TelaEntrarPartida)
        amigo.atual.texto = f"127.0.0.1:{porta}"
        amigo.tratar(amigo.atual.evento(tecla(pygame.K_RETURN)))
        assert rodar_ate(lambda: isinstance(host.atual, TelaSelecao) and isinstance(amigo.atual, TelaSelecao),
                         host, amigo)
        assert host.atual.online and amigo.atual.online

        escolher_time(host, (pygame.K_1, pygame.K_4, pygame.K_5))
        quadro(host, amigo)
        assert host.atual.aguardando and not isinstance(host.atual, TelaBatalha)
        assert rodar_ate(lambda: amigo.sessao.amigo_pronto, host, amigo)  # o amigo vê que o host está pronto
        escolher_time(amigo, (pygame.K_2, pygame.K_3, pygame.K_6))
        assert rodar_ate(lambda: isinstance(host.atual, TelaBatalha) and isinstance(amigo.atual, TelaBatalha),
                         host, amigo)

        batalha_host, batalha_amigo = host.atual, amigo.atual
        assert [l.nome for l in batalha_host.combate.times[1].lutadores] == ["Mizuha", "Fuuga", "Tetsu"]
        assert [l.nome for l in batalha_amigo.combate.times[0].lutadores] == ["Mizuha", "Fuuga", "Tetsu"]

        # IAs jogam no lugar das pessoas, cada uma olhando só a própria tela
        batalha_host.comando_jogador = IA(batalha_host.combate, 0, DIFICULDADES[2], random.Random(1)).comando
        batalha_amigo.comando_jogador = IA(batalha_amigo.combate, 0, DIFICULDADES[2], random.Random(2)).comando
        rodar_ate(lambda: batalha_host.contagem <= 0, host, amigo)
        for l in batalha_host.combate.times[0].lutadores + batalha_host.combate.times[1].lutadores:
            l.hp = 30  # luta curta
        assert rodar_ate(lambda: batalha_host.fim_visivel and batalha_amigo.fim_visivel, host, amigo, limite=60 * 120)

        # os dois veem o mesmo resultado, cada um do seu ponto de vista
        vencedor = batalha_host.combate.vencedor
        assert batalha_amigo.combate.vencedor == (None if vencedor is None else 1 - vencedor)
        hp_host = [l.hp for l in batalha_host.combate.times[1].lutadores]
        hp_amigo = [l.hp for l in batalha_amigo.combate.times[0].lutadores]
        assert hp_host == hp_amigo

        # revanche: só começa quando os dois pedem
        host.tratar(batalha_host.evento(tecla(pygame.K_r)))
        rodar_ate(lambda: amigo.sessao.amigo_quer_revanche, host, amigo)
        assert host.atual is batalha_host
        amigo.tratar(batalha_amigo.evento(tecla(pygame.K_r)))
        assert rodar_ate(lambda: host.atual is not batalha_host and amigo.atual is not batalha_amigo, host, amigo)
        assert isinstance(host.atual, TelaBatalha) and isinstance(amigo.atual, TelaBatalha)
        rodar_ate(lambda: False, host, amigo, limite=240)  # um pouco da nova luta

        # o amigo sai: o host volta ao menu com aviso
        amigo.atual.evento(tecla(pygame.K_ESCAPE))
        amigo.tratar(amigo.atual.evento(tecla(pygame.K_ESCAPE)))
        assert isinstance(amigo.atual, TelaTitulo) and amigo.sessao is None
        assert rodar_ate(lambda: isinstance(host.atual, TelaTitulo), host, amigo)
        assert host.sessao is None and "saiu" in host.atual.aviso
    finally:
        host.encerrar_online(avisar=False)
        amigo.encerrar_online(avisar=False)
        pygame.quit()


def test_conectar_sem_ninguem_mostra_erro():
    jogo = Jogo()
    try:
        jogo.tratar("entrar_online")
        jogo.atual.texto = "127.0.0.1:1"  # ninguém escutando aqui
        jogo.tratar(jogo.atual.evento(tecla(pygame.K_RETURN)))
        assert jogo.atual.status  # "Conectando..."
        limite = time.time() + 10  # no Windows a recusa demora uns 2 s para chegar
        while jogo.atual.erro is None and time.time() < limite:
            quadro(jogo)
        assert jogo.atual.erro is not None
        assert jogo.sessao is None and jogo.atual.status is None
    finally:
        pygame.quit()
