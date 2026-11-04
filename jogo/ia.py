"""Inteligência do time adversário.

A IA "aperta os mesmos botões" que você: a cada quadro ela devolve um Comando
(andar, mirar, usar jutsu, esquivar, trocar). A dificuldade muda o tempo de
reação, a pontaria e a chance de desviar.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from pygame.math import Vector2

from jogo.combate import INVESTIDA_VELOCIDADE, Combate, Comando, Lutador, Time
from jogo.jutsus import Efeito, Jutsu, Tipo
from jogo.naturezas import Natureza, multiplicador


@dataclass(frozen=True)
class Dificuldade:
    nome: str
    reacao: float  # segundos (em média) entre um ataque e outro
    erro_mira: float  # graus
    percepcao: float  # chance de perceber um ataque vindo
    chance_esquiva: float  # chance de usar a esquiva quando percebe
    antecipacao: float  # 0 = mira onde você está; 1 = mira onde você vai estar
    chance_troca: float  # chance de trocar quando está em desvantagem


DIFICULDADES = (
    Dificuldade("Fácil", reacao=1.0, erro_mira=16, percepcao=0.35, chance_esquiva=0.1, antecipacao=0.2, chance_troca=0.2),
    Dificuldade("Normal", reacao=0.6, erro_mira=8, percepcao=0.65, chance_esquiva=0.3, antecipacao=0.6, chance_troca=0.5),
    Dificuldade("Difícil", reacao=0.3, erro_mira=3, percepcao=0.9, chance_esquiva=0.6, antecipacao=1.0, chance_troca=0.85),
)


class IA:
    def __init__(self, combate: Combate, lado: int, dificuldade: Dificuldade = DIFICULDADES[1],
                 rng: random.Random | None = None):
        self.combate = combate
        self.lado = lado
        self.dif = dificuldade
        self.rng = rng or random.Random()
        self.espera_ataque = 0.8
        self.espera_troca = 3.0
        self.giro = 1 if self.rng.random() < 0.5 else -1
        self.tempo_giro = 1.5
        self.tempo_preso = 0.0
        self.ultima_pos: Vector2 | None = None
        self.reacoes: dict[int, tuple[bool, bool]] = {}  # ataque -> (percebeu, vai esquivar)

    # ---- Comando do quadro -------------------------------------------------------
    def comando(self, dt: float) -> Comando:
        c = Comando()
        time = self.combate.times[self.lado]
        alvo = self.combate.oponente(self.lado)
        if self.combate.terminou:
            return c
        if time.espera_nocaute > 0:
            c.trocar = self.melhor_reserva(time, alvo)
            return c
        eu = time.ativo
        if not eu.vivo:
            return c

        troca = self.quer_trocar(dt, time, eu, alvo)
        if troca is not None:
            c.trocar = troca
            return c

        if not self.desviar(eu, c):
            c.mover = self.posicionar(dt, eu, alvo)

        indice = self.escolher_jutsu(dt, eu, alvo) if alvo.vivo else None
        jutsu = eu.base.jutsus[indice] if indice is not None else None
        c.jutsu = indice
        c.mira = self.mirar(eu, alvo, jutsu)
        return c

    # ---- Mira ----------------------------------------------------------------------
    def mirar(self, eu: Lutador, alvo: Lutador, jutsu: Jutsu | None) -> Vector2:
        if jutsu is None:
            return alvo.pos.copy()
        distancia = eu.pos.distance_to(alvo.pos)
        tempo = 0.0
        if jutsu.tipo in (Tipo.PROJETIL, Tipo.LEQUE):
            tempo = distancia / jutsu.velocidade
        elif jutsu.tipo is Tipo.AREA:
            tempo = jutsu.atraso
        elif jutsu.tipo is Tipo.INVESTIDA:
            tempo = distancia / INVESTIDA_VELOCIDADE
        ponto = alvo.pos + alvo.vel * tempo * self.dif.antecipacao
        if jutsu.tipo is Tipo.AREA:
            erro = self.dif.erro_mira * 3
            return ponto + Vector2(self.rng.gauss(0, erro), self.rng.gauss(0, erro))
        deslocamento = ponto - eu.pos
        if deslocamento.length_squared() < 1:
            return ponto
        return eu.pos + deslocamento.rotate(self.rng.gauss(0, self.dif.erro_mira))

    # ---- Escolha do jutsu -----------------------------------------------------------
    def escolher_jutsu(self, dt: float, eu: Lutador, alvo: Lutador) -> int | None:
        self.espera_ataque -= dt
        if self.espera_ataque > 0:
            return None
        distancia = eu.pos.distance_to(alvo.pos)
        opcoes = []
        for i, jutsu in enumerate(eu.base.jutsus):
            if self.combate.pode_usar(eu, i):
                nota = self.avaliar(eu, alvo, jutsu, distancia)
                if nota > 0:
                    opcoes.append((nota * self.rng.uniform(0.8, 1.2), i))
        if not opcoes:
            return None
        self.espera_ataque = self.dif.reacao * self.rng.uniform(0.6, 1.4)
        return max(opcoes)[1]

    def avaliar(self, eu: Lutador, alvo: Lutador, jutsu: Jutsu, distancia: float) -> float:
        if jutsu.tipo is Tipo.SUPORTE:
            if jutsu.efeito is Efeito.CURA:
                return 40 if eu.fracao_hp < 0.5 else 0
            if eu.tem(jutsu.efeito):
                return 0
            if jutsu.efeito is Efeito.ESCUDO:
                return 25 if distancia < 260 else 0
            if jutsu.efeito is Efeito.FORCA:
                return 22 if distancia < 350 else 0
            return 15
        nota = jutsu.poder * multiplicador(jutsu.natureza, alvo.natureza)
        if jutsu.natureza is eu.natureza:
            nota *= 1.2
        livre = self.combate.arena.linha_livre(eu.pos, alvo.pos, jutsu.raio if jutsu.tipo is not Tipo.INVESTIDA else eu.raio)
        if jutsu.tipo in (Tipo.PROJETIL, Tipo.LEQUE):
            if distancia > jutsu.alcance * 0.95 or not livre:
                return 0
            if jutsu.tipo is Tipo.LEQUE:
                nota *= jutsu.quantidade ** 0.6
        elif jutsu.tipo is Tipo.CORPO:
            if distancia > jutsu.alcance + eu.raio + alvo.raio - 5:
                return 0
            nota *= 1.2
        elif jutsu.tipo is Tipo.INVESTIDA:
            if distancia > jutsu.alcance + 20 or not livre:
                return 0
        elif jutsu.tipo is Tipo.AREA:
            if distancia > jutsu.alcance + jutsu.raio * 0.5:
                return 0
            nota *= 0.9
        return nota

    # ---- Movimento ---------------------------------------------------------------------
    def distancia_desejada(self, eu: Lutador, alvo: Lutador) -> float:
        melhor_perto = melhor_longe = 0.0
        for i, jutsu in enumerate(eu.base.jutsus):
            if not jutsu.causa_dano or eu.recargas[i] > 0.4:
                continue
            nota = jutsu.poder * multiplicador(jutsu.natureza, alvo.natureza)
            if jutsu.tipo in (Tipo.CORPO, Tipo.INVESTIDA):
                melhor_perto = max(melhor_perto, nota)
            else:
                melhor_longe = max(melhor_longe, nota)
        if melhor_perto > melhor_longe * 1.1:
            return 55
        return 290 if melhor_longe else 200

    def posicionar(self, dt: float, eu: Lutador, alvo: Lutador) -> Vector2:
        para_alvo = alvo.pos - eu.pos
        distancia = para_alvo.length()
        direcao = para_alvo / distancia if distancia > 1 else Vector2(1, 0)
        desejada = self.distancia_desejada(eu, alvo)

        self.tempo_giro -= dt
        if self.tempo_giro <= 0:
            self.giro *= -1
            self.tempo_giro = self.rng.uniform(1.2, 3.0)
        tangente = direcao.rotate(90) * self.giro

        if distancia > desejada + 50:
            mover = direcao + tangente * 0.35
        elif distancia < desejada - 50:
            mover = -direcao + tangente * 0.5
        else:
            mover = tangente

        if eu.natureza is not Natureza.AGUA:  # foge da água, que deixa lento
            for lago in self.combate.arena.lagos:
                fora = eu.pos - lago.centro
                if 0 < fora.length() < lago.r + 60:
                    mover += fora.normalize() * 0.9

        if self.ultima_pos is not None and dt > 0 and eu.pos.distance_to(self.ultima_pos) < 40 * dt:
            self.tempo_preso += dt
            if self.tempo_preso > 0.4:  # encalhou numa pedra ou na parede: muda de lado
                self.giro *= -1
                self.tempo_preso = 0.0
        else:
            self.tempo_preso = 0.0
        self.ultima_pos = eu.pos.copy()
        return mover

    def desviar(self, eu: Lutador, c: Comando) -> bool:
        """Se tem um ataque vindo, sai do caminho. Devolve True se está fugindo."""
        for p in self.combate.projeteis:
            if p.lado == self.lado:
                continue
            v2 = p.vel.length_squared()
            if v2 == 0:
                continue
            t = (eu.pos - p.pos).dot(p.vel) / v2
            if t < 0 or t > 0.45:
                continue
            mais_perto = p.pos + p.vel * t
            if mais_perto.distance_to(eu.pos) > eu.raio + p.raio + 10:
                continue
            percebeu, vai_esquivar = self.reagir(p.ident)
            if not percebeu:
                continue
            lateral = p.vel.rotate(90).normalize()
            if (eu.pos - mais_perto).dot(lateral) < 0:
                lateral = -lateral
            c.mover = lateral
            c.esquiva = vai_esquivar and t < 0.22
            return True

        for area in self.combate.areas:
            if area.lado == self.lado:
                continue
            fora = eu.pos - area.pos
            if fora.length() > area.jutsu.raio + eu.raio + 10:
                continue
            percebeu, vai_esquivar = self.reagir(area.ident)
            if not percebeu:
                continue
            c.mover = fora.normalize() if fora.length_squared() > 1 else Vector2(1, 0).rotate(self.rng.uniform(0, 360))
            c.esquiva = vai_esquivar and area.restante < 0.25
            return True
        return False

    def reagir(self, ident: int) -> tuple[bool, bool]:
        if ident not in self.reacoes:
            percebeu = self.rng.random() < self.dif.percepcao
            self.reacoes[ident] = (percebeu, percebeu and self.rng.random() < self.dif.chance_esquiva)
            if len(self.reacoes) > 200:
                self.reacoes.pop(next(iter(self.reacoes)))
        return self.reacoes[ident]

    # ---- Trocas ------------------------------------------------------------------------
    def vantagem(self, l: Lutador, alvo: Lutador) -> float:
        ataque = max((multiplicador(j.natureza, alvo.natureza) for j in l.base.jutsus if j.causa_dano), default=1.0)
        defesa = multiplicador(alvo.natureza, l.natureza)
        return ataque - defesa + 0.3 * l.fracao_hp

    def melhor_reserva(self, time: Time, alvo: Lutador) -> int | None:
        reservas = time.reservas()
        if not reservas:
            return None
        return max(reservas, key=lambda i: self.vantagem(time.lutadores[i], alvo))

    def quer_trocar(self, dt: float, time: Time, eu: Lutador, alvo: Lutador) -> int | None:
        self.espera_troca -= dt
        if self.espera_troca > 0 or not alvo.vivo:
            return None
        self.espera_troca = 1.5
        melhor = self.melhor_reserva(time, alvo)
        if melhor is None or not self.combate.pode_trocar(time, melhor):
            return None
        reserva = time.lutadores[melhor]
        ganho = self.vantagem(reserva, alvo) - self.vantagem(eu, alvo)
        if ganho >= 0.8 and self.rng.random() < self.dif.chance_troca:
            return melhor
        if eu.fracao_hp < 0.2 and reserva.fracao_hp > 0.5 and self.rng.random() < 0.3:
            return melhor
        return None
