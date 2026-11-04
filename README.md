# Arena Shinobi

Batalhas ninja **em tempo real**, feitas em **Python + Pygame**. Monte um time de 3 ninjas, entre na arena e lute contra o time do computador: ande, mire, desvie e use os 4 jutsus de cada ninja. Quando um cai, o próximo entra. Vence quem derrubar o time inteiro do outro.

## Como funciona

- **Tempo real:** nada de esperar a vez. Cada jutsu tem sua própria recarga.
- **Naturezas de chakra:** cada ninja e cada jutsu têm uma natureza. Elas formam um ciclo:

  **Água > Fogo > Vento > Terra > Raio > Água**

  Golpe forte contra a natureza do rival causa **1,6×** de dano ("Super efetivo!"); contra a natureza que o vence, só **0,6×**. Neutro (taijutsu e armas) não tem vantagem nem fraqueza. Jutsus da mesma natureza do ninja batem 20% mais forte.
  No topo da tela aparece se você está em **Vantagem**, **Desvantagem** ou **Equilibrado** (com a dica de qual ninja chamar), e na barra de jutsus uma seta **verde** mostra que o golpe é forte contra o rival atual e uma **vermelha** que é fraco.
- **Troca de ninja:** aperte 1, 2 ou 3 para trocar no meio da luta. Chamar o outro ninja leva 0,7 s, em que você fica parado e pode levar golpes, e depois a troca tem recarga de 4 s. Vale para o rival também: quando ele começa a trocar, aparece um aviso e um círculo enchendo em volta dele.
- **Tipos de jutsu:** projétil, leque (vários projéteis), corpo a corpo, investida, área (marca o chão e explode depois de um instante: dá para fugir!) e suporte (cura, escudo, velocidade, força).
- **Efeitos:** queimadura (ninjas de Fogo são imunes), lentidão, atordoamento e empurrão.
- **Esquiva:** um impulso rápido em que você fica invulnerável por um instante.
- **Terreno:** pedras bloqueiam a passagem e os projéteis. Nos lagos, ninjas de Água ficam mais rápidos e os outros ficam lentos.
- **IA** com 3 dificuldades:
  - **Fácil:** lenta, erra bastante a mira, não desvia e não troca de ninja para te contrariar.
  - **Normal:** desvia às vezes e só pensa em trocar depois que seu ninja está 10 s em campo.
  - **Difícil:** reage rápido, antecipa seu movimento, desvia bem e troca depois de 5 s.

  Os valores ficam em `DIFICULDADES`, no topo de `jogo/ia.py`.

## Os ninjas

| Ninja | Natureza | Estilo |
|---|---|---|
| Kaen | Fogo | Ataca de longe e queima |
| Mizuha | Água | Resistente, se cura, rápida na água |
| Fuuga | Vento | O mais veloz, golpes rápidos |
| Ganro | Terra | Lento, aguenta muito, bate pesado de perto |
| Shiden | Raio | Muito dano e atordoamento |
| Tetsu | Neutro | Taijutsu puro, sem fraquezas |

## Controles

| Tecla | O que faz |
|---|---|
| WASD ou setas | Andar |
| Mouse | Mirar |
| Clique esquerdo (ou J) | Jutsu 1 |
| Clique direito (ou K) | Jutsu 2 |
| Q | Jutsu 3 |
| E | Jutsu 4 |
| Espaço ou Shift | Esquivar |
| 1, 2, 3 | Trocar de ninja |
| P | Pausar |
| Esc | Pausar / voltar |

Na escolha de time: clique nos cartões (ou use as setas + Espaço, ou as teclas 1–6), **Tab** muda a dificuldade, **R** sorteia um time e **Enter** começa a luta.

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

Os testes conferem as regras (dano, naturezas, recargas, trocas, terreno), colocam duas IAs para lutar entre si até o fim e passam por todas as telas sem abrir janela. Também dá para rodar pela aba **Testes** (ícone de frasco) do VS Code.

## Estrutura

```
batalha-de-turnos/
├── main.py               # ponto de entrada
├── jogo/
│   ├── naturezas.py      # naturezas de chakra e tabela de vantagens
│   ├── jutsus.py         # como um jutsu é descrito (tipo, poder, recarga...)
│   ├── ninjas.py         # os ninjas e seus jutsus  ← comece por aqui para criar ninjas
│   ├── arena.py          # campo de batalha: pedras e lagos
│   ├── combate.py        # regras da luta em tempo real (sem tela)
│   ├── ia.py             # inteligência do rival e dificuldades
│   ├── desenho.py        # funções de desenho (textos, barras, ninjas)
│   ├── tela_titulo.py    # tela inicial
│   ├── tela_selecao.py   # escolha do time
│   ├── tela_batalha.py   # a luta: controles, efeitos e painéis
│   ├── interface.py      # janela e troca entre telas
│   └── config.py         # tamanho da janela, cores
├── tests/                # testes automáticos
├── requirements.txt
└── .vscode/              # configuração para rodar com F5
```

As **regras** (`combate.py`, `ia.py`, `ninjas.py`...) não desenham nada, e as **telas** só mostram o que acontece. Assim dá para mudar o visual sem quebrar a lógica e testar a lógica sem abrir janela.

## Ideias para continuar

- Trocar os desenhos por sprites: carregue imagens com `pygame.image.load()` em `desenhar_ninja()` (`jogo/desenho.py`)
- Mais ninjas e jutsus (é só adicionar em `jogo/ninjas.py`)
- Habilidades passivas, itens de uso rápido, clima (chuva fortalece Água, por exemplo)
- Mapa para explorar, recrutar ninjas e enfrentar mestres em sequência
- 2 jogadores no mesmo PC ou online
- Sons com `pygame.mixer`

---

Feito com [pygame-ce](https://pyga.me/) (a versão da comunidade do Pygame; no código continua sendo `import pygame`).
