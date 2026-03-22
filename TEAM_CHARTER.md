# Team Charter — Projeto DEMI

---

## 1. Identificação da Equipe

| Campo | Informação |
|-------|------------|
| **Nome da Equipe** | Data Stick |
| **Curso** | Engenharia de Software |
| **Disciplina** | _(Indústria 4.0) |

### Integrantes

| Nome | RA | Função na Equipe |
|------|----|------------------|
| João Pedro Carvalho Freitas | 769667 | / Desenvolvedor secundario |
| Arthur Argeri Zilio | 839601 | Desenvolvedor principal |
| Gustavo Henrique | 840899 | Responsável por testes e apresentação |

---

## 2. Descrição do Problema (Indústria 4.0)

Na Indústria 4.0, a **visão computacional** é uma das tecnologias-chave para automação inteligente. Sistemas de reconhecimento de pose, gestos e identificação facial são utilizados em:

- **Segurança industrial**: monitoramento de postura de operadores para prevenir lesões
- **Controle de qualidade**: inspeção visual automatizada em linhas de produção
- **Interfaces homem-máquina**: controle de equipamentos por gestos sem contato físico
- **Monitoramento de EPIs**: detecção automática de uso de equipamentos de proteção

O problema abordado é a criação de um sistema de visão computacional em tempo real capaz de detectar e rastrear o corpo humano (esqueleto, mãos e rosto) usando apenas uma webcam comum, sem necessidade de sensores especializados. Além da detecção, o sistema realiza **coleta contínua de dados** em banco de dados SQLite, **exportação para CSV** e **visualização em dashboard web** com KPIs em tempo real — integrando sensoriamento, transmissão, análise e visualização inteligente.

O sistema também implementa **12 filtros de segurança industrial** que monitoram continuamente o trabalhador em tempo real:

| # | Filtro | Técnica | Risco Detectado |
|---|--------|---------|-----------------|
| 1 | Sonolência | EAR (Eye Aspect Ratio) | Olhos fechados por tempo prolongado |
| 2 | Bocejo | MAR (Mouth Aspect Ratio) | Boca aberta demais → fadiga |
| 3 | Distração | Desvio nariz-olhos | Cabeça virada, não olhando pra frente |
| 4 | Piscadas/Fadiga | Frequência de piscadas | Taxa anormal (>25/min ou <5/min) |
| 5 | Cabeça baixa | Posição Y do nariz | Olhando pra baixo (celular, cochilo) |
| 6 | Postura ombros | Ângulo shoulder tilt | Ombros desalinhados / curvado |
| 7 | Inclinação tronco | Desvio ombro-quadril | Tronco inclinado pra frente (coluna) |
| 8 | Braços elevados | Comparação punho-ombro Y | Braços acima dos ombros por tempo |
| 9 | Agachamento | Ângulo dos joelhos | Joelhos flexionados demais |
| 10 | Queda | Desaparecimento da pose | Pose some de repente → possível queda |
| 11 | Inatividade | Movimento das mãos | Mãos paradas por mais de 10s |
| 12 | Velocidade excessiva | Deslocamento/frame | Mãos movendo rápido demais (pressa) |

---

## 3. Objetivo Principal do Projeto

Desenvolver um sistema de visão computacional em tempo real capaz de reconhecer e rastrear o corpo humano, mãos e rosto utilizando apenas uma webcam comum, com o objetivo de demonstrar aplicações práticas de reconhecimento de imagem na Indústria 4.0, como automação, segurança e interação homem-máquina.

O software **DEMI (Detector de Esqueleto, Mãos e Identificação facial)** utiliza **MediaPipe** e **OpenCV** para:

- Detectar pose corporal (33 pontos do esqueleto)
- Rastrear mãos e contar dedos levantados
- Detectar e mapear o rosto com malha facial (Face Mesh)
- **Monitorar 12 filtros de segurança industrial** (sonolência, bocejo, distração, piscadas, cabeça baixa, postura, tronco, braços, agachamento, queda, inatividade, velocidade)
- **Gerar alertas em tempo real** com banners visuais e registro em banco de dados
- **Coletar dados de detecção automaticamente** a cada segundo em banco SQLite
- **Exportar dataset bruto para CSV** para análise
- **Dashboard web com KPIs em tempo real** (Flask + Chart.js via HTTP) — com aba dedicada de Segurança Industrial mostrando contagens de alertas por tipo, gráficos e tabela de alertas
- Oferecer gravação de vídeo e screenshots

---

## 4. Responsabilidades de Cada Membro

### João Pedro Carvalho Freitas — Líder / Desenvolvedor Principal
- Coordenar a equipe e gerenciar tarefas
- Desenvolver o código principal (detecção de pose, mãos e rosto)
- Integrar os módulos do MediaPipe com OpenCV
- Revisar e aprovar alterações no código

### Arthur Argeri Zilio — Pesquisa e Documentação
- Pesquisar sobre visão computacional e Indústria 4.0
- Elaborar a documentação técnica (README, Team Charter)
- Documentar o código com comentários e docstrings
- Registrar atas de reuniões e decisões tomadas

### Gustavo Henrique — Testes e Apresentação
- Testar o software em diferentes cenários (iluminação, distância, etc.)
- Reportar e registrar bugs encontrados
- Preparar slides e material de apresentação
- Conduzir a apresentação final do projeto

---

## 5. Principais Etapas do Projeto

| # | Etapa | Descrição |
|---|-------|-----------|
| 1 | Pesquisa e planejamento | Estudo do MediaPipe, OpenCV e aplicações na Indústria 4.0 |
| 2 | Configuração do ambiente | Instalação do Python, bibliotecas e configuração do venv |
| 3 | Detecção de pose (esqueleto) | Implementação do reconhecimento corporal |
| 4 | Detecção de mãos | Rastreamento de mãos com identificação esq/dir e contagem de dedos |
| 5 | Detecção facial (Face Mesh) | Implementação da malha facial |
| 6 | Funcionalidades extras | HUD, screenshot, gravação de vídeo, troca de cores, espelhamento |
| 7 | Filtros de segurança | Implementação dos 12 filtros industriais com alertas visuais e logs |
| 8 | Dashboard de segurança | Aba de Segurança Industrial no dashboard web com KPIs por filtro |
| 9 | Testes e ajustes | Testes de performance, resolução e usabilidade |
| 10 | Documentação final | README, Team Charter e preparação da apresentação |
| 11 | Apresentação | Demonstração ao vivo do software |

---

## 6. Cronograma de Atividades

| Semana | Atividade | Responsável |
|--------|-----------|-------------|
| Semana 1 | Pesquisa + planejamento + Team Charter | Todos |
| Semana 2 | Configuração do ambiente + detecção de pose | João Pedro |
| Semana 3 | Detecção de mãos + detecção facial | João Pedro |
| Semana 4 | Funcionalidades extras (HUD, gravação, etc.) | João Pedro e Gustavo |
| Semana 5 | Testes e correções de bugs | Gustavo |
| Semana 6 | Documentação final | Arthur |
| Semana 7 | Preparação e ensaio da apresentação | Todos |
| Semana 8 | **Entrega final + apresentação** | Todos |

> _(Ajustar datas conforme o calendário da disciplina)_

---

## 7. Comunicação da Equipe

| Item | Definição |
|------|-----------|
| **Frequência de reuniões** | Semanal (toda segunda-feira) |
| **Forma de comunicação** | WhatsApp (grupo da equipe) |
| **Compartilhamento de arquivos** | GitHub + Google Drive |
| **Reuniões extraordinárias** | Conforme necessidade, combinadas pelo WhatsApp |

---

## 8. Regras de Funcionamento

### Compromissos
- Todos os integrantes devem participar ativamente das reuniões semanais
- Tarefas devem ser entregues dentro do prazo combinado
- Comunicar com antecedência caso não consiga cumprir uma tarefa
- Manter o código atualizado no repositório (GitHub)

### Tomada de Decisões
- Decisões técnicas: **consenso entre os membros**
- Em caso de impasse: **votação simples** (maioria vence)
- Decisões urgentes: **líder decide** e informa o grupo

### Resolução de Conflitos
1. Conversa direta entre os envolvidos
2. Mediação do líder da equipe
3. Se necessário, consultar o professor

---

## 9. Tecnologias e Ferramentas Utilizadas

| Categoria | Ferramenta |
|-----------|------------|
| Linguagem | Python 3.11 |
| Visão computacional | OpenCV 4.11.0 |
| Detecção corporal/facial | MediaPipe 0.10.21 |
| Banco de dados | SQLite 3 |
| Dashboard web | Flask + Chart.js |
| Comunicação digital | HTTP (API REST) |
| Exportação de dados | CSV |
| Editor de código | Visual Studio Code |
| Controle de versão | Git + GitHub |
| Comunicação da equipe | WhatsApp |
| Documentação | Markdown (README.md) |

---

## 10. Assinaturas

Ao assinar este documento, cada integrante se compromete a seguir as regras e responsabilidades definidas neste Team Charter.

| Nome | Assinatura | Data |
|------|------------|------|
| João Pedro Carvalho Freitas | _________________ | ___/___/2026 |
| Arthur Argeri Zilio | _________________ | ___/___/2026 |
| Gustavo Henrique | _________________ | ___/___/2026 |
