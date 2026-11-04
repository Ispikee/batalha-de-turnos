"""Como um jutsu funciona: tipo, poder, recarga, alcance e efeitos."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from jogo.naturezas import Natureza


class Tipo(Enum):
    PROJETIL = "Projétil"  # voa em linha reta e para na primeira coisa que acertar
    LEQUE = "Leque"  # vários projéteis abertos em leque
    CORPO = "Corpo a corpo"  # golpe curto na frente do ninja
    INVESTIDA = "Investida"  # o ninja dispara para a frente e acerta quem estiver no caminho
    AREA = "Área"  # marca um círculo no chão; explode depois de um tempinho
    SUPORTE = "Suporte"  # efeito no próprio ninja (cura, escudo, etc.)


class Efeito(Enum):
    NENHUM = "Nenhum"
    QUEIMADURA = "Queimadura"  # perde HP aos poucos (ninjas de Fogo são imunes)
    LENTIDAO = "Lentidão"  # anda mais devagar
    ATORDOAR = "Atordoar"  # não anda nem usa jutsus por um instante
    EMPURRAO = "Empurrão"  # joga o alvo para trás
    CURA = "Cura"  # recupera `poder`% do HP máximo
    ESCUDO = "Escudo"  # recebe metade do dano
    VELOCIDADE = "Velocidade"  # anda mais rápido
    FORCA = "Força"  # causa mais dano


@dataclass(frozen=True)
class Jutsu:
    nome: str
    natureza: Natureza
    tipo: Tipo
    poder: int = 0
    recarga: float = 1.0  # segundos até poder usar de novo
    alcance: float = 400.0  # distância do projétil / da investida / do golpe / de onde a área pode cair
    velocidade: float = 600.0  # velocidade do projétil (pixels por segundo)
    raio: float = 10.0  # tamanho do projétil ou da área
    atraso: float = 0.0  # tempo até a área explodir
    efeito: Efeito = Efeito.NENHUM
    chance: float = 1.0  # chance do efeito acontecer
    duracao: float = 0.0  # duração do efeito
    quantidade: int = 1  # número de projéteis (leque)

    @property
    def causa_dano(self) -> bool:
        return self.tipo is not Tipo.SUPORTE

    @property
    def fisico(self) -> bool:
        """Golpes físicos usam o Ataque do ninja; os elementais à distância usam Ninjutsu."""
        return self.natureza is Natureza.NEUTRO or self.tipo in (Tipo.CORPO, Tipo.INVESTIDA)
