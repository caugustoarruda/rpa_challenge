# RPA Challenge — Automação (Python + Selenium)

Automação para o desafio [rpachallenge.com](https://rpachallenge.com/): baixa a planilha de dados
do site, preenche os 10 registros no formulário dinâmico (que reordena os campos visualmente a cada
rodada) e gera evidências da execução (screenshot, JSON de resultado e log).

> Especificação completa (requisitos, arquitetura, critérios de aceite e roadmap) em [`PRD.md`](./PRD.md).

## Status atual do projeto

**Concluído.** Todas as sprints do [roadmap](./PRD.md#11-roadmap-de-sprints) (0 a 7) foram
implementadas e validadas: pipeline ponta a ponta (download → parsing → preenchimento dos 10
registros → submissão → captura de evidências) funcionando contra o site real, com **100% de
acurácia (10/10 registros, 70/70 campos)** confirmada em múltiplas execuções, tanto headless quanto
non-headless. 58 testes automatizados (`pytest`), todos passando (dado o ambiente ter as
dependências de sistema do Chrome — ver [Pré-requisitos](#pré-requisitos)).

## Pré-requisitos

- **Python 3.11+**
- **Google Chrome ou Chromium instalado.** O binário do WebDriver (`chromedriver`) em si é resolvido
  automaticamente pelo Selenium Manager (Selenium 4.x) — não é preciso baixar/configurar o driver
  manualmente.
- **Bibliotecas de sistema do Chrome** (`libnss3`, `libnspr4` e dependências gráficas mínimas).
  Em imagens Linux mínimas (containers, WSL sem pacotes gráficos, etc.) essas libs **não** vêm
  pré-instaladas, e o Selenium Manager só baixa o binário do Chrome/`chromedriver` — não essas
  dependências de sistema. Sem elas, **qualquer execução (headless ou não) e a própria suíte de
  testes falham** com `selenium.common.exceptions.WebDriverException: ... Status code was: 127`.
  Em Debian/Ubuntu:
  ```bash
  sudo apt-get update && sudo apt-get install -y libnss3 libnspr4
  ```
  Se o erro persistir, pode ser necessário instalar também dependências gráficas adicionais do
  Chrome (`libgbm1`, `libasound2`/`libasound2t64`, `libatk-bridge2.0-0`, `libxcomposite1`,
  `libxdamage1`, `libxfixes3`, `libxrandr2`, `libgtk-3-0`), variando conforme a distribuição.
  Este foi um achado real de ambiente durante o desenvolvimento (WSL/Ubuntu sem essas libs) e é
  citado aqui explicitamente porque "máquina limpa" nem sempre significa "com essas libs gráficas
  já presentes".

## Instalação

```bash
git clone <url-do-repositorio>
cd rpa_challenge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Como executar

```bash
# Execução visível (navegador aberto), útil para acompanhar o preenchimento
python -m src.cli

# Execução headless (sem interface gráfica), útil para CI/servidor
python -m src.cli --headless

# Diretório de saída customizado (padrão: artifacts/)
python -m src.cli --output-dir artifacts/

# Timeout customizado (segundos) para cada espera explícita: download,
# campos do formulário e mensagem de conclusão (padrão: 30)
python -m src.cli --timeout 30
```

Ver todas as opções: `python -m src.cli --help`.

Ao final da execução:
- O terminal exibe um resumo (status, acurácia, tempo total) via log em nível INFO.
- Os artefatos ficam disponíveis em `artifacts/` (ver seção abaixo).
- Um código de saída `0` indica sucesso; qualquer valor diferente de `0` indica falha (consulte
  `artifacts/run.log` para a causa — exceções de domínio como timeout, elemento não encontrado ou
  download/parsing falho são logadas com contexto antes do processo abortar).

## Estrutura do projeto

```
rpa_challenge/
├── PRD.md                   # especificação completa do desafio
├── README.md                # este arquivo
├── requirements.txt         # dependências fixadas
├── src/
│   ├── cli.py                # entrypoint / argparse (--headless, --output-dir, --timeout)
│   ├── driver_factory.py     # criação/configuração do WebDriver (headless/non-headless)
│   ├── data_loader.py        # download da planilha do desafio + parsing (.xlsx)
│   ├── challenge_page.py     # Page Object: seletores estáveis e ações (start, fill_record, submit)
│   ├── runner.py              # orquestração do loop dos 10 registros + retry
│   ├── reporting.py           # cálculo de acurácia, screenshot, result.json
│   └── logging_config.py     # configuração centralizada de logs
├── tests/                    # testes automatizados (pytest)
└── artifacts/                # saída gerada em runtime (não versionado, ver abaixo)
```

## Artefatos gerados (`artifacts/`)

Gerados a cada execução (sucesso **ou** falha — em caso de falha, o `status` e a acurácia refletem
o estado parcial no momento do erro, em modo melhor-esforço):

| Arquivo | Conteúdo |
|---|---|
| `result.json` | `status` ("success"/"failure"), `records_filled`, `accuracy_pct`, `execution_time_seconds` (medido localmente via `time.monotonic()`), `site_reported_time` (extraído da mensagem de conclusão do próprio site, em segundos, ou `null` se não for possível extrair), `timestamp` (UTC, ISO 8601), `headless`. |
| `final_screenshot.png` | Captura de tela (`driver.save_screenshot`, sem manipulação de DOM) da tela no momento da conclusão/falha. |
| `run.log` | Log completo da execução (INFO por etapa relevante — download, cada round, submissão, conclusão —, WARNING/ERROR em falhas, todos com timestamp). |
| `challenge.xlsx` | Planilha baixada do site na execução mais recente (dado público do próprio desafio; não é um artefato de evidência, apenas o insumo baixado). |

Os nomes de arquivo são fixos: `result.json` e `final_screenshot.png` são sobrescritos a cada
execução (substituição atômica, ver Decisões técnicas); `run.log` é aberto em modo *append*
(acumula o histórico de execuções sucessivas no mesmo arquivo, sem duplicar handlers de logging).
Em ambos os casos, rodar o comando várias vezes seguidas não acumula arquivos duplicados nem quebra
por causa de artefatos de execuções anteriores (RNF08).

**Nota sobre versionamento:** `artifacts/` é, em geral, saída de runtime regenerada a cada execução
e por isso ignorada pelo Git — com uma exceção deliberada: `result.json`, `final_screenshot.png` e
`run.log` **são versionados** (ver `.gitignore`), contendo a evidência de uma execução real
bem-sucedida (`accuracy_pct: 100.0`), para que o avaliador possa confirmar o resultado sem precisar
rodar novamente (Seção 8.1 do PRD). Já `challenge.xlsx` (a planilha baixada) continua fora do
controle de versão, por não ser obrigatório versioná-la (Seção 8.1) e por mudar a cada execução.
Rodar o comando de execução acima sobrescreve os três arquivos com o resultado da nova execução.

## Decisões técnicas

- **Identificação de campos por atributo estável, não por posição.** O formulário é renderizado em
  Angular e embaralha a posição visual dos `<rpa1-field>` a cada rodada. Cada input mantém o
  atributo `ng-reflect-name` (ex. `labelFirstName`, `labelLastName`, `labelRole`) estável entre
  rounds — usado como seletor **primário** (`FIELD_SELECTORS` em `challenge_page.py`, fonte única de
  verdade do mapeamento coluna → seletor). Como **fallback** documentado, caso esse atributo deixe de
  existir numa atualização do site, o código localiza o `<input>` pelo texto do `<label>` irmão
  (`following-sibling::input[1]`) — nunca pelo `id`/`name` gerados aleatoriamente a cada render, que
  não são estáveis.
- **Sincronização via esperas explícitas (`WebDriverWait`/`expected_conditions`), nunca `sleep`
  fixo como mecanismo primário.** Usado para: botão "Start"/"Submit" clicável, presença de campos
  após `start()`, cada input antes de `clear()`/`send_keys()`, e visibilidade do popup de conclusão.
  A única espera por polling manual (não `WebDriverWait`, pois não há elemento DOM a esperar) é a
  conclusão do download do Excel, verificada olhando o sistema de arquivos (ausência de
  `.crdownload`/`.tmp` e presença do `.xlsx` final) — usa `time.sleep(0.25)` apenas como intervalo de
  polling entre verificações, não como espera fixa de duração pré-determinada.
- **Re-localização de elementos a cada round.** Nenhum `WebElement` é reaproveitado entre rounds;
  cada `fill_record`/`submit` consulta o DOM atual, evitando `StaleElementReferenceException` pelo
  re-render do Angular. Quando a exceção ainda assim ocorre (corrida rara entre o clique em "Submit"
  e o re-render), `runner._fill_and_submit_with_retry` refaz o round do zero, até
  `MAX_ATTEMPTS_PER_ROUND = 3` tentativas, antes de propagar o erro.
- **Page Object Model.** Todos os seletores (XPath/CSS) ficam isolados em `challenge_page.py`;
  `runner.py` apenas orquestra chamadas de alto nível (`start`, `fill_record`, `submit`,
  `wait_for_completion_message`), sem conhecer XPath/CSS.
- **Nenhuma manipulação de DOM para simular sucesso.** Toda interação ocorre via ações reais do
  Selenium (`send_keys`, `clear`, `click`); não há `execute_script` para forçar valores/estado
  (a única exceção é um comando CDP — `Page.setDownloadBehavior` — necessário só para reabilitar
  downloads de arquivo no Chrome headless, que os desabilita por padrão por segurança; não afeta o
  preenchimento do formulário em si).
- **Selenium Manager em vez de driver manual.** Elimina a necessidade de baixar/gerenciar o
  `chromedriver` manualmente (RNF03), embora não elimine a necessidade das bibliotecas de sistema do
  Chrome em si (ver Pré-requisitos).
- **Idempotência de execução (RNF08) tratada em três frentes:** `data_loader` limpa
  `.xlsx`/`.crdownload`/`.tmp` remanescentes antes de cada download e renomeia o resultado para um
  nome fixo (`challenge.xlsx`); `reporting` grava `result.json` de forma atômica (arquivo temporário
  + `os.replace`) e usa nomes fixos para screenshot/JSON; `logging_config` remove handlers de
  chamadas anteriores antes de recriá-los, evitando log duplicado em reconfigurações no mesmo
  processo.
- **Tratamento de falhas em `cli.py`:** exceções de domínio esperadas (`TimeoutException`,
  `NoSuchElementException`, `StaleElementReferenceException`, `FileNotFoundError`, `ValueError`) e
  qualquer erro inesperado são logadas com contexto (`exc_info=True`), geram artefatos em modo
  melhor-esforço com `status: "failure"` (se o driver ainda estiver utilizável) e abortam com código
  de saída `1` — nunca falham silenciosamente.
- **Extração do tempo reportado pelo site é "melhor esforço".** A mensagem de conclusão real do site
  é `"Congratulations!\nYour success rate is 100% ( 70 out of 70 fields) in 4983 milliseconds"` — o
  regex de extração (`reporting.SITE_TIME_PATTERN`) reconhece tanto segundos quanto milissegundos e
  converte para segundos; a detecção **crítica** de conclusão (RF08), porém, depende apenas da
  palavra "Congratulations" (`challenge_page.COMPLETION_MESSAGE_XPATH`), não da linha de tempo —
  para não quebrar a submissão caso o site altere a redação dessa linha específica no futuro.

## Testes automatizados

```bash
pytest
```

58 testes, cobrindo as partes determinísticas do pipeline definidas na Seção 5.1 do PRD:

| Arquivo | O que valida |
|---|---|
| `tests/test_data_loader.py` | Parsing de planilha `.xlsx` de exemplo para a estrutura de registros esperada, incluindo o caso real de coluna com espaço à direita no cabeçalho (`"Last Name "`); comportamento com planilha ausente/corrompida. |
| `tests/test_field_mapping.py` | **Mapeamento crítico** coluna → seletor estável, incluindo localização correta do campo em diferentes ordens visuais simuladas, fallback por `<label>` quando `ng-reflect-name` está ausente, e cobertura/ausência de ambiguidade de `FIELD_SELECTORS`. |
| `tests/test_reporting.py` | Cálculo de acurácia e geração de `result.json` com os campos esperados, incluindo acurácia parcial. |
| `tests/test_idempotency.py` | Rodar a geração de artefatos/download duas vezes seguidas não lança erro nem deixa estado inconsistente (arquivos sobrescritos de forma previsível); reconfiguração do logger não duplica handlers. |

Nenhum teste depende de `rpachallenge.com`: os fixtures são páginas HTML locais (`file://`) ou
`about:blank`, reproduzindo apenas a estrutura de DOM observada no site real. Ainda assim, **estes
testes abrem um Chrome headless de verdade** (o projeto não usa mocks de navegador), portanto
exigem os mesmos pré-requisitos de sistema descritos acima — sem `libnss3`/`libnspr4`, os testes que
dependem de um `WebDriver` real falham com o mesmo erro `Status code was: 127`, não por um defeito
no código.

## Limitações conhecidas

- **Dependência de site de terceiros.** O comportamento observado (estrutura do DOM, atributo
  `ng-reflect-name`, redação da mensagem de conclusão) reflete `rpachallenge.com` no momento do
  desenvolvimento; mudanças estruturais no site podem exigir ajuste dos seletores em
  `challenge_page.py` (mitigado parcialmente pelo fallback por `<label>`, mas não testado contra uma
  mudança real do site).
- **Bibliotecas de sistema do Chrome não são resolvidas automaticamente.** Diferente do
  `chromedriver` (via Selenium Manager), `libnss3`/`libnspr4`/dependências gráficas do Chrome
  precisam existir previamente no SO — ver Pré-requisitos. Esta é uma limitação real observada
  durante o desenvolvimento (ambiente WSL/Ubuntu sem essas libs), não apenas hipotética.
  Sem elas, **nem a execução nem o `pytest` funcionam**, pois vários testes sobem um Chrome headless
  real.
- **Testado em Linux (Ubuntu/WSL) com Google Chrome.** Outros sistemas operacionais/navegadores não
  fazem parte do escopo validado, embora `driver_factory.py` não contenha código específico de SO.
- **Sem paralelização.** O desafio é resolvido em uma única sessão de navegador por vez, por
  simplicidade — não há suporte a múltiplas execuções simultâneas (fora do escopo do PRD).
- **Tempo reportado pelo site (`site_reported_time`) depende do formato exato da mensagem de
  conclusão.** Se o site remover a linha de "success rate"/tempo ou mudar sua unidade para além de
  segundos/milissegundos, o campo volta a ser `null` (comportamento esperado, não uma falha da
  automação — ver Decisões técnicas).
- **Retry limitado a `StaleElementReferenceException`.** Outras falhas transitórias (ex. lentidão de
  rede pontual) não têm retry dedicado; dependem do timeout configurável (`--timeout`) ser
  suficiente.

## Uso de IA

Este projeto foi construído com apoio do [Claude Code](https://claude.com/claude-code) (Anthropic)
ao longo de todo o ciclo, de forma assistida e revisada pelo autor, não autônoma/sem supervisão:

- Elaboração inicial do `PRD.md` (escopo, requisitos, arquitetura proposta e roadmap de sprints) a
  partir da descrição do desafio fornecida pelo autor.
- Estrutura inicial do repositório (`src/`, `tests/`, `requirements.txt`, `.gitignore`) na Sprint 0.
- Implementação dos módulos de `src/` e dos testes em `tests/`, sprint a sprint, seguindo as
  decisões técnicas documentadas no PRD e neste README.
- Validação contra o site real (Sprint 6), incluindo a identificação e correção de dois bugs
  encontrados apenas na execução real (coluna de planilha com espaço no cabeçalho; extração de
  tempo do site em milissegundos) e a identificação do pré-requisito de bibliotecas de sistema do
  Chrome documentado acima.
- Esta própria documentação final (README, Sprint 7).

Todo o código gerado foi revisado, testado (58 testes automatizados + execuções reais repetidas
contra `rpachallenge.com`) e validado pelo autor antes da entrega; nenhuma parte da solução usa
gravação de passos (Selenium IDE/record-playback) ou manipulação de DOM para simular sucesso.

## Dados e segurança

A solução não requer login, credenciais, tokens ou cookies — utiliza exclusivamente dados públicos
disponibilizados pelo próprio site do desafio (planilha de exemplo, baixada a cada execução).
Nenhum segredo, `.env` ou credencial é versionado neste repositório.
