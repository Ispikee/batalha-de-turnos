"""Regras da batalha em tempo real.

Nada aqui abre janela: o combate só recebe comandos (para onde andar, para onde
mirar, qual jutsu usar...) e avança o tempo. Por isso dá para testar tudo com
pytest e até colocar duas IAs para lutar sozinhas (veja a pasta tests/).
Do Pygame usamos só o Vector2, que é matemática pura.
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field

from pygame.math import Vector2

from jogo.arena import Arena, criar_arena
from jogo.jutsus import Efeito, Jutsu, Tipo
from jogo.naturezas import Natureza, multiplicador
from jogo.ninjas import NinjaBase

# ---- Regras (ajuste à vontade) ----------------------------------------------
RAIO_LUTADOR = 22
RECARGA_GLOBAL = 0.3  # tempo mínimo entre dois jutsus seguidos
ESQUIVA_DURACAO = 0.16
ESQUIVA_VELOCIDADE = 950
ESQUIVA_RECARGA = 1.1
INVESTIDA_VELOCIDADE = 1100
TROCA_DURACAO = 0.7  # tempo parado chamando o outro ninja (dá para levar golpes!)
TROCA_RECARGA = 4.0
INVULNERAVEL_AO_ENTRAR = 0.6
ESPERA_APOS_NOCAUTE = 1.2
CHANCE_CRITICO = 0.08
MULTIPLICADOR_CRITICO = 1.5
BONUS_MESMA_NATUREZA = 1.2  # jutsu da mesma natureza do ninja bate mais forte
MULTIPLICADOR_FORCA = 1.3
MULTIPLICADOR_ESCUDO = 0.5
MULTIPLICADOR_LENTIDAO = 0.6
MULTIPLICADOR_VELOCIDADE = 1.4
AGUA_LENTO = 0.55
AGUA_RAPIDO = 1.2
QUEIMADURA_POR_SEGUNDO = 0.02  # fração do HP máximo
FORCA_EMPURRAO = 520
ANGULO_CORPO = 75  # golpes corpo a corpo acertam até esse ângulo para cada lado
FATOR_DANO = 0.8  # aumente para lutas mais rápidas
# -----------------------------------------------------------------------------

TEXTO_EFEITO = {
    Efeito.QUEIMADURA: "Queimado!",
    Efeito.LENTIDAO: "Lento!",
    Efeito.ATORDOAR: "Atordoado!",
    Efeito.ESCUDO: "Escudo!",
    Efeito.VELOCIDADE: "Mais rápido!",
    Efeito.FORCA: "Mais forte!",
}

_contador = itertools.count()


@dataclass
class Comando:
    """O que um lado quer fazer neste quadro (vem do teclado/mouse ou da IA)."""

    mover: Vector2 = field(default_factory=Vector2)
    mira: Vector2 | None = None  # ponto da arena para onde mirar
    jutsu: int | None = None
    esquiva: bool = False
    trocar: int | None = None


@dataclass
class Evento:
    """Algo que aconteceu e que a tela pode querer mostrar."""

    tipo: str  # dano, queimadura, cura, texto, jutsu, troca, nocaute, explosao, corte, esquiva, fim
    pos: Vector2
    valor: int = 0
    texto: str = ""
    natureza: Natureza | None = None
    eficacia: float = 1.0
    critico: bool = False
    angulo: float = 0.0
    raio: float = 0.0
    lado: int = 0


@dataclass
class Investida:
    jutsu: Jutsu
    direcao: Vector2
    restante: float


class Lutador:
    def __init__(self, base: NinjaBase, lado: int):
        self.base = base
        self.lado = lado
        self.hp = float(base.hp)
        self.pos = Vector2()
        self.vel = Vector2()  # velocidade real no último quadro (a IA usa para antecipar)
        self.mira = Vector2(1 if lado == 0 else -1, 0)
        self.recargas = [0.0] * len(base.jutsus)
        self.status: dict[Efeito, float] = {}
        self.empurrao = Vector2()
        self.esquiva = 0.0
        self.esquiva_dir = Vector2()
        self.recarga_esquiva = 0.0
        self.investida: Investida | None = None
        self.trava = 0.0
        self.invulneravel = 0.0
        self.flash = 0.0
        self.queimadura_acumulada = 0.0
        self.nocaute_anunciado = False

    @property
    def nome(self) -> str:
        return self.base.nome

    @property
    def natureza(self) -> Natureza:
        return self.base.natureza

    @property
    def hp_max(self) -> int:
        return self.base.hp

    @property
    def raio(self) -> float:
        return RAIO_LUTADOR

    @property
    def vivo(self) -> bool:
        return self.hp > 0

    @property
    def fracao_hp(self) -> float:
        return self.hp / self.hp_max

    @property
    def hp_inteiro(self) -> int:
        return max(0, -int(-self.hp // 1))  # arredonda para cima: 0.3 de HP ainda mostra 1

    def tem(self, efeito: Efeito) -> bool:
        return self.status.get(efeito, 0) > 0

    @property
    def atordoado(self) -> bool:
        return self.tem(Efeito.ATORDOAR)

    @property
    def ocupado(self) -> bool:
        return self.esquiva > 0 or self.investida is not None

    def velocidade_movimento(self, arena: Arena) -> float:
        v = 140 + self.base.velocidade * 1.6
        if self.tem(Efeito.LENTIDAO):
            v *= MULTIPLICADOR_LENTIDAO
        if self.tem(Efeito.VELOCIDADE):
            v *= MULTIPLICADOR_VELOCIDADE
        if arena.na_agua(self.pos):
            v *= AGUA_RAPIDO if self.natureza is Natureza.AGUA else AGUA_LENTO
        return v

    def limpar_efeitos(self) -> None:
        self.status.clear()
        self.empurrao = Vector2()
        self.esquiva = 0.0
        self.investida = None
        self.trava = 0.0
        self.vel = Vector2()


class Time:
    def __init__(self, bases: list[NinjaBase], lado: int):
        if not bases:
            raise ValueError("O time precisa de pelo menos um ninja.")
        self.lado = lado
        self.lutadores = [Lutador(b, lado) for b in bases]
        self.ativo_idx = 0
        self.recarga_troca = 0.0
        self.espera_nocaute = 0.0
        self.escolha_apos_nocaute: int | None = None
        self.troca_pendente: int | None = None  # ninja sendo chamado
        self.tempo_troca = 0.0

    @property
    def trocando(self) -> bool:
        return self.troca_pendente is not None

    @property
    def ativo(self) -> Lutador:
        return self.lutadores[self.ativo_idx]

    @property
    def derrotado(self) -> bool:
        return not any(l.vivo for l in self.lutadores)

    def reservas(self) -> list[int]:
        return [i for i, l in enumerate(self.lutadores) if l.vivo and i != self.ativo_idx]


@dataclass
class Projetil:
    jutsu: Jutsu
    atacante: Lutador
    pos: Vector2
    vel: Vector2
    restante: float  # distância que ainda pode voar
    ident: int = field(default_factory=lambda: next(_contador))
    vivo: bool = True

    @property
    def lado(self) -> int:
        return self.atacante.lado

    @property
    def raio(self) -> float:
        return self.jutsu.raio


@dataclass
class AreaAtaque:
    jutsu: Jutsu
    atacante: Lutador
    pos: Vector2
    restante: float
    ident: int = field(default_factory=lambda: next(_contador))

    @property
    def lado(self) -> int:
        return self.atacante.lado

    @property
    def progresso(self) -> float:
        if self.jutsu.atraso <= 0:
            return 1.0
        return 1 - self.restante / self.jutsu.atraso


class Combate:
    def __init__(
        self,
        time_a: list[NinjaBase],
        time_b: list[NinjaBase],
        arena: Arena | None = None,
        rng: random.Random | None = None,
    ):
        self.arena = arena or criar_arena()
        self.rng = rng or random.Random()
        self.times = [Time(list(time_a), 0), Time(list(time_b), 1)]
        for time in self.times:
            time.ativo.pos = self.arena.inicio(time.lado)
        self.projeteis: list[Projetil] = []
        self.areas: list[AreaAtaque] = []
        self.eventos: list[Evento] = []
        self.tempo = 0.0
        self.terminou = False
        self.vencedor: int | None = None  # 0, 1, ou None (empate / ainda lutando)

    # ---- Consultas -------------------------------------------------------------
    def ativo(self, lado: int) -> Lutador:
        return self.times[lado].ativo

    def oponente(self, lado: int) -> Lutador:
        return self.times[1 - lado].ativo

    def pode_usar(self, lutador: Lutador, indice: int) -> bool:
        if not (0 <= indice < len(lutador.base.jutsus)):
            return False
        if self.terminou or not lutador.vivo or lutador.atordoado or lutador.ocupado:
            return False
        time = self.times[lutador.lado]
        if time.ativo is not lutador or time.espera_nocaute > 0 or time.trocando:
            return False
        if lutador.trava > 0 or lutador.recargas[indice] > 0:
            return False
        jutsu = lutador.base.jutsus[indice]
        if jutsu.efeito is Efeito.CURA and jutsu.tipo is Tipo.SUPORTE and lutador.hp >= lutador.hp_max:
            return False
        return True

    def pode_esquivar(self, lutador: Lutador) -> bool:
        if self.times[lutador.lado].trocando:
            return False
        return lutador.vivo and not lutador.atordoado and not lutador.ocupado and lutador.recarga_esquiva <= 0

    def pode_trocar(self, time: Time, indice: int) -> bool:
        if self.terminou or not (0 <= indice < len(time.lutadores)) or indice == time.ativo_idx:
            return False
        if time.trocando:
            return False
        if not time.lutadores[indice].vivo:
            return False
        if time.espera_nocaute > 0:
            return True
        ativo = time.ativo
        return time.recarga_troca <= 0 and ativo.vivo and not ativo.atordoado and not ativo.ocupado

    def calcular_dano(self, atacante: Lutador, alvo: Lutador, jutsu: Jutsu) -> tuple[int, float, bool]:
        """Devolve (dano, eficácia da natureza, foi crítico)."""
        forca = atacante.base.ataque if jutsu.fisico else atacante.base.ninjutsu
        eficacia = multiplicador(jutsu.natureza, alvo.natureza)
        mesma = BONUS_MESMA_NATUREZA if jutsu.natureza is atacante.natureza else 1.0
        dano = jutsu.poder * forca / alvo.base.defesa * eficacia * mesma * FATOR_DANO
        dano *= self.rng.uniform(0.9, 1.1)
        critico = self.rng.random() < CHANCE_CRITICO
        if critico:
            dano *= MULTIPLICADOR_CRITICO
        if atacante.tem(Efeito.FORCA):
            dano *= MULTIPLICADOR_FORCA
        if alvo.tem(Efeito.ESCUDO):
            dano *= MULTIPLICADOR_ESCUDO
        return max(1, round(dano)), eficacia, critico

    # ---- Laço principal ------------------------------------------------------------
    def atualizar(self, dt: float, comandos: list[Comando | None]) -> None:
        if self.terminou:
            return
        self.tempo += dt
        for time, comando in zip(self.times, comandos):
            self._processar_time(time, comando or Comando(), dt)
        self._separar_lutadores()
        self._atualizar_projeteis(dt)
        self._atualizar_areas(dt)
        for time in self.times:
            self._atualizar_status(time.ativo, dt)
        self._verificar_nocautes()

    def _processar_time(self, time: Time, cmd: Comando, dt: float) -> None:
        time.recarga_troca = max(0.0, time.recarga_troca - dt)
        for l in time.lutadores:
            if l.vivo:
                l.recargas = [max(0.0, r - dt) for r in l.recargas]

        if time.espera_nocaute > 0:
            if cmd.trocar is not None and self.pode_trocar(time, cmd.trocar):
                time.escolha_apos_nocaute = cmd.trocar
            time.espera_nocaute -= dt
            if time.espera_nocaute <= 0:
                time.espera_nocaute = 0.0
                escolha = time.escolha_apos_nocaute
                if escolha is None or not time.lutadores[escolha].vivo:
                    escolha = time.reservas()[0]
                self._entrar(time, escolha)
                time.recarga_troca = TROCA_RECARGA / 2
            return

        eu = time.ativo
        if not eu.vivo:
            return
        eu.trava = max(0.0, eu.trava - dt)
        eu.recarga_esquiva = max(0.0, eu.recarga_esquiva - dt)
        eu.invulneravel = max(0.0, eu.invulneravel - dt)
        eu.flash = max(0.0, eu.flash - dt)

        if cmd.mira is not None and not eu.ocupado:
            direcao = cmd.mira - eu.pos
            if direcao.length_squared() > 1:
                eu.mira = direcao.normalize()

        if time.trocando:  # parado, chamando o outro ninja
            time.tempo_troca -= dt
            if time.tempo_troca <= 0:
                indice, time.troca_pendente = time.troca_pendente, None
                if time.lutadores[indice].vivo:
                    self._entrar(time, indice)
                    time.recarga_troca = TROCA_RECARGA
            else:
                self._mover(eu, Vector2(), dt)
            return

        if cmd.trocar is not None and self.pode_trocar(time, cmd.trocar):
            time.troca_pendente = cmd.trocar
            time.tempo_troca = TROCA_DURACAO
            self.eventos.append(Evento("trocando", eu.pos.copy(), texto=time.lutadores[cmd.trocar].nome,
                                       natureza=time.lutadores[cmd.trocar].natureza, lado=time.lado))
            self._mover(eu, Vector2(), dt)
            return

        if cmd.esquiva and self.pode_esquivar(eu):
            direcao = cmd.mover if cmd.mover.length_squared() > 0 else eu.mira
            eu.esquiva = ESQUIVA_DURACAO
            eu.esquiva_dir = direcao.normalize()
            eu.recarga_esquiva = ESQUIVA_RECARGA
            eu.invulneravel = max(eu.invulneravel, ESQUIVA_DURACAO + 0.06)
            self.eventos.append(Evento("esquiva", eu.pos.copy(), lado=eu.lado))

        if cmd.jutsu is not None and self.pode_usar(eu, cmd.jutsu):
            self._usar_jutsu(eu, cmd.jutsu, cmd.mira)

        self._mover(eu, cmd.mover, dt)

    # ---- Movimento -------------------------------------------------------------------
    def _mover(self, eu: Lutador, mover: Vector2, dt: float) -> None:
        antes = eu.pos.copy()
        investida = eu.investida
        if eu.esquiva > 0:
            velocidade = eu.esquiva_dir * ESQUIVA_VELOCIDADE
            eu.esquiva = max(0.0, eu.esquiva - dt)
        elif investida is not None:
            velocidade = investida.direcao * INVESTIDA_VELOCIDADE
            investida.restante -= dt
        elif eu.atordoado:
            velocidade = Vector2()
        else:
            velocidade = Vector2(mover)
            if velocidade.length_squared() > 1:
                velocidade = velocidade.normalize()
            velocidade *= eu.velocidade_movimento(self.arena)

        eu.pos += (velocidade + eu.empurrao) * dt
        eu.empurrao *= max(0.0, 1 - 9 * dt)
        eu.pos = self.arena.resolver_colisao(eu.pos, eu.raio)
        if dt > 0:
            eu.vel = (eu.pos - antes) / dt

        if investida is not None:
            alvo = self.oponente(eu.lado)
            if alvo.vivo and eu.pos.distance_to(alvo.pos) <= eu.raio + alvo.raio + 8:
                eu.investida = None
                if alvo.invulneravel <= 0:
                    self._acertar(eu, alvo, investida.jutsu, eu.pos)
            elif investida.restante <= 0 or eu.pos.distance_to(antes) < INVESTIDA_VELOCIDADE * dt * 0.3:
                eu.investida = None  # acabou o fôlego ou bateu numa pedra/parede

    def _separar_lutadores(self) -> None:
        a, b = self.times[0].ativo, self.times[1].ativo
        if not (a.vivo and b.vivo):
            return
        d = b.pos - a.pos
        distancia = d.length()
        minimo = a.raio + b.raio
        if distancia >= minimo:
            return
        if distancia < 1e-6:
            d, distancia = Vector2(1, 0), 1.0
        empurra = d / distancia * (minimo - distancia) / 2
        a.pos = self.arena.resolver_colisao(a.pos - empurra, a.raio)
        b.pos = self.arena.resolver_colisao(b.pos + empurra, b.raio)

    # ---- Jutsus ------------------------------------------------------------------------
    def _usar_jutsu(self, eu: Lutador, indice: int, mira: Vector2 | None) -> None:
        jutsu = eu.base.jutsus[indice]
        eu.recargas[indice] = jutsu.recarga
        eu.trava = RECARGA_GLOBAL
        direcao = eu.mira
        self.eventos.append(Evento("jutsu", eu.pos.copy(), texto=jutsu.nome, natureza=jutsu.natureza, lado=eu.lado))

        if jutsu.tipo is Tipo.PROJETIL:
            self._lancar(eu, jutsu, direcao)
        elif jutsu.tipo is Tipo.LEQUE:
            for k in range(jutsu.quantidade):
                self._lancar(eu, jutsu, direcao.rotate((k - (jutsu.quantidade - 1) / 2) * 12))
        elif jutsu.tipo is Tipo.CORPO:
            self.eventos.append(Evento(
                "corte", eu.pos.copy(), natureza=jutsu.natureza, angulo=direcao.as_polar()[1],
                raio=jutsu.alcance + eu.raio, lado=eu.lado,
            ))
            alvo = self.oponente(eu.lado)
            if alvo.vivo and alvo.invulneravel <= 0:
                distancia_alvo = alvo.pos - eu.pos
                distancia = distancia_alvo.length()
                if distancia <= jutsu.alcance + eu.raio + alvo.raio:
                    angulo = (direcao.angle_to(distancia_alvo) + 180) % 360 - 180 if distancia > 1 else 0
                    if abs(angulo) <= ANGULO_CORPO:
                        self._acertar(eu, alvo, jutsu, eu.pos)
        elif jutsu.tipo is Tipo.INVESTIDA:
            eu.investida = Investida(jutsu, direcao.copy(), jutsu.alcance / INVESTIDA_VELOCIDADE)
        elif jutsu.tipo is Tipo.AREA:
            ponto = mira if mira is not None else eu.pos + direcao * jutsu.alcance
            deslocamento = ponto - eu.pos
            if deslocamento.length() > jutsu.alcance:
                deslocamento.scale_to_length(jutsu.alcance)
            ponto = self.arena.limitar(eu.pos + deslocamento)
            self.areas.append(AreaAtaque(jutsu, eu, ponto, jutsu.atraso))
        elif jutsu.tipo is Tipo.SUPORTE:
            self._suporte(eu, jutsu)

    def _lancar(self, eu: Lutador, jutsu: Jutsu, direcao: Vector2) -> None:
        pos = eu.pos + direcao * (eu.raio + jutsu.raio + 2)
        self.projeteis.append(Projetil(jutsu, eu, pos, direcao * jutsu.velocidade, jutsu.alcance))

    def _suporte(self, eu: Lutador, jutsu: Jutsu) -> None:
        if jutsu.efeito is Efeito.CURA:
            antes = eu.hp
            eu.hp = min(float(eu.hp_max), eu.hp + eu.hp_max * jutsu.poder / 100)
            self.eventos.append(Evento("cura", eu.pos.copy(), valor=round(eu.hp - antes), lado=eu.lado))
        else:
            eu.status[jutsu.efeito] = jutsu.duracao
            self.eventos.append(Evento(
                "texto", eu.pos.copy(), texto=TEXTO_EFEITO.get(jutsu.efeito, jutsu.efeito.value),
                natureza=jutsu.natureza, lado=eu.lado,
            ))

    def _acertar(self, atacante: Lutador, alvo: Lutador, jutsu: Jutsu, origem: Vector2) -> None:
        dano, eficacia, critico = self.calcular_dano(atacante, alvo, jutsu)
        alvo.hp = max(0.0, alvo.hp - dano)
        alvo.flash = 0.15
        self.eventos.append(Evento(
            "dano", alvo.pos.copy(), valor=dano, natureza=jutsu.natureza, eficacia=eficacia,
            critico=critico, lado=alvo.lado,
        ))
        if not alvo.vivo:
            return

        efeito = jutsu.efeito
        if efeito in (Efeito.QUEIMADURA, Efeito.LENTIDAO, Efeito.ATORDOAR) and self.rng.random() < jutsu.chance:
            if efeito is Efeito.QUEIMADURA and alvo.natureza is Natureza.FOGO:
                return  # fogo não queima ninja de fogo
            alvo.status[efeito] = max(alvo.status.get(efeito, 0.0), jutsu.duracao)
            if efeito is Efeito.ATORDOAR:
                alvo.investida = None
            self.eventos.append(Evento("texto", alvo.pos.copy(), texto=TEXTO_EFEITO[efeito],
                                       natureza=jutsu.natureza, lado=alvo.lado))
        elif efeito is Efeito.EMPURRAO and self.rng.random() < jutsu.chance:
            direcao = alvo.pos - origem
            direcao = direcao.normalize() if direcao.length_squared() > 1 else Vector2(atacante.mira)
            alvo.empurrao = direcao * FORCA_EMPURRAO

    # ---- Projéteis e áreas ---------------------------------------------------------------
    def _atualizar_projeteis(self, dt: float) -> None:
        for p in self.projeteis:
            passo = p.vel * dt
            p.pos += passo
            p.restante -= passo.length()
            if p.restante <= 0 or not self.arena.dentro(p.pos):
                p.vivo = False
                continue
            if self.arena.colide_pedra(p.pos, p.raio):
                p.vivo = False
                self.eventos.append(Evento("explosao", p.pos.copy(), natureza=p.jutsu.natureza, raio=p.raio * 1.6))
                continue
            alvo = self.oponente(p.lado)
            if alvo.vivo and alvo.invulneravel <= 0 and p.pos.distance_to(alvo.pos) <= p.raio + alvo.raio:
                p.vivo = False
                self._acertar(p.atacante, alvo, p.jutsu, p.pos - p.vel.normalize() * 30)
        self.projeteis = [p for p in self.projeteis if p.vivo]

    def _atualizar_areas(self, dt: float) -> None:
        restantes = []
        for area in self.areas:
            area.restante -= dt
            if area.restante > 0:
                restantes.append(area)
                continue
            self.eventos.append(Evento("explosao", area.pos.copy(), natureza=area.jutsu.natureza,
                                       raio=area.jutsu.raio, lado=area.lado))
            alvo = self.oponente(area.lado)
            if alvo.vivo and alvo.invulneravel <= 0 and alvo.pos.distance_to(area.pos) <= area.jutsu.raio + alvo.raio * 0.5:
                self._acertar(area.atacante, alvo, area.jutsu, area.pos)
        self.areas = restantes

    # ---- Efeitos e nocautes ----------------------------------------------------------------
    def _atualizar_status(self, l: Lutador, dt: float) -> None:
        if not l.vivo:
            return
        if l.tem(Efeito.QUEIMADURA):
            dano = l.hp_max * QUEIMADURA_POR_SEGUNDO * dt
            l.hp = max(0.0, l.hp - dano)
            l.queimadura_acumulada += dano
            if l.queimadura_acumulada >= 4 or not l.vivo:
                self.eventos.append(Evento("queimadura", l.pos.copy(), valor=round(l.queimadura_acumulada),
                                           natureza=Natureza.FOGO, lado=l.lado))
                l.queimadura_acumulada = 0.0
        for efeito in list(l.status):
            l.status[efeito] -= dt
            if l.status[efeito] <= 0:
                del l.status[efeito]

    def _verificar_nocautes(self) -> None:
        for time in self.times:
            l = time.ativo
            if not l.vivo and not l.nocaute_anunciado:
                l.nocaute_anunciado = True
                l.limpar_efeitos()
                time.troca_pendente = None  # caiu antes de conseguir trocar
                self.eventos.append(Evento("nocaute", l.pos.copy(), texto=l.nome, lado=time.lado))
                if not time.derrotado:
                    time.espera_nocaute = ESPERA_APOS_NOCAUTE
                    time.escolha_apos_nocaute = None
        derrotados = [time.derrotado for time in self.times]
        if any(derrotados):
            self.terminou = True
            self.vencedor = None if all(derrotados) else (1 if derrotados[0] else 0)
            self.projeteis.clear()
            self.areas.clear()
            self.eventos.append(Evento("fim", Vector2(), lado=-1 if self.vencedor is None else self.vencedor))

    def _entrar(self, time: Time, indice: int) -> None:
        antigo = time.ativo
        novo = time.lutadores[indice]
        novo.pos = antigo.pos.copy()
        novo.mira = antigo.mira.copy()
        antigo.limpar_efeitos()
        novo.limpar_efeitos()
        novo.invulneravel = INVULNERAVEL_AO_ENTRAR
        time.ativo_idx = indice
        self.eventos.append(Evento("troca", novo.pos.copy(), texto=novo.nome, natureza=novo.natureza, lado=time.lado))
