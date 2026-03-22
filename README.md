# DEMI - Detector de Esqueleto, Mãos e Identificação Facial

**Módulo Inteligente 4.0** — Software de visão computacional em tempo real que usa **MediaPipe** e **OpenCV** para detectar e rastrear corpo, mãos e rosto pela webcam, com **coleta automática de dados**, **exportação CSV** e **dashboard web de KPIs**.

---

## ⚡ Como rodar — Jeito fácil (recomendado)

**Dê um duplo clique no arquivo `iniciar_demi.bat`.**

O script vai:
1. Verificar se o Python está instalado
2. Instalar todas as dependências automaticamente
3. Iniciar o dashboard no navegador (`http://localhost:5000`)
4. Abrir a câmera do DEMI

> Não precisa abrir terminal nem digitar nenhum comando.

---

## ⚠️ REQUISITO OBRIGATÓRIO — Versão do Python

> **MediaPipe NÃO é compatível com Python 3.12 ou superior.**
> 
> Use obrigatoriamente **Python 3.9, 3.10 ou 3.11**.
> 
> 📥 Download recomendado: [Python 3.11.9](https://www.python.org/downloads/release/python-3119/)
> 
> Durante a instalação, marque a opção **"Add Python to PATH"**.

Se você tiver Python 3.12+ e tentar rodar, vai aparecer um erro na instalação do MediaPipe. A solução é instalar o Python 3.11 e tentar novamente.

---

## Funcionalidades

| Recurso | Descrição |
|---|---|
| **Pose (Esqueleto)** | Detecta 33 pontos do corpo e desenha o esqueleto completo |
| **Mãos** | Rastreia até 2 mãos, identifica esquerda/direita e mostra confiança |
| **Contagem de dedos** | Conta automaticamente quantos dedos estão levantados |
| **Rosto (Face Mesh)** | Desenha a malha facial com contornos de olhos e lábios |
| **Coleta de dados** | Registra detecções a cada segundo em banco SQLite |
| **Dashboard web** | Painel com KPIs e gráficos em tempo real (Flask + Chart.js) |
| **Exportação CSV** | Exporta dataset bruto para análise externa |
| **FPS em tempo real** | Mostra o framerate com cores (verde/amarelo/vermelho) |
| **Screenshot** | Captura a tela e salva como PNG na pasta `screenshots/` |
| **Gravação de vídeo** | Grava em AVI na pasta `recordings/` |
| **Espelhamento** | Liga/desliga o espelho da câmera |
| **Troca de cores** | 7 cores disponíveis para os landmarks |
| **HUD informativo** | Barra com status, contagem de dados coletados e controles |

---

## Requisitos

- **Python 3.9, 3.10 ou 3.11** (⚠️ não use 3.12+)
- Webcam

### Instalação das dependências

```bash
pip install opencv-python mediapipe flask "numpy<2"
```

> **IMPORTANTE:** Use `opencv-python` (NÃO `opencv-python-headless`), senão a janela de vídeo não funciona.

---

## Como usar (via terminal)

### 1. Iniciar a detecção + coleta de dados

```bash
python demi.py
```

Os dados são coletados automaticamente a cada 1 segundo no banco `demi_data.db`.

### 2. Abrir o dashboard de KPIs

Em outro terminal (mantenha o demi.py rodando):

```bash
python dashboard.py
```

Acesse **http://localhost:5000** no navegador. O dashboard atualiza a cada 3 segundos automaticamente.

### 3. Exportar dados para CSV

Pressione `E` no DEMI ou exporte manualmente. Os arquivos são salvos na pasta `exports/`.

---

## Controles (Teclado)

| Tecla | Ação |
|-------|------|
| `1` | Liga/desliga detecção de **Pose** (esqueleto) |
| `2` | Liga/desliga detecção de **Mãos** |
| `3` | Liga/desliga detecção de **Rosto** |
| `C` | Troca a cor dos landmarks |
| `M` | Espelha/desespelha a imagem |
| `S` | Salva screenshot (pasta `screenshots/`) |
| `R` | Inicia/para gravação de vídeo (pasta `recordings/`) |
| `E` | Exporta dados coletados para CSV (pasta `exports/`) |
| `D` | Abre o dashboard no navegador |
| `ESC` | Fecha o programa |

---

## Cores disponíveis

Vermelho → Verde → Azul → Amarelo → Ciano → Magenta → Branco

Pressione `C` para alternar entre elas.

---

## Estrutura do Projeto

```
reconhecimento-de-camera/
├── demi.py               # Detecção + coleta de dados
├── dashboard.py          # Dashboard web com KPIs (Flask)
├── iniciar_demi.bat      # Launcher — duplo clique para rodar tudo
├── requirements.txt      # Dependências do projeto
├── demi_data.db          # Banco de dados SQLite (gerado automaticamente)
├── README.md             # Esta documentação
├── TEAM_CHARTER.md       # Team Charter da equipe
├── RELATORIO_TECNICO.md  # Relatório técnico completo
├── screenshots/          # Capturas de tela (criada automaticamente)
├── recordings/           # Gravações de vídeo (criada automaticamente)
└── exports/              # Arquivos CSV exportados (criada automaticamente)
```

---

## Arquitetura da Solução

```
[Webcam] → [demi.py - MediaPipe + OpenCV] → [SQLite DB]
                                                   ↓
                                             [dashboard.py - Flask]
                                                   ↓
                                             [Navegador - KPIs + Gráficos]
                                                   ↓
                                             [Exportação CSV]
```

### Pilares da Indústria 4.0 atendidos:

| Pilar | Como é aplicado |
|---|---|
| **Sensoriamento** | Webcam como sensor de visão computacional |
| **Coleta de dados** | Registro automático a cada segundo em SQLite |
| **Comunicação digital** | API REST via HTTP (Flask) entre backend e dashboard |
| **Visualização inteligente** | Dashboard web com KPIs, gráficos e tabelas em tempo real |
| **Dataset** | Exportação para CSV para análise externa |

---

## Arquitetura do Código

O código é organizado em funções separadas por responsabilidade:

**demi.py:**
- **`init_database()` / `start_session()` / `end_session()`** — Gerenciam o banco de dados SQLite
- **`log_detection()`** — Registra dados de detecção no banco
- **`export_to_csv()`** — Exporta dataset bruto para CSV
- **`init_pose()` / `init_hands()` / `init_face_mesh()`** — Inicializam os detectores do MediaPipe
- **`draw_pose()` / `draw_hands()` / `draw_face()`** — Desenham os landmarks no frame
- **`count_raised_fingers()`** — Algoritmo de contagem de dedos levantados
- **`draw_hud()`** — Renderiza o painel de informações na tela
- **`save_screenshot()` / `start_recording()` / `stop_recording()`** — Utilitários de captura
- **`main()`** — Loop principal com leitura de câmera, detecção, coleta e controles

**dashboard.py:**
- **API REST** (`/api/data`) — Fornece KPIs e dados em formato JSON via HTTP
- **Frontend** — HTML + CSS + Chart.js com atualização automática a cada 3 segundos
- **KPIs**: taxa de detecção, FPS médio, contagem de dedos, tempo de coleta, etc.

---

## Solução de Problemas

| Problema | Solução |
|---|---|
| `The function is not implemented` no `cv2.imshow` | Instale `opencv-python` (não headless): `pip uninstall opencv-python-headless -y && pip install opencv-python` |
| `NumPy 1.x cannot be run in NumPy 2.x` | Faça downgrade: `pip install "numpy<2"` |
| Erro ao instalar MediaPipe | Verifique se está usando Python 3.9, 3.10 ou 3.11 (não 3.12+) |
| Câmera não abre | Verifique se outra aplicação está usando a webcam |
| FPS muito baixo | Desative módulos que não precisa (teclas 1, 2, 3) |