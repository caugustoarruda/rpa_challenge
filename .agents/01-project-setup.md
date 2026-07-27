# Agente: Setup do Projeto

## Objetivo
Deixar o repositório com a base estrutural pronta para desenvolvimento: pastas, dependências,
configuração inicial do WebDriver e documentação mínima de instalação.

## Escopo
- Estrutura de pastas: `src/`, `tests/`, `artifacts/`.
- `requirements.txt`.
- `.gitignore`.
- `src/driver_factory.py` (criação/configuração do WebDriver, incluindo suporte a `--headless`).
- Esqueleto inicial de `src/cli.py` (apenas parsing de argumentos, sem lógica de negócio ainda).
- `README.md` inicial (seção de instalação/execução).

## Entradas
- `PRD.md` Seção 6 (arquitetura técnica) e Seção 4 (RF01, RF12).
- Nenhum artefato de outro agente é necessário — este é o primeiro agente a atuar.

## Responsabilidades
1. Criar a árvore de pastas conforme a Seção 6 do PRD.
2. Escrever `requirements.txt` com versões fixadas (Selenium 4.x, pandas, openpyxl, pytest).
3. Implementar `driver_factory.py`: função que retorna um WebDriver Chrome/Chromium configurado,
   aceitando um parâmetro para modo headless e configurando diretório de download.
4. Implementar `cli.py` com `argparse`: flags `--headless` e `--output-dir` (valor padrão
   `artifacts/`), sem lógica de negócio (isso é do agente de orquestração).
5. Criar `.gitignore` cobrindo `artifacts/`, `__pycache__/`, ambiente virtual, planilha baixada e
   qualquer arquivo de download local.
6. Escrever a seção de instalação do `README.md`.

## Restrições (guardrails)
- **RNF03 (idempotência de setup)**: usar exclusivamente Selenium Manager nativo (Selenium 4.x) —
  não introduzir `webdriver-manager` nem instruções de download manual de driver.
- Não implementar lógica de navegação, preenchimento ou parsing de planilha aqui — isso pertence a
  outros agentes.

## Critério de conclusão (DoD)
`python -m src.cli --help` roda em máquina limpa; o navegador abre e fecha corretamente tanto em
modo headless quanto non-headless (validado com um smoke test manual mínimo em `driver_factory.py`,
sem lógica do desafio ainda).

## Saída para o próximo agente
Estrutura de pastas e `driver_factory.py`/`cli.py` prontos para o agente `02-data-acquisition.md`
implementar o download e parsing da planilha.
