"""Ponto de entrada do jogo.

Rode com `python main.py` no terminal, ou aperte F5 no VS Code.
"""
from jogo.interface import Jogo


def main() -> None:
    Jogo().executar()


if __name__ == "__main__":
    main()
