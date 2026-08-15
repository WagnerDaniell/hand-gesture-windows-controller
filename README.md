# 🖐️ Hand Gesture Windows Controller (Windows 11)

Um sistema completo em Python de alta performance para **controlar o cursor do mouse e gerenciar janelas do Windows 11 em tempo real** através de gestos manuais capturados pela webcam, com suporte a múltiplos monitores, filtro anti-tremor One Euro (1€ Filter), debounce de segurança e HUD interativo.

---

## 📋 Sumário
1. [Objetivos e Funcionalidades](#-objetivos-e-funcionalidades)
2. [Tabela de Gestos](#-tabela-de-gestos)
3. [Arquitetura do Sistema](#-arquitetura-do-sistema)
4. [Análise Técnica e Bibliotecas Escolhidas](#-análise-técnica-e-bibliotecas-escolhidas)
5. [Instalação e Pré-requisitos](#-instalação-e-pré-requisitos)
6. [Como Executar](#-como-executar)
7. [Atalhos e Botão de Emergência](#-atalhos-e-botão-de-emergência)
8. [Configurações e Calibração](#-configurações-e-calibração)
9. [Testes Automatizados](#-testes-automatizados)

---

## 🎯 Objetivos e Funcionalidades

- **Detecção de Mãos em Tempo Real**: Rastreamento de 21 landmarks 3D usando **Google MediaPipe Hands**.
- **Controle de Janelas e Mouse no Windows 11**: Utilização de APIs nativas Win32 (`pywin32`, `ctypes.windll.user32`) para resposta instantânea a 60+ FPS sem latência.
- **Suporte Nativo a Múltiplos Monitores**: Mapeamento contínuo sobre o Desktop Virtual do Windows (`SM_XVIRTUALSCREEN`, `SM_CXVIRTUALSCREEN`), permitindo arrastar janelas entre monitores com facilidade.
- **Filtro Anti-Tremor One Euro (1€ Filter)**: Algoritmo de filtragem adaptativo por velocidade — alta suavidade e estabilidade para cliques precisos em baixa velocidade, e zero atraso em movimentos rápidos.
- **Zona Ativa de Calibração (ROI)**: Caixa delimitadora configurável na câmera para que o usuário alcance todos os cantos da tela com conforto, sem precisar esticar os braços.
- **Sistema de Debounce & Histerese**: Previne cliques acidentais e flickers de transição de estado.
- **Killswitch Global de Emergência**: Interrupção ou pausa imediata a qualquer momento (via teclas `ESC` ou `F8`), mesmo com o HUD minimizado.
- **HUD Visual Moderno**: Interface em OpenCV mostrando o esqueleto da mão, métricas em tempo real, estado do mouse, coordenadas e FPS.

---

## 🖐️ Tabela de Gestos

| Gesto | Descrição do Gesto | Ação no Windows |
| :--- | :--- | :--- |
| 👆 **Dedo Indicador Levantado** | Dedo indicador estendido; médium, anelar e mínimo dobrados | **Move o cursor do mouse** com suavidade milimétrica sobre a tela. |
| 👌 **Pinça (Indicador + Polegar)** | Ponta do indicador e polegar aproximados/tocando | **Clique e Segurar Botão Esquerdo** (`mouse_down`). Ao mover a mão, **arrasta janelas** pela barra de título ou itens na tela. |
| 🖐️ **Mão Aberta** | Todos os 5 dedos estendidos | **Solta o botão esquerdo** (`mouse_up`) / Estado de sobrevoo neutro. |
| ↔️ **Movimento Lateral (Pinçado)** | Mão em pinça movendo-se lateralmente | **Move e transfere a janela** entre os monitores conectados. |
| ✊ **Punho Fechado** | Todos os dedos fechados em direção à palma | **Trava de Segurança / Neutro** — nenhuma ação é executada (permite descansar a mão). |

---

## 🏗️ Arquitetura do Sistema

O projeto segue princípios de arquitetura modular, limpa e desacoplada:

```
projetopython/
│
├── config.py                 # Central de configurações e hiperparâmetros
├── main.py                   # Orquestrador e loop principal da aplicação
├── requirements.txt          # Dependências do projeto
├── run.bat                   # Script inicializador para Windows
├── README.md                 # Documentação completa
│
├── core/                     # Núcleo de processamento matemático e lógica
│   ├── __init__.py
│   ├── smoothing.py          # Implementação do 1€ Filter (One Euro) e EMA
│   └── state_machine.py      # Máquina de estados com debounce e histerese
│
├── vision/                   # Módulos de visão computacional
│   ├── __init__.py
│   ├── hand_detector.py      # Wrapper do MediaPipe Hands com normalização de escala
│   └── gesture_classifier.py # Classificador geométrico de poses e distâncias 3D
│
├── window_manager/           # Integração com Windows 11 e Monitores
│   ├── __init__.py
│   ├── monitor_manager.py    # Gerenciamento de múltiplos monitores e Desktop Virtual
│   └── window_controller.py  # Manipulação de HWNDs, janelas e docking Win32
│
├── input_controller/         # Emulação de mouse e escuta de teclado
│   ├── __init__.py
│   ├── mouse_controller.py   # Emulador Win32 ctypes para movimentos sem lag
│   └── hotkey_listener.py    # Hook global de teclado via pynput para Killswitch
│
├── ui/                       # Interface gráfica e feedback visual
│   ├── __init__.py
│   └── hud_renderer.py       # Renderizador do HUD OpenCV de alta fidelidade
│
└── tests/                    # Suíte de testes unitários automatizados
    └── test_gesture_system.py
```

---

## 🔬 Análise Técnica e Bibliotecas Escolhidas

### 1. Manipulação de Janelas e Múltiplos Monitores no Windows 11
- **`pywin32` (`win32gui`, `win32api`, `win32con`)**: Escolhida por ser a biblioteca padrão da indústria para comunicação direta com a API Win32 no Windows. Fornece acesso nativo a `GetSystemMetrics(SM_XVIRTUALSCREEN)` (que cobre monitores com coordenadas negativas e resoluções assimétricas), `WindowFromPoint`, `GetAncestor` e `SetWindowPos`.
- **`screeninfo`**: Fornece enumeração limpa e estruturada das dimensões físicas e virtuais de cada display conectado.

### 2. Controle de Mouse de Baixíssima Latência
- **`ctypes.windll.user32`**: Chamadas diretas a `SetCursorPos` e `mouse_event` são despachadas diretamente para o subsistema do Windows em microssegundos, eliminando o atraso de 100ms comum no modo padrão de bibliotecas de automação genéricas.
- **`pyautogui`**: Configurado com `PAUSE = 0` e `FAILSAFE = False` como camada de utilidades e fallback.

### 3. Filtro Anti-Tremor: One Euro Filter (1€ Filter)
- Mãos humanas apresentam micro-tremores naturais quando tentamos mantê-las paradas no ar. Filtros comuns (como média móvel simples) adicionam atraso indesejado.
- O **One Euro Filter** (*Casiez et al., CHI 2012*) resolve isso usando uma frequência de corte adaptativa à velocidade:
  $$\hat{x}_k = \alpha x_k + (1-\alpha)\hat{x}_{k-1}$$
  $$\alpha = \frac{1}{1 + \frac{\tau}{T}}, \quad \tau = \frac{1}{2\pi (f_{c,\min} + \beta |\dot{x}|)}$$
- Quando a mão está quase parada ($|\dot{x}| \approx 0$), o filtro prioriza a estabilidade extrema. Em movimentos rápidos, o cutoff aumenta e a latência cai a zero.

---

## 🚀 Instalação e Pré-requisitos

### Pré-requisitos
- **Sistema Operacional**: Windows 10 ou Windows 11 (64-bit).
- **Python**: Versão 3.10, 3.11 ou 3.12 instalada.
- **Webcam**: Integrada ou USB.

### Passo a Passo

1. **Abra o terminal (PowerShell ou CMD) na pasta do projeto**:
   ```powershell
   cd C:\Users\wagne\Desktop\projetopython
   ```

2. **Crie e ative o ambiente virtual (se ainda não existir)**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Instale as dependências**:
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

### Opções de Linha de Comando
Você pode personalizar parâmetros diretamente via CLI:
```powershell
# Usar câmera específica (ex: câmera externa 1)
.\.venv\Scripts\python.exe main.py --camera 1

# Mudar modo de monitor (span_all ou primary_only)
.\.venv\Scripts\python.exe main.py --mode primary_only

# Ajustar sensibilidade do filtro anti-tremor
.\.venv\Scripts\python.exe main.py --min-cutoff 1.0 --beta 0.08
```

---

## ⌨️ Atalhos e Botão de Emergência

O aplicativo possui escuta global de teclado ativa em segundo plano:

| Tecla | Função |
| :--- | :--- |
| **`ESC`** ou **`Q`** | 🛑 **Killswitch de Emergência** — Encerra a aplicação e libera imediatamente os botões do mouse. |
| **`F8`** ou **`ESPAÇO`** | ⏸️ **Pausar / Retomar** — Trava o controle por gestos temporariamente sem fechar o programa. |
| **`M`** | 🖥️ **Alternar Modo de Monitor** — Cicla entre *SPAN ALL* (todos os monitores) e *PRIMARY ONLY*. |
| **`D`** | 📊 **Alternar HUD** — Oculta/exibe painéis de telemetria na janela OpenCV. |

---

## ⚙️ Configurações e Calibração

Todas as preferências podem ser ajustadas em [`config.py`](file:///C:/Users/wagne/Desktop/projetopython/config.py):

- **Área Ativa (ROI)**: `margin_x_min = 0.15`, `margin_x_max = 0.85` (delimita o retângulo azul na tela onde sua mão mapeia de 0% a 100% da tela).
- **Distância de Pinça**: `pinch_threshold = 0.32` e `pinch_release_threshold = 0.45` (normalizados pelo comprimento da palma, permitindo usar de perto ou de longe).
- **Debounce de Cliques**: `click_debounce_frames = 2` (exige 2 quadros consecutivos para confirmar a mudança de gesto).

---

## 🧪 Testes Automatizados

Para rodar a suíte de testes unitários e validar todos os cálculos matemáticos e estados:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```
Resultado esperado: `Ran 10 tests in 0.003s -> OK`

---

## 👨‍💻 Desenvolvido com
- **Google MediaPipe** (Computer Vision & Hand Pose)
- **OpenCV** (Real-time Video Processing & HUD)
- **PyWin32 & Windows User32 SDK** (Win32 OS Interop)
- **ScreenInfo** (Multi-Monitor Geometry Engine)
