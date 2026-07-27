# RPA Challenge — Automação (Python + Selenium)

Automação para o desafio [rpachallenge.com](https://rpachallenge.com/): baixa a planilha de dados
do site, preenche os 10 registros no formulário dinâmico (que reordena os campos visualmente a cada
rodada) e gera evidências da execução (screenshot, JSON de resultado e log).

> Especificação completa (requisitos, arquitetura, critérios de aceite e roadmap) em [`PRD.md`](./PRD.md).

## Status atual do projeto

🚧 **Em desenvolvimento — Sprint 0 (setup) concluída, Sprint 1 (aquisição de dados) a seguir.**
A estrutura do repositório (`src/`, `tests/`, `artifacts/`), `requirements.txt`, `.gitignore` e o
esqueleto de `driver_factory.py`/`cli.py` já existem e foram validados (`python -m src.cli --help`
e abertura/fechamento do navegador em modo headless e non-headless). Os demais módulos (`data_loader`,
`challenge_page`, `runner`, `reporting`, `logging_config`) ainda são stubs — a lógica de negócio será
implementada nas próximas sprints. Este documento será atualizado a cada sprint concluída para
refletir o estado real do repositório.

Acompanhe o progresso em [`PRD.md` § 11 — Roadmap de Sprints](./PRD.md#11-roadmap-de-sprints).

## Pré-requisitos

- Python 3.11+
- Google Chrome (ou Chromium) instalado — o WebDriver é gerenciado automaticamente pelo Selenium
  Manager (Selenium 4.x), sem necessidade de baixar/configurar o driver manualmente.

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
```

Ao final da execução:
- O terminal exibe um resumo (status, acurácia, tempo total).
- Os artefatos ficam disponíveis em `artifacts/` (ver seção abaixo).
- Um código de saída `0` indica sucesso; qualquer valor diferente de `0` indica falha (consulte
  `artifacts/run.log` para a causa).

## Estrutura do projeto

```
rpa_challenge/
├── PRD.md                   # especificação completa do desafio
├── README.md                # este arquivo
├── requirements.txt         # dependências fixadas
├── src/
│   ├── cli.py                # entrypoint / argparse (--headless, --output-dir)
│   ├── driver_factory.py     # criação/configuração do WebDriver
│   ├── data_loader.py        # download da planilha do desafio + parsing (.xlsx)
│   ├── challenge_page.py     # Page Object: seletores estáveis e ações (start, fill_record, submit)
│   ├── runner.py             # orquestração do loop dos 10 registros
│   ├── reporting.py          # cálculo de acurácia, screenshot, result.json
│   └── logging_config.py     # configuração centralizada de logs
├── tests/                    # testes automatizados (pytest)
└── artifacts/                 # saída gerada em runtime (não versionado)
```

## Artefatos gerados (`artifacts/`)

| Arquivo | Conteúdo |
|---|---|
| `result.json` | Status, quantidade de registros preenchidos, acurácia (%), tempo de execução, tempo reportado pelo site, timestamp, modo (headless/non-headless). |
| `final_screenshot.png` | Captura de tela da mensagem de conclusão do desafio. |
| `run.log` | Log completo da execução (etapas, avisos e erros, com timestamps). |

## Decisões técnicas

- **Identificação de campos por atributo estável, não por posição.** O formulário do desafio é
  renderizado em Angular e embaralha a posição visual dos inputs a cada rodada. Os campos são
  localizados por atributo estável associado ao seu significado (ex. `ng-reflect-name`), com
  fallback documentado para `placeholder`/label — nunca por índice de DOM ou coordenadas de tela.
- **Sincronização via esperas explícitas.** Toda interação aguarda condições reais do DOM
  (`WebDriverWait` / `expected_conditions`), evitando `time.sleep()` fixo como mecanismo primário de
  sincronização — necessário porque o tempo de re-render entre rounds varia.
- **Page Object Model.** Seletores ficam isolados em `challenge_page.py`, separados da orquestração
  (`runner.py`), facilitando manutenção caso o site mude atributos no futuro.
- **Nenhuma manipulação de DOM para simular sucesso.** Toda interação ocorre via ações reais do
  Selenium (`send_keys`, `click`); não há uso de `execute_script` para forçar valores/estado.
- **Selenium Manager em vez de driver manual.** Elimina a necessidade de baixar/gerenciar o
  ChromeDriver manualmente, tornando o setup reprodutível em máquina limpa.

## Testes automatizados

```bash
pytest
```

Cobrem principalmente as partes determinísticas do pipeline (não dependem do site real):
- Parsing da planilha (`data_loader`).
- **Mapeamento crítico** coluna da planilha → seletor do campo do formulário.
- Cálculo de acurácia e geração de `result.json` (`reporting`).
- **Idempotência**: reexecuções sucessivas não falham nem deixam artefatos/downloads em estado
  inconsistente.

## Limitações conhecidas

- Depende da disponibilidade e do comportamento atual de `rpachallenge.com` (site de terceiros);
  mudanças estruturais no site podem exigir ajuste dos seletores em `challenge_page.py`.
- Testado em ambiente Linux com Google Chrome; outros navegadores/SOs não são cobertos pelo escopo
  atual.
- Não há paralelização de execuções — o desafio é resolvido em uma única sessão de navegador por
  vez, por simplicidade.

## Uso de IA

Este PRD e a documentação inicial (README) foram elaborados com apoio do Claude Code (Anthropic) a
partir da descrição do desafio fornecida pelo autor. Toda a implementação do código de automação
segue as decisões técnicas documentadas acima e é revisada e validada pelo autor antes da entrega.

## Dados e segurança

A solução não requer login, credenciais, tokens ou cookies — utiliza exclusivamente dados públicos
disponibilizados pelo próprio site do desafio (planilha de exemplo). Nenhum segredo é versionado
neste repositório.
