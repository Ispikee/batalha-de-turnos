"""Conexão entre dois PCs (TCP), para jogar online contra um amigo.

Um PC "cria a partida" (Servidor) e o outro "entra" pelo IP (Conectando).
Depois disso os dois conversam do mesmo jeito, pela classe Conexao: as
mensagens são dicionários enviados como JSON, uma por linha.
Tudo que espera a rede roda em threads, para o jogo não travar.
"""
from __future__ import annotations

import ipaddress
import json
import queue
import socket
import threading

PORTA = 5050
VERSAO_REDE = 1  # mude quando as mensagens mudarem: versões diferentes não conectam


class Conexao:
    def __init__(self, sock: socket.socket):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # manda na hora, sem juntar pacotes
        sock.settimeout(None)
        self.sock = sock
        self.recebidas: queue.Queue = queue.Queue()
        self.saida: queue.Queue = queue.Queue()
        self.fechada = False
        threading.Thread(target=self._receber, daemon=True).start()
        threading.Thread(target=self._enviar, daemon=True).start()

    def enviar(self, mensagem: dict) -> None:
        if not self.fechada:
            self.saida.put(json.dumps(mensagem, separators=(",", ":")).encode() + b"\n")

    def receber_tudo(self) -> list[dict]:
        mensagens = []
        while True:
            try:
                mensagens.append(self.recebidas.get_nowait())
            except queue.Empty:
                return mensagens

    def fechar(self) -> None:
        self.fechada = True
        self.saida.put(None)
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()

    def _receber(self) -> None:
        buffer = b""
        try:
            while True:
                dados = self.sock.recv(65536)
                if not dados:
                    break
                buffer += dados
                while b"\n" in buffer:
                    linha, buffer = buffer.split(b"\n", 1)
                    if linha:
                        self.recebidas.put(json.loads(linha))
        except (OSError, ValueError):
            pass
        self.fechada = True

    def _enviar(self) -> None:
        try:
            while True:
                dados = self.saida.get()
                if dados is None:
                    break
                partes = [dados]
                while True:  # junta o que já estiver na fila e manda de uma vez
                    try:
                        extra = self.saida.get_nowait()
                    except queue.Empty:
                        break
                    if extra is None:
                        self.sock.sendall(b"".join(partes))
                        return
                    partes.append(extra)
                self.sock.sendall(b"".join(partes))
        except OSError:
            pass
        self.fechada = True


class Servidor:
    """Abre a porta e espera UM amigo conectar."""

    def __init__(self, porta: int = PORTA):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("0.0.0.0", porta))
        self.sock.listen(1)
        self.porta = self.sock.getsockname()[1]
        self.conexao: Conexao | None = None
        threading.Thread(target=self._aceitar, daemon=True).start()

    def _aceitar(self) -> None:
        try:
            sock, _ = self.sock.accept()
            self.conexao = Conexao(sock)
        except OSError:
            pass
        finally:
            self.sock.close()

    def fechar(self) -> None:
        self.sock.close()


class Conectando:
    """Tenta conectar no amigo em segundo plano. Veja `terminou`, `conexao` e `erro`."""

    def __init__(self, endereco: str, timeout: float = 6.0):
        self.conexao: Conexao | None = None
        self.erro: str | None = None
        self.terminou = False
        threading.Thread(target=self._conectar, args=(endereco.strip(), timeout), daemon=True).start()

    def _conectar(self, endereco: str, timeout: float) -> None:
        try:
            host, porta = separar_endereco(endereco)
            sock = socket.create_connection((host, porta), timeout=timeout)
            self.conexao = Conexao(sock)
        except ValueError as e:
            self.erro = str(e)
        except socket.timeout:
            self.erro = "O amigo não respondeu. Confira o IP e se ele já criou a partida."
        except ConnectionRefusedError:
            self.erro = "Conexão recusada: seu amigo já está na tela de \"Criar partida\"?"
        except socket.gaierror:
            self.erro = "Endereço inválido. Digite só o IP, por exemplo 26.12.34.56"
        except OSError as e:
            self.erro = f"Não deu para conectar ({e.strerror or e})."
        self.terminou = True


def separar_endereco(endereco: str) -> tuple[str, int]:
    """'26.1.2.3' -> ('26.1.2.3', 5050); '26.1.2.3:6000' -> ('26.1.2.3', 6000)."""
    if not endereco:
        raise ValueError("Digite o IP do seu amigo.")
    host, _, porta = endereco.partition(":")
    if not porta:
        return host, PORTA
    if not porta.isdigit():
        raise ValueError("A porta (depois do ':') precisa ser um número.")
    return host, int(porta)


def meus_ips() -> list[tuple[str, str]]:
    """IPs deste PC, com uma descrição de onde cada um funciona."""
    ips: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    try:  # o IP "principal" (não manda nada para a internet de verdade)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    resultado = []
    for ip in sorted(ips):
        if ip.startswith("127.") or ip.startswith("169.254."):
            continue
        if ip.startswith("26."):
            descricao = "Radmin VPN (internet)"
        elif ipaddress.ip_address(ip).is_private:
            descricao = "mesma rede / Wi-Fi"
        else:
            descricao = "internet (precisa abrir a porta no roteador)"
        resultado.append((ip, descricao))
    # o do Radmin primeiro, que é o mais usado para jogar pela internet
    return sorted(resultado, key=lambda par: not par[0].startswith("26."))
