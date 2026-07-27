# PRD — Automação RPA Challenge (rpachallenge.com)

## 1. Contexto

O [RPA Challenge](https://rpachallenge.com/) é um site de treinamento para automação que apresenta um
formulário dinâmico: a cada submissão os campos de input trocam de posição visual na tela. O desafio
fornece uma planilha (Excel) com 10 registros de dados que devem ser inseridos, um de cada vez, nos
campos corretos — mesmo que sua posição mude a cada rodada.

Este documento define o escopo, os requisitos e o plano de execução (sprints) para construir uma
automação em **Python + Selenium** que resolva o desafio de forma robusta, auditável e reprodutível.

## 2. Objetivo

Construir um script/CLI em Python que:

1. Acessa `https://rpachallenge.com/`.
2. Baixa a planilha de dados do desafio.
3. Preenche os 10 registros no formulário dinâmico com **100% de acurácia**, sem depender da posição
   visual dos campos.
4. Gera evidências do resultado (screenshot, JSON, logs) na pasta `artifacts/`.
5. É executável em uma máquina limpa com poucos comandos, em modo headless ou não-headless.

## 3. Escopo

### Dentro do escopo
- Download automatizado da planilha via botão "Download Excel" do site.
- Leitura da planilha (`.xlsx`) e mapeamento das colunas para os campos do formulário.
- Identificação de campos por atributo estável (ex.: `ng-reflect-name`, `placeholder` ou `label`
  associada) — nunca por posição/coordenadas ou índice de DOM sujeito a reordenação.
- Espera explícita (`WebDriverWait` / `expected_conditions`) para sincronizar com o DOM Angular,
  que re-renderiza os inputs entre rounds.
- Loop de preenchimento das 10 linhas, com clique em "Submit" a cada rodada.
- Tratamento de falhas com retry controlado e logging estruturado.
- Captura do resultado final: mensagem de sucesso, tempo total reportado pelo site, contagem de
  registros corretos.
- Persistência de evidências em `artifacts/`: screenshot da tela final, `result.json`, arquivo de log.
- Suporte a execução headless e non-headless via flag de CLI.
- Instruções de setup reprodutíveis (`requirements.txt`, `README.md`, script de entrypoint único).

### Fora do escopo
- Gravação de passos via Selenium IDE ou qualquer ferramenta de "record & playback".
- Manipulação direta do DOM (`execute_script` para forçar valores/estado) como atalho para "simular"
  sucesso.
- Suporte a outros desafios do site (ex.: RPA Challenge OCR, PDF) — apenas o desafio de formulário
  dinâmico padrão.
- Paralelização/múltiplas execuções simultâneas.
- Interface gráfica própria (uso é via CLI).

## 4. Requisitos Funcionais

| ID | Requisito |
|----|-----------|
| RF01 | O sistema deve navegar até `rpachallenge.com` usando um WebDriver Selenium real (Chrome/Chromium). |
| RF02 | O sistema deve clicar no botão de download e obter o arquivo Excel do desafio automaticamente. |
| RF03 | O sistema deve ler a planilha e extrair os 10 registros com suas colunas (First Name, Last Name, Company Name, Role in Company, Address, Email, Phone Number). |
| RF04 | O sistema deve clicar em "Start" para iniciar o desafio. |
| RF05 | Para cada um dos 10 registros, o sistema deve localizar cada campo do formulário por atributo estável (não por posição) e preencher com o valor correspondente. |
| RF06 | O sistema deve limpar (`clear()`) cada campo antes de preenchê-lo, evitando concatenação de valores residuais. |
| RF07 | O sistema deve clicar em "Submit" após preencher cada registro e aguardar o re-render do próximo round antes de prosseguir. |
| RF08 | Ao final dos 10 registros, o sistema deve capturar a mensagem/tela de conclusão do desafio. |
| RF09 | O sistema deve gerar um screenshot da tela final e salvá-lo em `artifacts/`. |
| RF10 | O sistema deve gerar um `result.json` em `artifacts/` contendo: status (sucesso/falha), acurácia, tempo total de execução, tempo reportado pelo site (se disponível), timestamp da execução. |
| RF11 | O sistema deve registrar logs estruturados (nível INFO/DEBUG/ERROR) de cada etapa relevante em arquivo dentro de `artifacts/` (ou `logs/`). |
| RF12 | O sistema deve aceitar um parâmetro de CLI para alternar entre modo headless e non-headless. |

## 5. Requisitos Não Funcionais

| ID | Requisito |
|----|-----------|
| RNF01 | **Robustez a reordenação**: a lógica de localização de campos não pode depender de índice de posição no DOM nem de coordenadas de tela. |
| RNF02 | **Sincronização confiável**: uso exclusivo de esperas explícitas (`WebDriverWait`); proibido uso de `time.sleep()` fixo como mecanismo primário de sincronização (permitido apenas como fallback mínimo e documentado). |
| RNF03 | **Idempotência de setup**: `pip install -r requirements.txt` + um comando de execução devem ser suficientes em uma máquina limpa (sem drivers pré-instalados manualmente — usar `webdriver-manager` ou Selenium Manager nativo). |
| RNF04 | **Legibilidade e modularidade**: separação clara entre camadas (navegação/driver, extração de dados, preenchimento de formulário, geração de artefatos, CLI). |
| RNF05 | **Reprodutibilidade**: mesma execução deve produzir 100% de acurácia de forma consistente (não só "na sorte"). |
| RNF06 | **Auditabilidade**: nenhuma manipulação de DOM para forçar estado de sucesso; todo preenchimento deve ocorrer via interação real (`send_keys`, `click`). |
| RNF07 | **Portabilidade**: compatível com Linux (ambiente de desenvolvimento atual); Chrome/Chromium como navegador alvo. |
| RNF08 | **Idempotência de execução**: rodar o script múltiplas vezes seguidas não deve falhar por causa de artefatos/downloads de execuções anteriores (arquivos são sobrescritos ou nomeados de forma segura; nenhum estado residual quebra a próxima execução). |
| RNF09 | **Dados públicos, sem segredos**: a solução não requer login, credenciais, tokens ou cookies — nada disso deve ser versionado no repositório; todos os dados usados (planilha do desafio) são públicos. |

## 5.1. Testes Automatizados

O desafio não possui API própria, então o foco de testes automatizados recai sobre as partes
determinísticas e críticas do pipeline (a interação com o navegador em si é validada por execução
real, não por mocks de UI):

| Teste | O que valida |
|-------|--------------|
| `test_data_loader.py` | Parsing correto da planilha (`.xlsx`) de exemplo para a estrutura de registros esperada; comportamento com planilha ausente/corrompida. |
| `test_field_mapping.py` | **Mapeamento crítico** coluna da planilha → seletor estável do campo do formulário (ex. `First Name` → seletor por `ng-reflect-name`), garantindo que nenhuma coluna fica sem mapeamento e que não há mapeamento ambíguo/duplicado. |
| `test_reporting.py` | Cálculo de acurácia e geração de `result.json` com os campos esperados. |
| `test_idempotency.py` | Rodar a geração de artefatos/download duas vezes seguidas no mesmo diretório não lança erro nem deixa estado inconsistente (arquivo é sobrescrito de forma previsível). |

Esses testes rodam sem depender do site real (usam fixtures locais: planilha de exemplo, HTML/JSON
de amostra), permitindo execução rápida em CI ou máquina do avaliador via `pytest`.

## 6. Arquitetura Técnica Proposta

```
rpa_challenge/
├── PRD.md
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── cli.py               # entrypoint / argparse (--headless, --output-dir, etc.)
│   ├── driver_factory.py    # criação/configuração do WebDriver (headless/non-headless)
│   ├── data_loader.py       # download da planilha + parsing (pandas/openpyxl)
│   ├── challenge_page.py    # Page Object: seletores estáveis, ações (start, fill_record, submit)
│   ├── runner.py            # orquestração do loop de 10 registros + medição de tempo/acurácia
│   ├── reporting.py         # geração de result.json, screenshot, cálculo de acurácia
│   └── logging_config.py    # configuração centralizada de logs
├── tests/
│   └── ...                  # testes unitários (parsing, mapeamento de campos, reporting)
└── artifacts/                # saída gerada em runtime (git-ignored, exceto .gitkeep)
```

**Stack**
- Python 3.11+
- Selenium 4.x (Selenium Manager cuida do driver automaticamente, sem downloads manuais)
- pandas + openpyxl (leitura da planilha)
- Padrão **Page Object Model** para isolar seletores da lógica de orquestração
- `logging` (stdlib) para logs estruturados
- `argparse` para CLI
- `pytest` para testes

**Estratégia de identificação de campos**
Os inputs do RPA Challenge são renderizados via Angular e mantêm um atributo `ng-reflect-name`
estável (correspondente ao nome da coluna, ex. `labelFirstName`, `labelLastName`, `labelEmail` etc.)
mesmo quando a posição visual do campo muda a cada round. A automação deve:
1. Mapear cada coluna da planilha para o seletor estável do campo correspondente (via XPath/CSS
   usando `ng-reflect-name`, com fallback documentado para `placeholder` caso o atributo mude).
2. Re-consultar os elementos a cada round (nunca reaproveitar referências de `WebElement` obtidas
   antes do re-render), evitando `StaleElementReferenceException`.
3. Preencher por significado, não por índice de lista de elementos.

## 7. Artefatos de Saída (`artifacts/`)

| Arquivo | Conteúdo |
|---------|----------|
| `result.json` | `{"status": "success", "records_filled": 10, "accuracy_pct": 100.0, "execution_time_seconds": ..., "site_reported_time": ..., "timestamp": "...", "headless": true/false}` |
| `final_screenshot.png` | Print da tela de conclusão do desafio (mensagem de sucesso do site). |
| `run.log` | Log completo da execução (INFO por etapa, ERROR em falhas, com timestamps). |

## 8. Critérios de Aceite

- [ ] Desafio concluído com **100% de acurácia** (10/10 registros corretos), confirmado pela
      mensagem de sucesso do próprio site.
- [ ] Execução bem-sucedida mesmo com a **reordenação visual dos campos** entre rounds (validado
      rodando múltiplas vezes, já que a ordem muda a cada execução).
- [ ] **Zero preenchimento manual** — execução ponta a ponta via um único comando.
- [ ] **Nenhuma manipulação de DOM** para simular sucesso (sem `execute_script` para setar valores
      ou disparar eventos de forma artificial).
- [ ] **Nenhuma gravação frágil de passos** (sem Selenium IDE / record-playback; toda lógica é
      código versionado e legível).
- [ ] Funciona em modo headless e non-headless via flag de CLI.
- [ ] Artefatos (`result.json`, screenshot, log) gerados corretamente em `artifacts/` a cada execução.
- [ ] Setup reprodutível em máquina limpa com `pip install -r requirements.txt` + 1 comando.

## 8.1. Checklist de Entrega

Itens exigidos para que o avaliador consiga executar, validar e entender a solução sem
ambiguidade — apenas o necessário, sem escopo adicional:

- [ ] **README** com: instalação, comando(s) de execução (headless e non-headless), decisões
      técnicas relevantes (ex. estratégia de identificação de campos, escolha de espera explícita),
      limitações conhecidas, e uso de IA no desenvolvimento (se houver, descrever brevemente onde
      foi usada — ex. geração inicial deste PRD/estrutura).
- [ ] **Código Python organizado** — estrutura modular descrita na Seção 6 (`src/`), sem lógica de
      um único desafio (RPA Challenge) misturada com scripts soltos.
- [ ] **Arquivo de dependências**: `requirements.txt` com versões fixadas o suficiente para
      reprodutibilidade.
- [ ] **Testes automatizados relevantes**: cobertura do mapeamento crítico coluna→campo e da
      idempotência da execução (ver Seção 5.1) — não é necessário testar a UI do site em si via
      mocks, já que a validação real é a execução ponta a ponta.
- [ ] **Evidências de execução**: `result.json`, `final_screenshot.png` e `run.log` gerados em
      `artifacts/` (Seção 7), suficientes para o avaliador confirmar o resultado sem precisar
      rodar novamente.
- [ ] **Nenhum dado sensível versionado**: sem credenciais, tokens, cookies, `.env` com segredos ou
      arquivos grandes desnecessários (ex. binário do navegador, planilha baixada não é obrigatória
      versionar). A solução usa exclusivamente dados públicos do próprio site do desafio.

## 9. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Mudança de atributos estáveis do site (ex. `ng-reflect-name` alterado em update do site) | Alto | Isolar seletores no `challenge_page.py` (Page Object); documentar fallback por `placeholder`/label. |
| `StaleElementReferenceException` por reuso de referência antiga após re-render | Médio | Sempre re-localizar elementos dentro do loop de cada round, com `WebDriverWait`. |
| Timing variável do site (rede/render) causando preenchimento antes do DOM estabilizar | Médio | Esperas explícitas por presença/clicabilidade do elemento, não `sleep` fixo. |
| Download do Excel falhar (bloqueio de pop-up, diretório de downloads) | Médio | Configurar diretório de download do Chrome explicitamente nas prefs do driver; validar existência do arquivo antes de prosseguir. |
| Execução headless com comportamento diferente do non-headless (viewport, downloads) | Baixo | Testar explicitamente os dois modos como parte da Definition of Done. |

## 10. Métricas de Sucesso

- Acurácia: 100% (10/10 registros).
- Taxa de sucesso em execuções repetidas: ≥ 95% em 10 execuções consecutivas (considerando variação
  de rede/render do site de terceiros).
- Tempo total de execução: registrado, sem meta rígida, mas deve ser competitivo (referência: poucos
  segundos por round).

---

## 11. Roadmap de Sprints

Sprints curtos (ciclo de 1 dia cada), adequados ao tamanho do desafio. Cada sprint tem entregável
verificável e Definition of Done (DoD) objetiva. Ao concluir uma sprint (DoD atendida), marque o
checkbox correspondente para sabermos em que parte do fluxo estamos.

### Progresso geral

- [X] Sprint 0 — Setup do projeto
- [X] Sprint 1 — Aquisição de dados
- [X] Sprint 2 — Motor de identificação e preenchimento de campos
- [X] Sprint 3 — Orquestração do loop completo
- [ ] Sprint 4 — Logging e tratamento de falhas
- [ ] Sprint 5 — Artefatos e relatório de resultado
- [ ] Sprint 6 — Testes, headless/non-headless e validação de robustez
- [ ] Sprint 7 — Documentação e entrega

### Sprint 0 — Setup do projeto (0,5 dia) — [X] Concluída
**Objetivo:** base do repositório pronta para desenvolvimento.
- [X] Estrutura de pastas (`src/`, `tests/`, `artifacts/`).
- [X] `requirements.txt` (selenium, pandas, openpyxl, pytest).
- [X] `README.md` inicial com instruções de instalação/execução.
- [X] `.gitignore` (artifacts/, __pycache__, venv, downloads locais, planilha baixada) — garante que
  nenhum artefato de execução, dado grande ou eventual arquivo local sensível seja versionado (o
  desafio não usa credenciais/tokens, apenas dados públicos).
- [X] Configuração de `driver_factory.py` com suporte a `--headless`.

**DoD:** `python -m src.cli --help` roda em máquina limpa; navegador abre e fecha corretamente em
ambos os modos.

### Sprint 1 — Aquisição de dados (0,5 dia) — [X] Concluída
**Objetivo:** obter e parsear a planilha do desafio de forma automatizada.
- [X] Navegar até o site e localizar/clicar no botão de download.
- [X] Configurar diretório de download do Chrome via preferences do driver.
- [X] Aguardar (com wait, não sleep) a conclusão do download.
- [X] `data_loader.py`: parsing do `.xlsx` para lista de dicts/objetos por registro.

**DoD:** dado um teste local, os 10 registros são extraídos corretamente com todas as colunas
esperadas, validado por teste unitário com uma planilha de exemplo.

### Sprint 2 — Motor de identificação e preenchimento de campos (1 dia) — [X] Concluída
**Objetivo:** implementar o Page Object com seletores estáveis e ação de preenchimento por round.
- Inspecionar o DOM do desafio e mapear atributo estável de cada campo → coluna da planilha.
- Implementar `challenge_page.py`: `start()`, `fill_record(record)`, `submit()`.
- Implementar espera explícita para each campo antes de interagir.
- Testar manualmente que o preenchimento acerta o campo certo mesmo após reordenação.

**DoD:** rodando 1 round manualmente (non-headless), todos os campos são preenchidos corretamente
mesmo alternando a ordem visual entre execuções.

### Sprint 3 — Orquestração do loop completo (0,5 dia) — [X] Concluída
**Objetivo:** encadear os 10 rounds até a conclusão do desafio.
- [X] `runner.py`: loop sobre os 10 registros chamando `fill_record` + `submit`.
- [X] Tratamento de `StaleElementReferenceException` / re-tentativa controlada por round.
- [X] Medição de tempo total de execução.
- [X] Captura da tela/mensagem final de sucesso do site.

**DoD:** execução ponta a ponta (download → preenchimento → submissão dos 10 registros) termina com
a mensagem de sucesso do site, sem intervenção manual.

### Sprint 4 — Logging e tratamento de falhas (0,5 dia) — [ ] Concluída
**Objetivo:** tornar a execução auditável e resiliente.
- `logging_config.py`: logger configurado com níveis e formato consistente, saída para arquivo em
  `artifacts/run.log`.
- Logs em pontos-chave: início, download concluído, cada round preenchido, submissão, conclusão,
  erros.
- Tratamento explícito de exceções esperadas (timeout, elemento não encontrado, download falho) com
  mensagens acionáveis; falha real deve abortar com código de saída não-zero.

**DoD:** ao forçar um erro (ex. seletor inválido temporário), o log aponta claramente a causa e o
processo termina com status de falha, sem travar silenciosamente.

### Sprint 5 — Artefatos e relatório de resultado (0,5 dia) — [ ] Concluída
**Objetivo:** gerar as evidências exigidas pelo desafio.
- `reporting.py`: cálculo de acurácia, captura de screenshot final, geração de `result.json`.
- Extração do tempo reportado pelo próprio site (se exposto na tela de sucesso).
- Nomeação/organização consistente dos artefatos (timestamp opcional para não sobrescrever execuções
  anteriores, se desejado).

**DoD:** após uma execução, `artifacts/` contém `result.json` válido, `final_screenshot.png` e
`run.log`, todos consistentes entre si.

### Sprint 6 — Testes, headless/non-headless e validação de robustez (0,5–1 dia) — [ ] Concluída
**Objetivo:** validar os critérios de aceite de ponta a ponta.
- Testes unitários (`pytest`) descritos na Seção 5.1: `data_loader`, **mapeamento crítico**
  coluna→campo, `reporting` e **idempotência** de artefatos/download.
- Execução completa em modo headless e non-headless — comparar resultados.
- Rodar a automação múltiplas vezes (mínimo 3–5x) para confirmar 100% de acurácia consistente mesmo
  com reordenação diferente a cada run.
- Revisão de código: garantir ausência de `execute_script` para forçar estado, ausência de
  `time.sleep` como mecanismo primário de sincronização, e ausência de credenciais/dados sensíveis
  versionados.

**DoD:** todos os itens da seção "Critérios de Aceite" e do "Checklist de Entrega" (Seção 8.1)
verificados e marcados; `pytest` passa localmente sem depender do site real.

### Sprint 7 — Documentação e entrega (0,5 dia) — [ ] Concluída
**Objetivo:** preparar o pacote final para avaliação.
- `README.md` final: pré-requisitos, instalação, comandos de execução (headless/non-headless),
  descrição dos artefatos gerados, decisões técnicas relevantes, limitações conhecidas e uso de IA
  no desenvolvimento (se houver).
- Revisão de estrutura do repositório (remoção de arquivos temporários, `.gitignore` correto,
  confirmação de que nenhum dado sensível ou arquivo grande desnecessário foi versionado).
- Commit final com histórico limpo.

**DoD:** um avaliador consegue clonar o repositório em máquina limpa, seguir o README e obter
100% de acurácia sem qualquer ajuste manual; checklist da Seção 8.1 100% concluído.

---

**Estimativa total:** ~4–5 dias de esforço (podendo ser comprimido para 1–2 dias em dedicação full-time,
dado o escopo bem delimitado do desafio).
