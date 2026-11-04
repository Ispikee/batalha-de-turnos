# Batalha de Turnos

Jogo de batalha por turnos feito em **Python + Pygame**. Você controla o Herói contra um Goblin: escolha uma ação, veja o inimigo responder e tente vencer antes que seu HP acabe.

## O que já funciona

- 4 ações: **Atacar**, **Magia** (gasta MP, bate forte e ignora defesa), **Defender** (corta o próximo dano pela metade e recupera MP) e **Curar** (gasta MP)
- Inimigo com uma IA simples (cura quando está fraco, às vezes usa magia ou defende)
- Acertos críticos, barras de HP/MP animadas, números de dano subindo, registro da batalha
- Tela de vitória/derrota com opção de jogar de novo
- Testes automáticos das regras com `pytest`

## Controles

| Tecla | O que faz |
|---|---|
| Setas ↑/↓ ou W/S | Escolher ação |
| Enter ou Espaço | Confirmar |
| 1, 2, 3, 4 | Usar a ação direto |
| Mouse | Passar por cima e clicar |
| R | Jogar de novo (no fim da luta) |
| Esc | Sair |

## Como rodar no VS Code

**Precisa ter:** [Python 3.10 a 3.13](https://www.python.org/downloads/) (no Windows, marque *"Add python.exe to PATH"* na instalação), [VS Code](https://code.visualstudio.com/) e [Git](https://git-scm.com/downloads).

1. Abra a pasta do projeto no VS Code (**Arquivo → Abrir Pasta**). Aceite instalar as extensões recomendadas (Python).
2. Abra o terminal (**Terminal → Novo Terminal**) e crie o ambiente virtual:

   **Windows**
   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```
   > Se o PowerShell bloquear a ativação, rode uma vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

   **macOS / Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Aperte **F5** (configuração **"Jogar"**) ou rode `python main.py`.

Se o VS Code perguntar qual interpretador usar, escolha o que tem `.venv` no caminho (**Ctrl+Shift+P → "Python: Select Interpreter"**).

## Testes

```bash
pytest
```

Também dá para rodar pela aba **Testes** (ícone de frasco) do VS Code.

## Estrutura

```
batalha-de-turnos/
├── main.py              # ponto de entrada
├── jogo/
│   ├── batalha.py       # regras: dano, ações, IA do inimigo (sem Pygame)
│   ├── personagem.py    # personagens e seus atributos
│   ├── interface.py     # tela, desenho, teclado e mouse (Pygame)
│   └── config.py        # tamanho da janela, cores, tempos
├── tests/
│   └── test_batalha.py  # testes das regras
├── requirements.txt
└── .vscode/             # configuração para rodar com F5
```

A ideia é manter **regras** (`batalha.py`, `personagem.py`) separadas da **tela** (`interface.py`). Assim você pode mudar o visual sem quebrar a lógica, e testar a lógica sem abrir janela.

## Ideias para continuar

- Trocar as formas por sprites: carregue imagens com `pygame.image.load()` em `desenhar_lutador()`
- Mais inimigos e uma sequência de lutas
- Itens (poção, éter), status (veneno, atordoado), níveis e experiência
- Times com vários personagens de cada lado
- Sons com `pygame.mixer`

---

Feito com [pygame-ce](https://pyga.me/) (a versão da comunidade do Pygame; no código continua sendo `import pygame`).
