"""Inteligência do time adversário.

A IA "aperta os mesmos botões" que você: a cada quadro ela devolve um Comando
(andar, mirar, usar jutsu, esquivar, trocar). A dificuldade muda o tempo de
reação, a pontaria e a chance de desviar.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from pygame.math import Vector2

from jogo.arena import distancia_ponto_segmento
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
    movimento: float  # 1 = anda na velocidade total do ninja
    tempo_para_trocar: float  # segundos que seu ninja precisa estar em campo antes da IA pensar em trocar


DIFICULDADES = (
    Dificuldade("Fácil", reacao=1.6, erro_mira=22, percepcao=0.2, chance_esquiva=0.0, antecipacao=0.0,
                chance_troca=0.0, movimento=0.65, tempo_para_trocar=999),
    Dificuldade("Normal", reacao=1.1, erro_mira=13, percepcao=0.45, chance_esquiva=0.12, antecipacao=0.35,
                chance_troca=0.35, movimento=0.8, tempo_para_trocar=10),
    Dificuldade("Difícil", reacao=0.55, erro_mira=6, percepcao=0.75, chance_esquiva=0.35, antecipacao=0.8,
                chance_troca=0.7, movimento=1.0, tempo_para_trocar=5),
)

TEMPO_MINIMO_EM_CAMPO = 6.0  # a IA não troca um ninja que acabou de entrar


class IA:
    def __init__(self, combate: Combate, lado: int, dificuldade: Dificuldade = DIFICULDADES[1],
                 rng: random.Random | None = None):
        self.combate = combate
        self.lado = lado
        self.dif = dificuldade
        self.rng = rng or random.Random()
        self.espera_ataque = 1.5
        self.espera_troca = 1.5
        self.rival_visto: Lutador | None = None
        self.tempo_com_rival = 0.0  # há quanto tempo o ninja do jogador está em campo
        self.meu_visto: Lutador | None = None
        self.tempo_em_campo = 0.0
        self.escolha_nocaute: int | None = None
        self.giro = 1 if self.rng.random() < 0.5 else -1  # sentido em que anda em volta do rival
        self.perto = False  # True = quer lutar corpo a corpo
        self.tempo_modo = 0.0
        self.destino: Vector2 | None = None
        self.tempo_destino = 0.0
        self.mover_suave = Vector2()
        self.tempo_sem_ver = 0.0
        self.tempo_preso = 0.0
        self.ultima_pos: Vector2 | None = None
        self.reacoes: dict[int, tuple[bool, bool]] = {}  # ataque -> (percebeu, vai esquivar)

    def contar_tempo_em_campo(self, dt: float, eu: Lutador, rival: Lutador) -> None:
        if rival is not self.rival_visto:
            self.rival_visto, self.tempo_com_rival = rival, 0.0
        if eu is not self.meu_visto:
            self.meu_visto, self.tempo_em_campo = eu, 0.0
        self.tempo_com_rival += dt
        self.tempo_em_campo += dt

    # ---- Comando do quadro -------------------------------------------------------
    def comando(self, dt: float) -> Comando:
        c = Comando()
        time = self.combate.times[self.lado]
        alvo = self.combate.oponente(self.lado)
        if self.combate.terminou:
            return c
        self.contar_tempo_em_campo(dt, time.ativo, alvo)
        if time.espera_nocaute > 0:
            if self.escolha_nocaute is None:  # decide uma vez só quem entra
                melhor = self.melhor_reserva(time, alvo)
                acerta = self.rng.random() < self.dif.chance_troca
                self.escolha_nocaute = melhor if acerta else self.rng.choice(time.reservas())
            c.trocar = self.escolha_nocaute
            return c
        self.escolha_nocaute = None
        eu = time.ativo
        if not eu.vivo or time.trocando:
            return c

        troca = self.quer_trocar(dt, time, eu, alvo)
        if troca is not None:
            c.trocar = troca
            return c

        if self.desviar(eu, c):
            self.mover_suave = Vector2(c.mover)  # depois de desviar, continua dali sem tranco
            self.destino = None
        else:
            c.mover = self.posicionar(dt, eu, alvo)
        c.mover *= self.dif.movimento

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
        """Para onde andar. A IA escolhe um ponto em volta do rival e vai até ele com calma,
        em vez de recalcular a direção do zero a cada quadro (o que deixava o movimento tremido)."""
        self.tempo_modo -= dt
        if self.tempo_modo <= 0:  # só muda de ideia (perto/longe) de tempos em tempos
            perto = self.distancia_desejada(eu, alvo) < 100
            if perto != self.perto:
                self.perto, self.destino = perto, None
            self.tempo_modo = 1.5

        if self.combate.arena.linha_livre(eu.pos, alvo.pos, eu.raio):
            self.tempo_sem_ver = 0.0
        else:
            self.tempo_sem_ver += dt
            if self.tempo_sem_ver > 1.5:  # rodando em volta da pedra sem achar o rival: muda o plano
                self.tempo_sem_ver = 0.0
                if self.rng.random() < 0.5:
                    self.giro *= -1
                self.destino = None

        if self.perto:  # corpo a corpo: vai direto no rival
            encostado = eu.pos.distance_to(alvo.pos) < eu.raio + alvo.raio + 25
            desejado = Vector2() if encostado else self.direcao_ate(eu, alvo.pos)
        else:
            self.tempo_destino -= dt
            # escolhe o próximo ponto um pouco antes de chegar, para não frear e dar meia-volta
            if (self.destino is None or self.tempo_destino <= 0 or self.preso(dt, eu)
                    or eu.pos.distance_to(self.destino) < 50):
                self.destino = self.novo_destino(eu, alvo)
                self.tempo_destino = self.rng.uniform(2.0, 3.5)
            desejado = self.direcao_ate(eu, self.destino)

        # aceleração suave: nada de virar 180° de um quadro para o outro
        self.mover_suave += (desejado - self.mover_suave) * min(1.0, dt * 7)
        return Vector2(self.mover_suave)

    def direcao_ate(self, eu: Lutador, ponto: Vector2) -> Vector2:
        """Direção para chegar em `ponto`, dando a volta se tiver uma pedra no meio do caminho."""
        caminho = ponto - eu.pos
        if caminho.length_squared() < 1:
            return Vector2()
        for pedra in self.combate.arena.pedras:
            no_caminho = distancia_ponto_segmento(pedra.centro, eu.pos, ponto) < pedra.r + eu.raio
            if no_caminho and eu.pos.distance_to(pedra.centro) < caminho.length():
                lado = Vector2(-caminho.y, caminho.x).normalize()
                desvio = (eu.pos - pedra.centro).dot(lado)
                if abs(desvio) < 1:
                    lado *= self.giro  # bem alinhado com a pedra: escolhe um lado
                elif desvio < 0:
                    lado = -lado  # contorna pelo lado onde já está
                beirada = pedra.centro + lado * (pedra.r + eu.raio + 20)
                return (beirada - eu.pos).normalize()
        return caminho.normalize()

    def novo_destino(self, eu: Lutador, alvo: Lutador) -> Vector2:
        arena = self.combate.arena
        tem_longe = any(j.tipo in (Tipo.PROJETIL, Tipo.LEQUE, Tipo.AREA) for j in eu.base.jutsus)
        desejada = 290 if tem_longe else 200
        de_alvo = eu.pos - alvo.pos
        angulo_atual = de_alvo.as_polar()[1] if de_alvo.length_squared() > 1 else self.rng.uniform(0, 360)
        if self.rng.random() < 0.2:
            self.giro *= -1  # às vezes muda o sentido em que anda em volta do rival
        indo = self.mover_suave if self.mover_suave.length_squared() > 0.04 else None

        candidatos = []  # (quanto precisa virar, ponto)
        for tentativa in range(12):
            sentido = self.giro if tentativa < 8 else -self.giro
            angulo = angulo_atual + sentido * self.rng.uniform(25, 70)
            ponto = alvo.pos + Vector2(1, 0).rotate(angulo) * desejada * self.rng.uniform(0.85, 1.15)
            ponto = arena.limitar(ponto, 90)  # longe das paredes, para não encurralar nos cantos
            if ponto.distance_to(eu.pos) < 80 or arena.colide_pedra(ponto, eu.raio + 10):
                continue
            if eu.natureza is not Natureza.AGUA and any(lago.contem(ponto, 30) for lago in arena.lagos):
                continue  # a água deixa lento quem não é de Água
            virada = abs((indo.angle_to(ponto - eu.pos) + 180) % 360 - 180) if indo is not None else 0.0
            candidatos.append((virada, ponto))
        if not candidatos:
            return arena.limitar(alvo.pos + Vector2(1, 0).rotate(angulo_atual) * desejada, 90)
        # prefere seguir em frente ou fazer uma curva; meia-volta só se não tiver outro jeito
        suaves = [p for virada, p in candidatos if virada <= 90]
        return self.rng.choice(suaves) if suaves else min(candidatos, key=lambda c: c[0])[1]

    def preso(self, dt: float, eu: Lutador) -> bool:
        """True se a IA quer andar mas não sai do lugar (encalhou numa pedra ou parede)."""
        quer_andar = self.mover_suave.length_squared() > 0.1
        if quer_andar and self.ultima_pos is not None and dt > 0 and eu.pos.distance_to(self.ultima_pos) < 30 * dt:
            self.tempo_preso += dt
        else:
            self.tempo_preso = 0.0
        self.ultima_pos = eu.pos.copy()
        if self.tempo_preso > 0.4:
            self.tempo_preso = 0.0
            return True
        return False

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
        if self.tempo_em_campo < TEMPO_MINIMO_EM_CAMPO:
            return None
        melhor = self.melhor_reserva(time, alvo)
        if melhor is None or not self.combate.pode_trocar(time, melhor):
            return None
        reserva = time.lutadores[melhor]
        # só reage ao seu ninja depois de um tempo: dá para você aproveitar a vantagem
        if self.tempo_com_rival >= self.dif.tempo_para_trocar:
            ganho = self.vantagem(reserva, alvo) - self.vantagem(eu, alvo)
            if ganho >= 0.8 and self.rng.random() < self.dif.chance_troca:
                return melhor
        if eu.fracao_hp < 0.2 and reserva.fracao_hp > 0.5 and self.rng.random() < 0.3:
            return melhor
        return None
