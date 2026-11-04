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

## Jogar online contra um amigo

Cada um joga no seu PC. Um **cria a partida** e o outro **entra** digitando o IP de quem criou.

**Antes de tudo:** os dois precisam ter o jogo instalado (veja "Como rodar" abaixo) e **na mesma versão**. Quem não usa Git pode baixar em **Code → Download ZIP** na página do repositório no GitHub.

### Na mesma casa (mesmo Wi-Fi)
1. Um abre o jogo e escolhe **Criar partida online**. A tela mostra o IP dele, por exemplo `192.168.0.15`.
2. O outro escolhe **Entrar em partida online**, digita esse IP e aperta Enter.
3. Os dois escolhem o time e apertam **PRONTO!** A luta começa quando os dois estiverem prontos.

### Pela internet (cada um na sua casa)
O jeito mais fácil é o **[Radmin VPN](https://www.radmin-vpn.com/)** (grátis): ele faz os dois PCs parecerem estar na mesma rede.
1. Os dois instalam o Radmin VPN.
2. Um clica em **Rede → Criar rede** (escolhe um nome e uma senha). O outro clica em **Rede → Entrar na rede** com esse nome e senha.
3. Quem criou a rede abre o jogo em **Criar partida online**. Vai aparecer um IP que começa com **26.** (é o do Radmin).
4. O outro entra com esse IP `26.x.x.x`.

> **Windows perguntou sobre o firewall?** Na primeira vez que você cria uma partida, o Windows pergunta se o Python pode usar a rede. Clique em **Permitir acesso** e marque **redes privadas e públicas** (a rede do Radmin costuma ser "pública"). Se você clicou em Cancelar sem querer, procure "Permitir um aplicativo pelo Firewall do Windows" no menu Iniciar e marque o Python.

Outras opções: [ZeroTier](https://www.zerotier.com/) ou [Tailscale](https://tailscale.com/) funcionam do mesmo jeito (usem o IP que eles mostram). Sem VPN, quem cria a partida precisa abrir a **porta 5050 (TCP)** no roteador.

**Como funciona por dentro:** quem cria a partida roda as regras da luta; o PC do amigo manda os comandos dele (andar, mirar, jutsus) e desenha o que recebe. Cada um se vê do lado esquerdo: no PC do amigo a arena aparece girada. Online a luta não pausa: o **P** abre o menu, mas seu ninja fica parado apanhando. No fim, **R** pede revanche (os dois precisam apertar) e **Enter** leva os dois de volta para a escolha de time.

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

Os testes conferem as regras (dano, naturezas, recargas, trocas, terreno), colocam duas IAs para lutar entre si até o fim, passam por todas as telas sem abrir janela e simulam uma partida online inteira entre dois jogos no mesmo PC. Também dá para rodar pela aba **Testes** (ícone de frasco) do VS Code.

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
│   ├── tela_online.py    # criar partida / entrar pelo IP
│   ├── rede.py           # conexão entre os dois PCs (TCP)
│   ├── online.py         # o que os PCs trocam: comandos e estado da luta
│   ├── interface.py      # janela, troca entre telas e mensagens online
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
- 2 jogadores no mesmo PC (teclado dividido ou controle)
- Gerar um .exe com PyInstaller para o amigo jogar sem instalar Python
- Sons com `pygame.mixer`

---

Feito com [pygame-ce](https://pyga.me/) (a versão da comunidade do Pygame; no código continua sendo `import pygame`).
