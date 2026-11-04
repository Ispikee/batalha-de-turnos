"""Testes do modo online, com os dois "PCs" rodando aqui mesmo (127.0.0.1)."""
import random
import time

import pytest
from pygame.math import Vector2

from jogo.combate import Combate, Comando
from jogo.ia import DIFICULDADES, IA
from jogo.ninjas import ninja
from jogo.online import ControleRemoto, SessaoOnline, aplicar_estado, exportar_estado
from jogo.rede import Conectando, Servidor, separar_endereco

DT = 1 / 60
TIME_HOST = ["Kaen", "Ganro", "Shiden"]
TIME_CLIENTE = ["Mizuha", "Fuuga", "Tetsu"]


def bases(nomes):
    return [ninja(n) for n in nomes]


def esperar(condicao, segundos=5.0):
    limite = time.time() + segundos
    while time.time() < limite:
        if condicao():
            return True
        time.sleep(0.0005)
    return False


@pytest.fixture
def par_conectado():
    servidor = Servidor(porta=0)  # porta 0 = o sistema escolhe uma livre
    cliente = Conectando(f"127.0.0.1:{servidor.porta}")
    assert esperar(lambda: cliente.terminou and servidor.conexao is not None), cliente.erro
    assert cliente.conexao is not None
    yield servidor.conexao, cliente.conexao
    servidor.conexao.fechar()
    cliente.conexao.fechar()


def test_separar_endereco():
    assert separar_endereco("26.1.2.3") == ("26.1.2.3", 5050)
    assert separar_endereco("192.168.0.10:6000") == ("192.168.0.10", 6000)
    with pytest.raises(ValueError):
        separar_endereco("")


def test_mensagens_vao_e_voltam(par_conectado):
    host, cliente = par_conectado
    cliente.enviar({"t": "oi", "n": 1})
    host.enviar({"t": "oi", "n": 2})
    recebidas_host, recebidas_cliente = [], []
    assert esperar(lambda: recebidas_host.extend(host.receber_tudo()) or recebidas_host)
    assert esperar(lambda: recebidas_cliente.extend(cliente.receber_tudo()) or recebidas_cliente)
    assert recebidas_host == [{"t": "oi", "n": 1}]
    assert recebidas_cliente == [{"t": "oi", "n": 2}]


def test_conectar_em_porta_fechada_da_erro_amigavel():
    servidor = Servidor(porta=0)
    porta = servidor.porta
    servidor.fechar()
    tentativa = Conectando(f"127.0.0.1:{porta}", timeout=2)
    assert esperar(lambda: tentativa.terminou)
    assert tentativa.conexao is None and tentativa.erro


def test_cliente_ve_o_estado_girado_180_graus():
    host = Combate(bases(TIME_HOST), bases(TIME_CLIENTE), rng=random.Random(1))
    cliente = Combate(bases(TIME_CLIENTE), bases(TIME_HOST))  # no cliente, o time dele é o lado 0
    host.atualizar(DT, [Comando(mira=Vector2(host.ativo(1).pos), jutsu=0), Comando(mover=Vector2(0, 1))])
    host.ativo(1).hp -= 37
    aplicar_estado(cliente, exportar_estado(host))

    centro = Vector2(host.arena.retangulo.center)
    assert cliente.ativo(0).nome == host.ativo(1).nome
    assert cliente.ativo(0).hp == pytest.approx(host.ativo(1).hp)
    assert cliente.ativo(0).pos.distance_to(centro * 2 - host.ativo(1).pos) < 0.2
    assert cliente.ativo(0).pos.x < centro.x  # o cliente também se vê do lado esquerdo
    assert len(cliente.projeteis) == len(host.projeteis) == 1
    assert cliente.projeteis[0].vel.distance_to(-host.projeteis[0].vel) < 0.2
    assert [e.tipo for e in cliente.eventos] == [e.tipo for e in host.eventos]


def test_controle_remoto_desfaz_o_espelho():
    host = Combate(bases(TIME_HOST), bases(TIME_CLIENTE))
    controle = ControleRemoto(host, lado=1)
    centro = Vector2(host.arena.retangulo.center)
    # no PC do cliente ele anda para a direita e mira no ponto (300, 200)
    controle.receber({"mv": [1, 0], "mi": [300, 200], "j": None, "e": False, "tr": None})
    c = controle.comando(DT)
    assert c.mover == Vector2(-1, 0)
    assert c.mira == centro * 2 - Vector2(300, 200)


def test_luta_inteira_pela_rede(par_conectado):
    conexao_host, conexao_cliente = par_conectado
    sessao_host = SessaoOnline(conexao_host, host=True)
    sessao_cliente = SessaoOnline(conexao_cliente, host=False)

    host = Combate(bases(TIME_HOST), bases(TIME_CLIENTE), rng=random.Random(5))
    cliente = Combate(bases(TIME_CLIENTE), bases(TIME_HOST))
    for l in host.times[0].lutadores + host.times[1].lutadores:
        l.hp = 40  # luta curta
    controle = ControleRemoto(host, lado=1)
    ia_host = IA(host, 0, DIFICULDADES[1], random.Random(1))
    ia_cliente = IA(cliente, 0, DIFICULDADES[1], random.Random(2))  # joga olhando só a tela do cliente

    jutsus_do_cliente = 0
    for _ in range(round(120 / DT)):
        if host.terminou:
            break
        # cliente: decide pelo que vê e manda o comando
        sessao_cliente.enviar_comando(ia_cliente.comando(DT))
        # host: recebe o comando, roda a luta e manda o estado
        assert esperar(lambda: any(m["t"] == "cmd" for m in conexao_host.recebidas.queue))
        for msg in conexao_host.receber_tudo():
            if msg["t"] == "cmd":
                controle.receber(msg)
        host.atualizar(DT, [ia_host.comando(DT), controle.comando(DT)])
        jutsus_do_cliente += sum(1 for e in host.eventos if e.tipo == "jutsu" and e.lado == 1)
        sessao_host.enviar_estado(host)
        host.eventos.clear()
        # cliente: aplica o estado que chegou
        assert esperar(lambda: any(m["t"] == "estado" for m in conexao_cliente.recebidas.queue))
        for msg in conexao_cliente.receber_tudo():
            if msg["t"] == "estado":
                aplicar_estado(cliente, msg)
        cliente.eventos.clear()

    assert host.terminou and cliente.terminou
    assert jutsus_do_cliente > 0  # os comandos do cliente chegaram e viraram jutsus no host
    vencedor_host = host.vencedor
    assert cliente.vencedor == (None if vencedor_host is None else 1 - vencedor_host)
    for lado in (0, 1):
        for a, b in zip(host.times[lado].lutadores, cliente.times[1 - lado].lutadores):
            assert a.nome == b.nome and a.hp == pytest.approx(b.hp)
