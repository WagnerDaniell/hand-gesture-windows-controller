# 🖐️ Hand Gesture Windows Controller (Windows 11)

Um sistema de alto desempenho em Python para **controlar o cursor do mouse, disparar cliques atômicos e manipular janelas no Windows 11 em tempo real** através de visão computacional via webcam, com arquitetura **Dual-Hand (duas mãos)**, filtro anti-tremor **One Euro (1€ Filter)** com amortecimento suave de parada, suporte a múltiplos monitores e HUD interativo.

---

## 📋 Sumário
1. [Destaques e Funcionalidades](#-destaques-e-funcionalidades)
2. [Modos de Uso e Tabela de Gestos](#-modos-de-uso-e-tabela-de-gestos)
   - [Modo Recomendado: 2 Mãos (Dual-Hand)](#-modo-recomendado-2-mãos-dual-hand)
   - [Modo 1 Mão (Single-Hand)](#-modo-1-mão-single-hand)
   - [Trava Geral de Pausa / Retomada](#-trava-geral-de-pausa--retomada)
3. [Arquitetura do Projeto](#-arquitetura-do-projeto)
4. [Inovações Técnicas e Algoritmos](#-inovações-técnicas-e-algoritmos)
5. [Instalação e Pré-requisitos](#-instalação-e-pré-requisitos)
6. [Como Executar](#-como-executar)
7. [Atalhos de Teclado](#-atalhos-de-teclado)
8. [Configurações e Personalização (`config.py`)](#-configurações-e-personalização-configpy)
9. [Testes Automatizados](#-testes-automatizados)

---

## 🎯 Destaques e Funcionalidades

- **Arquitetura Dual-Hand (Dois Papéis Independentes)**: Separação total entre a mão que guia o mouse e a mão que dispara os cliques. A mão de mira nunca precisa mexer os dedos, eliminando 100% de solavancos e desvios ao clicar.
- **Detecção Dinâmica por Quantidade de Mãos**:
  - **1 Mão na tela**: Controla livremente o cursor por todo o monitor (não perde o foco mesmo ao cruzar a tela).
  - **2 Mãos na tela**: A mão posicionada à esquerda vira o gatilho de ações e a da direita continua na mira.
- **Clique Atômico vs. Segurar/Arrastar (100% Separados)**: Clique rápido instantâneo que não trava o botão do mouse, evitando que o Windows confunda um clique com seleção ou arraste de arquivos.
- **Trava de Pausa Universal com Punho Fechado (✊)**: Fechar o punho com qualquer uma das mãos pausa e congela o sistema instantaneamente; fechar o punho novamente destrava e retoma o controle.
- **Filtro Anti-Tremor One Euro com Smoothstep Easing**: Rigidez máxima em repouso (`min_cutoff = 0.05`), zona morta milimétrica de 2 pixels e curva de desaceleração suave que faz o cursor pousar sem tremores.
- **Multiplicador de Velocidade e Alcance de Cantos (`speed_multiplier = 1.35`)**: Deslocamento ágil do mouse que alcança todos os 4 cantos da tela sem exigir que a mão chegue nas bordas físicas da webcam.
- **Motor MediaPipe Tasks Vision com Carregamento em Buffer**: Compatível com Python 3.10 a 3.14 e imune a erros de caracteres especiais e acentuação no caminho de pastas do Windows.
- **Suporte Nativo a Múltiplos Monitores Win32**: Mapeamento sobre o Desktop Virtual (`SM_XVIRTUALSCREEN`) com emulação via `ctypes.windll.user32` a 60+ FPS sem latência.

---

## 🖐️ Modos de Uso e Tabela de Gestos

### 👐 Modo Recomendado: 2 Mãos (Dual-Hand)

Neste modo, a mão direita cuida da mira e a mão esquerda atua como gatilho:

| Mão | Gesto | Ação no Windows |
| :--- | :--- | :--- |
| **👉 Mão Direita** *(Mira)* | 👆 **Dedo Indicador Apontando** | **Move o cursor do mouse** com máxima precisão. Fica 100% firme durante os cliques. |
| **👈 Mão Esquerda** *(Ações)* | ✌️ **Dois Dedos** ou 👌 **Pinça** | **Clique Esquerdo Simples (Instantâneo)** — Dispara 1 clique pontual sem arrasto. |
| **👈 Mão Esquerda** *(Ações)* | 🖐️ **Mão Aberta** | **Segurar Clique & Arrastar (Hold Drag)** — Segura o botão esquerdo para mover janelas ou selecionar textos; solta ao fechar a mão. |

---

### ☝️ Modo 1 Mão (Single-Hand)

Quando apenas uma mão está visível na câmera:
- **👆 Dedo Indicador**: Movimenta o cursor livremente por toda a tela.
- **✌️ Dois Dedos / 👌 Pinça**: Clique simples no local apontado.
- **🖐️ Mão Aberta**: Segura o clique para arrastar.

---

### 🔒 Trava Geral de Pausa / Retomada

| Gesto | Descrição | Comportamento |
| :--- | :--- | :--- |
| ✊ **Punho Fechado** *(Qualquer Mão)* | Fechar todos os dedos em punho | **Trava / Pausa Imediata**: Congela o cursor, solta cliques e impede qualquer ação acidental.<br>**Destravar**: Faça o punho fechado (✊) novamente para retomar o controle. |

---

## 🏗️ Arquitetura do Projeto

```
hand-gesture-windows-controller/
│
├── config.py                 # Central de configurações (velocidade, margens, filtros)
├── main.py                   # Orquestrador principal, loop de vídeo e despacho de ações
├── requirements.txt          # Dependências do projeto
├── run.bat                   # Inicializador rápido para Windows
├── README.md                 # Documentação oficial
│
├── core/                     # Processamento matemático e estados
│   ├── smoothing.py          # One Euro Filter adaptativo + Deceleração Smoothstep
│   └── state_machine.py      # Máquina de estados desacoplada com debounce e cooldown
│
├── vision/                   # Visão computacional e inteligência artificial
│   ├── hand_detector.py      # Wrapper MediaPipe Tasks com suporte a multi-mãos e buffer
│   ├── gesture_classifier.py # Classificador geométrico 3D de poses e distâncias
│   └── models/
│       └── hand_landmarker.task  # Modelo de landmarks de mãos MediaPipe
│
├── window_manager/           # Integração com Windows 11 e Displays
│   ├── monitor_manager.py    # Gerenciador de múltiplos monitores e Desktop Virtual
│   └── window_controller.py  # Manipulação nativa de HWNDs e janelas Win32
│
├── input_controller/         # Emulação de mouse e atalhos
│   ├── mouse_controller.py   # Emulação de baixo nível via Win32 ctypes (zero input lag)
│   └── hotkey_listener.py    # Escuta global de atalhos de teclado (F8 / ESC)
│
├── ui/                       # Interface e feedback visual
│   └── hud_renderer.py       # HUD OpenCV moderno com identificação colorida das mãos
│
└── tests/                    # Suíte de testes automatizados
    └── test_gesture_system.py
```

---

## 🔬 Inovações Técnicas e Algoritmos

### 1. Desacoplamento Dual-Hand
Ao rastrear duas mãos simultaneamente, o sistema separa as responsabilidades com ordenação espacial no plano espelhado:
- $\text{Hand}_{\text{action}} = \arg\min_{h} (h.\text{wrist.x})$ (Mão mais à esquerda na imagem)
- $\text{Hand}_{\text{cursor}} = \arg\max_{h} (h.\text{wrist.x})$ (Mão mais à direita na imagem)

### 2. Estabilização e Amortecimento de Parada (1€ Filter + Smoothstep)
O sistema combina o **One Euro Filter** com uma função de interpolação Hermite (*Smoothstep*) para desaceleração natural:
$$\text{ease}(r) = 3r^2 - 2r^3, \quad r = \frac{d - \text{deadzone}}{\text{damping\_radius} - \text{deadzone}}$$
- Se a distância $d \le 2\text{px}$: o cursor congela (elimina ruído da câmera e tremor fisiológico).
- Se $2\text{px} < d < 14\text{px}$: o cursor realiza uma transição suave e amortecida até repousar.
- Se $d \ge 14\text{px}$: resposta direta com zero latência.

### 3. Amplificação de Alcance nos Cantos
$$\text{norm\_coord} = \left(\frac{p - \text{center}}{\text{roi\_size}}\right) \times \text{speed\_multiplier} + 0.5$$
Com `speed_multiplier = 1.35` e margens de segurança de 18%, o cursor atinge os limites $0.0$ e $1.0$ do Desktop Virtual antes que a mão do usuário chegue perto dos limites do enquadramento da câmera.

---

## 🚀 Instalação e Pré-requisitos

### Pré-requisitos
- **Windows 10 ou 11** (64-bit).
- **Python**: 3.10, 3.11, 3.12, 3.13 ou 3.14.
- **Webcam**: Integrada ou USB.

### Instalação

1. Clone ou extraia o projeto no seu computador.
2. Abra o terminal na pasta do projeto:
   ```powershell
   cd "c:\caminho\para\hand-gesture-windows-controller"
   ```
3. Crie e ative o ambiente virtual:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Instale os pacotes necessários:
   ```powershell
   pip install -r requirements.txt
   ```

---

## 💻 Como Executar

### Opção 1: Pelo Inicializador Rápido (Recomendado)
Dê um duplo clique no arquivo **`run.bat`** ou execute no terminal:
```cmd
run.bat
```

### Opção 2: Pelo Python
```powershell
.\.venv\Scripts\python.exe main.py
```

### Argumentos de Linha de Comando (CLI)
```powershell
# Usar uma webcam secundária (ex: índice 1)
.\.venv\Scripts\python.exe main.py --camera 1

# Travar o controle apenas no monitor principal
.\.venv\Scripts\python.exe main.py --mode primary_only

# Ajustar parâmetros do filtro One Euro
.\.venv\Scripts\python.exe main.py --min-cutoff 0.05 --beta 0.08
```

---

## ⌨️ Atalhos de Teclado

| Tecla | Função |
| :--- | :--- |
| **`ESC`** ou **`Q`** | 🛑 **Killswitch de Emergência** — Finaliza o programa e solta todos os cliques. |
| **`F8`** ou **`ESPAÇO`** | ⏸️ **Pausar / Retomar** — Trava ou destrava o controle via teclado. |
| **`M`** | 🖥️ **Alternar Modo de Monitor** — Cicla entre *SPAN ALL* (todos os monitores) e *PRIMARY ONLY*. |
| **`D`** | 📊 **Alternar HUD** — Oculta ou exibe as sobreposições gráficas na janela da câmera. |

---

## ⚙️ Configurações e Personalização (`config.py`)

No arquivo [`config.py`](file:///c:/Users/wagne/OneDrive/%C3%81rea%20de%20Trabalho/hand-gesture-windows-controller/config.py), você pode personalizar:

- **`speed_multiplier`** *(padrão: `1.35`)*: Velocidade e sensibilidade do mouse.
- **`margin_x_min` / `margin_x_max`** *(padrão: `0.18` / `0.82`)*: Área delimitadora de alcance na câmera.
- **`deadzone_pixels`** *(padrão: `2.0`)*: Raio de congelamento anti-tremor quando a mão está parada.
- **`damping_radius`** *(padrão: `14.0`)*: Raio de desaceleração suave de parada.
- **`min_cutoff`** *(padrão: `0.05`)*: Rigidez da filtragem em baixas velocidades.
- **`beta`** *(padrão: `0.08`)*: Aceleração em movimentos rápidos sem lag.

---

## 🧪 Testes Automatizados

Para rodar a suíte completa de testes unitários:
```powershell
.\.venv\Scripts\python.exe -m unittest discover tests
```
Resultado esperado: `Ran 12 tests in 0.004s -> OK`

---

## 🛠️ Tecnologias Utilizadas
- **Google MediaPipe Tasks API** (Detecção e rastreamento de 21 landmarks 3D)
- **OpenCV Python** (Processamento de vídeo e HUD interativo)
- **Win32 User32 Ctypes & PyWin32** (Emulação de cursor e janelas em tempo real)
- **ScreenInfo** (Geometria do Desktop Virtual Multi-Monitor)
- **Pynput** (Escuta assíncrona de atalhos globais)
