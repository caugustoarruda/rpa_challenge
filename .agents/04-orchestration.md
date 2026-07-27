# Agente: Orquestração do Loop de Execução

## Objetivo
Encadear a aquisição de dados, o preenchimento round-a-round e a submissão até a conclusão dos 10
registros, do início ao fim, sem intervenção manual.

## Escopo
- `src/runner.py`.
- Integração entre `data_loader.py`, `challenge_page.py` e `driver_factory.py`.

## Entradas
- `data_loader.py` funcional (agente `02-data-acquisition.md`).
- `challenge_page.py` com `start()`, `fill_record(record)`, `submit()` funcionais (agente
  `03-form-automation.md`).
- PRD Seção 4 (RF07, RF08) e Seção 9 (risco de `StaleElementReferenceException`).

## Responsabilidades
1. Implementar `runner.py`: função de orquestração que
   - chama `start()`,
   - itera sobre os 10 registros retornados por `data_loader.py`,
   - para cada um: `fill_record(record)` → `submit()` → aguarda (espera explícita) o re-render do
     próximo round antes de prosseguir,
   - após o último registro, aguarda e captura a tela/mensagem final de sucesso do site.
2. Tratar `StaleElementReferenceException` com retry controlado por round (número máximo de
   tentativas definido e documentado, não um loop infinito).
3. Medir o tempo total de execução (início do desafio até a mensagem de conclusão).
4. Expor uma função de entrada única e clara que `cli.py` possa chamar (ex. `run(output_dir,
   headless)`), retornando os dados necessários para os agentes de logging e relatório (status,
   tempo, elementos capturados).

## Restrições (guardrails)
- **RNF01/RNF02**: reforça as mesmas restrições do agente `03-form-automation.md` no nível do loop
  — nunca reutilizar referência de elemento de round anterior, nunca `sleep()` fixo entre rounds.
- Não duplicar lógica de seletor aqui — qualquer localização de elemento passa por
  `challenge_page.py`. `runner.py` só orquestra chamadas.
- Não implementar geração de `result.json`/screenshot/log aqui — apenas captura os dados brutos
  necessários (ex. mensagem final, tempo) e delega a persistência aos agentes `05` e `06`.

## Critério de conclusão (DoD)
Execução ponta a ponta (download → preenchimento → submissão dos 10 registros) termina com a
mensagem de sucesso do site, sem intervenção manual.

## Saída para o próximo agente
`runner.py` retornando um objeto/dict com status, tempo de execução, mensagem final capturada e
contagem de registros preenchidos, para os agentes `05-logging-resilience.md` (logs durante a
execução) e `06-reporting-evidence.md` (artefatos ao final).
