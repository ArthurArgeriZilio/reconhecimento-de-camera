# Relatório Técnico — DEMI: Módulo Inteligente 4.0
## Monitoramento de Segurança Industrial por Visão Computacional

Equipe: Data Stick
Integrantes: Arthur Argeri Zilio (839601), João Pedro Carvalho Freitas (769667), Gustavo Henrique (840899)
Curso: Engenharia de Software — Indústria 4.0
Data: Março de 2026

---

## 1. Introdução / Problema Abordado

A Indústria 4.0 trouxe uma transformação profunda na forma como as fábricas e ambientes de trabalho operam. Entre os pilares dessa revolução, a visão computacional se destacou como uma das tecnologias mais versáteis: ela permite que máquinas "enxerguem" e interpretem o ambiente ao redor, gerando dados que antes exigiam inspeção humana constante.

Nesse contexto, o problema que a gente quis resolver foi simples de enunciar, mas complicado de implementar: como monitorar a segurança ergonômica de um trabalhador em tempo real, sem depender de sensores físicos caros ou equipamentos especializados? Sensores de pressão, acelerômetros e câmeras industriais têm custo elevado e exigem infraestrutura específica. A pergunta foi: será que uma webcam comum, combinada com algoritmos de visão computacional, consegue substituir esses dispositivos para fins de monitoramento de postura e fadiga?

A resposta que chegamos foi sim — com limitações, mas sim. O DEMI (Detector de Esqueleto, Mãos e Identificação Facial) é o resultado desse trabalho. O sistema usa uma webcam padrão como sensor de visão, aplica modelos de machine learning via MediaPipe para extrair dados corporais em tempo real, armazena essas informações em banco de dados local e exibe tudo num dashboard web com alertas automáticos de segurança industrial.

A justificativa para usar a webcam como sensor principal está no custo-benefício: qualquer computador moderno tem uma webcam embutida ou de baixo custo. Isso torna a solução acessível para pequenas empresas, laboratórios ou ambientes educacionais, que raramente têm orçamento para sensores industriais dedicados.

---

## 2. Descrição do Sensor / Hardware Utilizado

O "sensor" do nosso sistema é uma webcam padrão USB, configurada para capturar frames em resolução **1280x720 pixels** (HD), com taxa de captura que varia entre 18 e 32 FPS dependendo da carga computacional. Na média dos sete dias de coleta, o sistema operou a **26,5 FPS**, o que é suficiente para detectar movimentos corporais em tempo real.

É importante deixar claro o motivo de considerar a webcam como sensor: ela captura dados físicos do ambiente (luz refletida pelos objetos) e os converte em sinal digital (arquivo de imagem), exatamente como um sensor de temperatura converte calor em sinal elétrico. A diferença é que os dados captados pela câmera são muito mais ricos — uma imagem contém informação sobre posição, forma, distância relativa, expressão facial, etc.

O processamento desses dados brutos de imagem é feito pelo **MediaPipe**, biblioteca do Google que funciona como o "motor de interpretação" do sensor. O MediaPipe aplica modelos de deep learning para extrair, de cada frame:

- **33 pontos de pose corporal** (esqueleto completo, incluindo ombros, quadris, joelhos, pulsos)
- **21 pontos por mão** (para cada mão detectada, até 2 simultâneas)
- **468 pontos de malha facial** (olhos, sobrancelhas, lábios, contorno do rosto)

Esses pontos são coordenadas normalizadas no espaço 2D (e parcialmente 3D), que o DEMI usa para calcular ângulos, distâncias e padrões de movimento — gerando, por fim, os alertas de segurança.

**Especificações técnicas do sensor:**

| Parâmetro | Valor |
|---|---|
| Resolução | 1280x720 px (HD) |
| FPS médio | 26,5 |
| FPS mínimo registrado | 18,0 |
| FPS máximo registrado | 32,0 |
| Interface | USB / Integrada |
| Biblioteca de processamento | MediaPipe 0.10.x |
| Pontos de pose extraídos | 33 |
| Pontos por mão | 21 |
| Pontos faciais | 468 |

---

## 3. Arquitetura da Solução

A arquitetura do DEMI segue um fluxo de processamento em camadas, do sensor até a visualização:

```
[Webcam (Sensor)] 
       ↓ frames em tempo real
[demi.py — MediaPipe + OpenCV]
       ↓ 1 registro/segundo
[SQLite DB — demi_data.db]
       ↓ queries SQL
[dashboard.py — Flask REST API]
       ↓ JSON via HTTP (/api/data)
[Navegador — KPIs + Gráficos Chart.js]
       ↓ exportação manual (tecla E)
[CSV Export — pasta exports/]
```

**Camada 1 — Captura (Webcam):** A câmera envia frames brutos para o processo principal. O OpenCV gerencia a captura com `cv2.VideoCapture(0)`.

**Camada 2 — Processamento (demi.py):** O coração do sistema. Aplica os três modelos do MediaPipe (pose, mãos, face mesh), calcula os indicadores de segurança em tempo real, exibe o overlay na janela de vídeo e registra os dados no banco a cada segundo via `log_detection()`. 

**Camada 3 — Armazenamento (SQLite):** Banco de dados local `demi_data.db` com três tabelas: `detections` (registros por segundo), `sessions` (resumo por sessão) e `alerts` (alertas disparados com timestamp e descrição).

**Camada 4 — API (dashboard.py):** Servidor Flask que expõe endpoint REST `/api/data` retornando JSON com os últimos registros. Também serve a interface web do dashboard.

**Camada 5 — Visualização (Navegador):** Dashboard em HTML/CSS/JavaScript com Chart.js. Atualiza automaticamente a cada 3 segundos via polling HTTP. Duas abas: "Detecções" e "Segurança Industrial".

**Camada 6 — Exportação (CSV):** O operador pode pressionar `E` a qualquer momento para exportar os dados em formato CSV para a pasta `exports/`, gerando os três arquivos de dataset.

---

## 4. Comunicação Digital

A comunicação entre os componentes do sistema é baseada em **HTTP REST**, que é um protocolo de comunicação digital amplamente usado na Indústria 4.0.

O fluxo funciona assim: o `demi.py` age como produtor de dados, escrevendo continuamente no banco SQLite. O `dashboard.py` age como consumidor, lendo esse banco via SQL e expondo os dados como API JSON no endpoint `/api/data`. O navegador, por sua vez, chama esse endpoint a cada 3 segundos (polling HTTP), mantendo o dashboard atualizado.

Comparando com protocolos industriais: o MQTT seria mais eficiente para comunicação em tempo real em redes de IoT (publish/subscribe, menor latência), mas para o nosso caso de uso — monitoramento local com atualização a cada 3 segundos — o HTTP polling cumpre a função de forma equivalente e mais simples de implementar. Na prática, o resultado visual para o usuário é o mesmo.

O endpoint principal retorna um objeto JSON com arrays de dados das últimas sessões, estatísticas agregadas (total de detecções, alertas por tipo, FPS médio) e o **Safety Score** calculado automaticamente pelo backend com base nos alertas recentes.

---

## 5. Dashboard e Visualização

O dashboard foi desenvolvido com **Flask** no backend e **Chart.js** no frontend, acessível em `http://localhost:5000`. Ele tem duas abas principais:

**Aba 1 — Detecções:** Mostra KPIs gerais como total de frames processados, taxa de detecção de pose, taxa de detecção de rosto, FPS médio e contagem de mãos. Inclui gráficos de linha com o histórico de FPS, gráfico de barras com a distribuição de `fingers_count` e um gráfico temporal de detecções ao longo da sessão.

**Aba 2 — Segurança Industrial:** Painel focado nos alertas. Exibe o **Safety Score** (de 0 a 100, calculado com base nos alertas das últimas horas), tabela de alertas recentes com timestamp e severidade, gráfico de pizza com a distribuição dos tipos de alerta e histograma de alertas por hora do dia.

No total são **6 gráficos**, todos atualizados em tempo real via JavaScript. A tabela de alertas exibe as últimas 50 ocorrências em ordem cronológica reversa.

---

## 6. Os 12 Filtros de Segurança Industrial

O DEMI implementa 12 filtros independentes de monitoramento. Cada um analisa os landmarks do MediaPipe e dispara alertas quando um padrão de risco é detectado:

| # | Filtro | Técnica Usada | Risco Detectado |
|---|---|---|---|
| 1 | Sonolência (drowsiness) | EAR — Eye Aspect Ratio | Olhos semifechados por mais de 2s |
| 2 | Bocejo (yawn) | MAR — Mouth Aspect Ratio | Boca muito aberta (fadiga) |
| 3 | Distração (distraction) | Ângulo yaw da cabeça (face landmarks) | Cabeça virada lateralmente |
| 4 | Piscadas/Fadiga (blink_rate) | Frequência de EAR < limiar | Taxa de piscadas abaixo do normal |
| 5 | Cabeça baixa (head_down) | Ângulo pitch do nariz vs ombros | Cabeça inclinada para frente |
| 6 | Postura dos ombros (posture) | Diferença de altura entre ombros | Ombros assimétricos/inclinados |
| 7 | Inclinação do tronco (trunk_lean) | Vetor quadril-ombro vs vertical | Torso inclinado lateralmente |
| 8 | Braços elevados (arms_up) | Posição Y dos pulsos vs ombros | Pulso acima do nível do ombro |
| 9 | Agachamento (squat) | Ângulo do joelho (quadril-joelho-tornozelo) | Joelho em flexão acentuada |
| 10 | Queda (fall) | Desaparecimento abrupto da pose | Pessoa sai do quadro subitamente |
| 11 | Inatividade (inactivity) | Velocidade média dos pulsos < limiar | Mãos paradas por mais de 10s |
| 12 | Velocidade excessiva (hand_speed) | Velocidade dos pulsos > limiar | Movimentos bruscos de mão |

**EAR (Eye Aspect Ratio):** Razão entre as distâncias verticais e horizontais dos pontos dos olhos. Quando o olho fecha, a distância vertical cai, reduzindo o EAR. Valor abaixo de ~0.25 por mais de 2 segundos consecutivos indica sonolência.

**MAR (Mouth Aspect Ratio):** Mesmo princípio aplicado à boca. Valor acima de ~0.6 indica abertura elevada (bocejo).

---

## 7. Coleta de Dados — 7 Dias

A coleta foi realizada em ambiente de laboratório/sala de aula, durante o período de **14/03/2026 a 20/03/2026**, totalizando sete dias consecutivos.

| Métrica | Valor |
|---|---|
| Total de registros coletados | **11.260** |
| Total de sessões | **27** |
| Total de alertas disparados | **408** |
| FPS médio geral | **26,5** |
| Taxa média de detecção de pose | **88,2%** |
| Taxa média de detecção de rosto | **89,1%** |
| Período | 14/03/2026 a 20/03/2026 |

Todos os arquivos do projeto estão disponíveis na pasta do Google Drive da equipe:

📁 **[Acesse a pasta completa do projeto no Google Drive](https://drive.google.com/drive/folders/1lxLwyeiMIu-eIh7HvVcQnbCQTCezkQzs?usp=sharing)**

A pasta contém:
- **Dataset bruto** — os três arquivos `.csv` de coleta (`detections_dataset.csv`, `alerts_dataset.csv`, `sessions_dataset.csv`)
- **Vídeo de demonstração** — gravação do protótipo funcionando em tempo real, com narração da equipe
- **Código-fonte completo** — todos os arquivos do projeto para execução local (`demi.py`, `dashboard.py`, `iniciar_demi.bat`, `requirements.txt`)
- **Capturas de tela** — screenshots do dashboard e da câmera com overlay de detecção

O dataset inclui três arquivos:
- `detections_dataset.csv` — registro por segundo de todas as variáveis de detecção
- `alerts_dataset.csv` — log completo de todos os alertas disparados
- `sessions_dataset.csv` — resumo por sessão com total de frames e detecções

---

## 8. Análise dos Dados Coletados

### Resumo por Dia

| Data | Dia | Sessões | Registros | Alertas | FPS Médio |
|---|---|---|---|---|---|
| 14/03/2026 | Segunda | 5 | 2.600 | 95 | 26,4 |
| 15/03/2026 | Terça | 5 | 2.530 | 91 | 26,5 |
| 16/03/2026 | Quarta | 4 | 1.810 | 65 | 26,5 |
| 17/03/2026 | Quinta | 4 | 1.740 | 63 | 26,6 |
| 18/03/2026 | Sexta | 3 | 1.130 | 41 | 26,5 |
| 19/03/2026 | Sábado | 3 | 720 | 27 | 26,4 |
| 20/03/2026 | Domingo | 3 | 730 | 26 | 26,5 |
| **Total** | | **27** | **11.260** | **408** | **26,5** |

### Interpretação

Os dias de semana concentraram a maior parte da coleta. Segunda e terça-feira juntas somaram 5.130 registros — quase metade do total dos sete dias. Isso reflete um padrão de uso típico: início de semana com mais atividade, decaindo progressivamente até o fim de semana. A média de duração por sessão nos dias úteis ficou em torno de **8 minutos**, enquanto nos finais de semana foi de aproximadamente **4 minutos**.

Em termos de alertas, os mais frequentes foram de **postura** (91 ocorrências, 22,3%), seguidos por **distração** (72, 17,6%) e **cabeça baixa** (71, 17,4%). Isso faz sentido para um ambiente de trabalho com computador: a postura tende a piorar ao longo da sessão, e distrações laterais são comuns em salas compartilhadas. O fato do filtro de distração ter sido o segundo mais acionado sugere que o ambiente de coleta tinha estímulos visuais laterais — outras pessoas passando, janelas, etc.

A **sonolência** apareceu 31 vezes (7,6%), com concentração maior nas sessões da tarde, especialmente depois das 14h. Esse padrão é coerente com a queda fisiológica de atenção no período pós-almoço. Os alertas de sonolência têm severidade `danger`, o que os torna prioritários no Safety Score.

O **Safety Score** médio das sessões da tarde ficou visivelmente abaixo das manhãs, puxado pelos alertas de sonolência e bocejo. Nas manhãs do início da semana, o score estava acima de 85; nas tardes de quinta-feira, chegou a cair para a faixa dos 70.

Quanto ao FPS, a variação foi pequena ao longo dos dias — média de 26,5 com desvio padrão baixo. Houve quedas pontuais abaixo de 20 FPS em momentos com os três módulos simultaneamente ativos (pose + mãos + rosto), especialmente em máquinas com CPU mais carregada. Isso é esperado: o MediaPipe é computacionalmente intenso quando usa os três pipelines juntos.

Durante todo o período de coleta, **zero alertas de queda** foram registrados (filtro `fall`), o que confirma que o ambiente era controlado e seguro. Também não houve alertas do tipo `critical` — todos os eventos de risco ficaram na faixa de `warning` ou `danger`.

---

## 9. Relação com os Pilares da Indústria 4.0

| Pilar | Como o DEMI aplica |
|---|---|
| **Internet das Coisas (IoT)** | A webcam funciona como dispositivo de sensoriamento conectado. O dashboard acessa os dados via HTTP, simulando uma arquitetura de IoT local. Em uma expansão, o demi.py poderia enviar dados via MQTT para um broker central. |
| **Big Data e Análise de Dados** | O sistema coleta ~1 registro por segundo de forma contínua, gerando datasets com milhares de entradas. Os dados são estruturados (CSV, SQLite) e prontos para análise estatística. O dashboard faz agregações em tempo real. |
| **Computação em Nuvem** | Atualmente o processamento é local, mas toda a arquitetura foi projetada para migrar facilmente: o banco SQLite pode ser substituído por PostgreSQL/MySQL em nuvem, e a API Flask pode rodar em um container Docker num servidor remoto. |
| **Inteligência Artificial** | O coração do sistema é IA: o MediaPipe usa redes neurais para detectar pose, mãos e rosto. Os filtros de segurança aplicam algoritmos geométricos sobre os resultados dos modelos. |
| **Cibersegurança** | Os dados coletados incluem imagens e informações biométricas (posição corporal, expressão facial). O sistema mantém tudo local e não transmite dados para servidores externos, preservando a privacidade do monitorado. |

---

## 10. Conclusão

O projeto demonstrou que é possível construir um sistema funcional de monitoramento ergonômico e de segurança industrial usando apenas uma webcam comum e software open source. Durante os sete dias de coleta, o DEMI registrou 11.260 entradas, disparou 408 alertas e manteve uma taxa de detecção de pose de 88,2% — números que mostram que o sistema é estável e relativamente confiável.

As principais limitações identificadas durante o desenvolvimento são:

**Dependência de iluminação:** o MediaPipe perde precisão em ambientes com pouca luz ou iluminação lateral forte. Em alguns testes noturnos, a taxa de detecção caiu visivelmente.

**Ângulo da câmera:** o sistema funciona melhor com a câmera na altura dos olhos, frontal ao usuário. Câmeras posicionadas de lado ou muito acima perdem pontos de landmark importantes, especialmente os ombros.

**Consumo de CPU:** com os três módulos ativos simultaneamente, o processo consome bastante CPU. Em máquinas mais antigas, o FPS cai abaixo de 20, o que impacta a fluidez do overlay e pode atrasar levemente o disparo de alertas.

**Compatibilidade de dependências:** durante o desenvolvimento, a equipe teve um problema com a versão do NumPy. A versão 2.x quebrou a compatibilidade com o MediaPipe, causando erro na inicialização. A solução foi fixar `numpy<2` no arquivo de dependências — o que está documentado no `requirements.txt`.

Em termos de possibilidades futuras, a gente enxerga algumas expansões naturais para o projeto:

- Integração com um **ESP32** para disparar um alarme sonoro quando um alerta de sonolência ou queda for detectado, adicionando uma camada de resposta física ao sistema
- Envio dos dados via **MQTT** para um broker central (ex: Mosquitto), permitindo monitorar múltiplos postos de trabalho em tempo real
- Treinamento de modelos customizados para detectar EPIs (capacete, colete, luvas) usando o feed de câmera — expandindo o escopo de segurança industrial
- Exportação automática para planilhas ou dashboard em **Grafana**, para análise histórica mais robusta

No geral, o DEMI é um protótipo funcional que cumpriu bem o objetivo proposto: demonstrar na prática a integração de coleta de dados, comunicação digital, análise e visualização inteligente dentro do contexto da Indústria 4.0 — usando hardware acessível e tecnologias modernas de visão computacional.

---

## 11. Referências

GOOGLE. *MediaPipe: A framework for building perception pipelines*. Google LLC, 2023. Disponível em: https://mediapipe.dev. Acesso em: março de 2026.

OPENCV TEAM. *OpenCV Documentation*. OpenCV, 2024. Disponível em: https://docs.opencv.org. Acesso em: março de 2026.

PALLETS PROJECTS. *Flask Documentation*. Pallets, 2024. Disponível em: https://flask.palletsprojects.com. Acesso em: março de 2026.

SOUSA, R. V.; OLIVEIRA, M. A. *Visão Computacional Aplicada ao Monitoramento de Segurança em Ambientes Industriais*. Revista Brasileira de Automação Industrial, v. 12, n. 3, p. 45-58, 2023.

SILVA, J. F.; CARVALHO, T. M. *Indústria 4.0: Sensoriamento Inteligente e Análise de Dados em Tempo Real*. Anais do Congresso Brasileiro de Engenharia de Produção (CONBREPRO), p. 112-121, 2022.

NETO, A. R.; PIMENTEL, B. G. *Sistemas de Visão Computacional de Baixo Custo para Monitoramento Ergonômico: Uma Revisão Sistemática*. In: Simpósio Brasileiro de Automação Inteligente (SBAI), 2023.

