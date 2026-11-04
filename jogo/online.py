"""Partida online: o que os dois PCs mandam um para o outro.

Quem cria a partida (host) roda as regras de verdade (combate.py). O outro PC
(cliente) só manda os comandos dele e desenha o estado que o host manda.

Para os dois jogadores se verem do lado esquerdo da tela, o cliente vê a
arena "girada" 180°: o lado 0 dele é o lado 1 do host, e toda posição é
espelhada pelo centro da arena (que é simétrica).
"""
from __future__ import annotations

from pygame.math import Vector2

from jogo.combate import AreaAtaque, Combate, Comando, Evento, Investida, Projetil
from jogo.jutsus import Efeito
from jogo.naturezas import Natureza
from jogo.rede import VERSAO_REDE, Conexao

TEMPO_GUARDAR_ACAO = 0.3  # se o jutsu chegar meio cedo, o host tenta de novo por esse tempo


def _v(v: Vector2, casas: int = 1) -> list[float]:
    return [round(v.x, casas), round(v.y, casas)]


# ---- Estado do jogo (host -> cliente) ---------------------------------------------
def exportar_estado(combate: Combate) -> dict:
    """Tudo que o cliente precisa para desenhar a luta, mais os eventos deste quadro."""
    def lutador(l):
        return {
            "hp": round(l.hp, 2), "p": _v(l.pos), "v": _v(l.vel), "m": _v(l.mira, 3),
            "r": [round(r, 2) for r in l.recargas], "s": {e.name: round(t, 2) for e, t in l.status.items()},
            "e": round(l.esquiva, 3), "re": round(l.recarga_esquiva, 2),
            "i": l.base.jutsus.index(l.investida.jutsu) if l.investida else -1,
            "tr": round(l.trava, 2), "inv": round(l.invulneravel, 2), "f": round(l.flash, 2),
        }

    def time(t):
        return {"a": t.ativo_idx, "rt": round(t.recarga_troca, 2), "ko": round(t.espera_nocaute, 2),
                "tp": t.troca_pendente, "tt": round(t.tempo_troca, 2), "l": [lutador(l) for l in t.lutadores]}

    def origem(atacante):
        equipe = combate.times[atacante.lado].lutadores
        return atacante.lado, equipe.index(atacante)

    projeteis = []
    for p in combate.projeteis:
        lado, n = origem(p.atacante)
        projeteis.append({"l": lado, "n": n, "j": p.atacante.base.jutsus.index(p.jutsu),
                          "p": _v(p.pos), "v": _v(p.vel), "r": round(p.restante, 1), "id": p.ident})
    areas = []
    for a in combate.areas:
        lado, n = origem(a.atacante)
        areas.append({"l": lado, "n": n, "j": a.atacante.base.jutsus.index(a.jutsu),
                      "p": _v(a.pos), "r": round(a.restante, 3), "id": a.ident})
    eventos = [{
        "t": e.tipo, "p": _v(e.pos), "val": e.valor, "tx": e.texto,
        "n": e.natureza.name if e.natureza else None, "ef": e.eficacia, "c": e.critico,
        "a": round(e.angulo, 1), "ra": e.raio, "l": e.lado,
    } for e in combate.eventos]
    return {
        "t": "estado", "tempo": round(combate.tempo, 3), "fim": combate.terminou, "venc": combate.vencedor,
        "times": [time(t) for t in combate.times], "proj": projeteis, "areas": areas, "ev": eventos,
    }


def aplicar_estado(combate: Combate, d: dict, espelhar: bool = True) -> None:
    """Copia o estado do host para o combate do cliente (girado 180°) e junta os eventos."""
    centro = Vector2(combate.arena.retangulo.center)

    def ponto(xy):
        return centro * 2 - Vector2(xy) if espelhar else Vector2(xy)

    def vetor(xy):
        return -Vector2(xy) if espelhar else Vector2(xy)

    def lado(n):
        return 1 - n if espelhar and n in (0, 1) else n

    combate.tempo = d["tempo"]
    combate.terminou = d["fim"]
    combate.vencedor = lado(d["venc"]) if d["venc"] is not None else None
    for lado_host, dt in enumerate(d["times"]):
        time = combate.times[lado(lado_host)]
        time.ativo_idx, time.recarga_troca, time.espera_nocaute = dt["a"], dt["rt"], dt["ko"]
        time.troca_pendente, time.tempo_troca = dt["tp"], dt["tt"]
        for l, dl in zip(time.lutadores, dt["l"]):
            l.hp = dl["hp"]
            l.pos, l.vel, l.mira = ponto(dl["p"]), vetor(dl["v"]), vetor(dl["m"])
            l.recargas = list(dl["r"])
            l.status = {Efeito[nome]: t for nome, t in dl["s"].items()}
            l.esquiva, l.recarga_esquiva = dl["e"], dl["re"]
            l.investida = Investida(l.base.jutsus[dl["i"]], l.mira.copy(), 0.1) if dl["i"] >= 0 else None
            l.trava, l.invulneravel, l.flash = dl["tr"], dl["inv"], dl["f"]

    def atacante(item):
        return combate.times[lado(item["l"])].lutadores[item["n"]]

    combate.projeteis = []
    for p in d["proj"]:
        quem = atacante(p)
        combate.projeteis.append(Projetil(quem.base.jutsus[p["j"]], quem, ponto(p["p"]), vetor(p["v"]),
                                          p["r"], ident=p["id"]))
    combate.areas = []
    for a in d["areas"]:
        quem = atacante(a)
        combate.areas.append(AreaAtaque(quem.base.jutsus[a["j"]], quem, ponto(a["p"]), a["r"], ident=a["id"]))
    for e in d["ev"]:
        combate.eventos.append(Evento(
            e["t"], ponto(e["p"]), valor=e["val"], texto=e["tx"],
            natureza=Natureza[e["n"]] if e["n"] else None, eficacia=e["ef"], critico=e["c"],
            angulo=(e["a"] + 180) % 360 if espelhar else e["a"], raio=e["ra"], lado=lado(e["l"]),
        ))


# ---- Comandos (cliente -> host) ------------------------------------------------------
def exportar_comando(c: Comando) -> dict:
    return {"t": "cmd", "mv": _v(c.mover, 3), "mi": _v(c.mira) if c.mira is not None else None,
            "j": c.jutsu, "e": c.esquiva, "tr": c.trocar}


class ControleRemoto:
    """No host: transforma os comandos que chegam do amigo em Comandos para o lado 1.

    Ações de um toque (jutsu, esquiva, troca) ficam guardadas um tempinho: se
    chegarem um quadro antes da recarga acabar no host, ainda acontecem.
    """

    def __init__(self, combate: Combate, lado: int = 1):
        self.combate = combate
        self.lado = lado
        self.mover = Vector2()
        self.mira: Vector2 | None = None
        self.jutsu: int | None = None
        self.esquiva = 0.0
        self.trocar: int | None = None
        self.espera_jutsu = 0.0
        self.espera_troca = 0.0

    def receber(self, msg: dict) -> None:
        centro = Vector2(self.combate.arena.retangulo.center)
        self.mover = -Vector2(msg["mv"])
        self.mira = centro * 2 - Vector2(msg["mi"]) if msg.get("mi") is not None else None
        if msg.get("j") is not None:
            self.jutsu, self.espera_jutsu = msg["j"], TEMPO_GUARDAR_ACAO
        if msg.get("e"):
            self.esquiva = TEMPO_GUARDAR_ACAO
        if msg.get("tr") is not None:
            self.trocar, self.espera_troca = msg["tr"], TEMPO_GUARDAR_ACAO

    def comando(self, dt: float) -> Comando:
        time = self.combate.times[self.lado]
        eu = time.ativo
        c = Comando(mover=Vector2(self.mover), mira=self.mira)
        if self.jutsu is not None:
            if self.combate.pode_usar(eu, self.jutsu):
                c.jutsu, self.jutsu = self.jutsu, None
            else:
                self.espera_jutsu -= dt
                if self.espera_jutsu <= 0:
                    self.jutsu = None
        if self.esquiva > 0:
            if self.combate.pode_esquivar(eu):
                c.esquiva, self.esquiva = True, 0.0
            else:
                self.esquiva -= dt
        if self.trocar is not None:
            if self.combate.pode_trocar(time, self.trocar):
                c.trocar, self.trocar = self.trocar, None
            else:
                self.espera_troca -= dt
                if self.espera_troca <= 0:
                    self.trocar = None
        return c


# ---- Sessão ------------------------------------------------------------------------------
class SessaoOnline:
    """Tudo sobre a partida online atual: conexão, quem está pronto, revanche..."""

    def __init__(self, conexao: Conexao, host: bool):
        self.conexao = conexao
        self.host = host
        self.meu_time: list[str] | None = None
        self.time_amigo: list[str] | None = None
        self.pronto = False
        self.amigo_pronto = False
        self.quero_revanche = False
        self.amigo_quer_revanche = False
        self.estados: list[dict] = []  # cliente: estados que chegaram e ainda não foram desenhados
        self.controle: ControleRemoto | None = None  # host: comandos do amigo
        conexao.enviar({"t": "ola", "versao": VERSAO_REDE})

    def marcar_pronto(self, nomes: list[str]) -> None:
        self.pronto, self.meu_time = True, list(nomes)
        self.conexao.enviar({"t": "pronto", "ninjas": self.meu_time})

    def desmarcar_pronto(self) -> None:
        self.pronto = False
        self.conexao.enviar({"t": "nao_pronto"})

    def pedir_revanche(self) -> None:
        self.quero_revanche = True
        self.conexao.enviar({"t": "revanche"})

    def nova_luta(self) -> None:
        self.pronto = self.amigo_pronto = False
        self.quero_revanche = self.amigo_quer_revanche = False
        self.estados.clear()

    def enviar_estado(self, combate: Combate) -> None:
        self.conexao.enviar(exportar_estado(combate))

    def enviar_comando(self, c: Comando) -> None:
        self.conexao.enviar(exportar_comando(c))
