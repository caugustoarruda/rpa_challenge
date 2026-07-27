# Agente: Artefatos e Relatório de Resultado

## Objetivo
Gerar as evidências de execução exigidas pelo desafio: screenshot final, `result.json` e garantir
que ambos fiquem consistentes entre si e com o `run.log`.

## Escopo
- `src/reporting.py`.
- `tests/test_reporting.py`.
- `tests/test_idempotency.py` (idempotência de geração de artefatos — pode ser compartilhado com o
  agente `07-qa-testing.md`, mas a implementação da lógica idempotente é deste agente).

## Entradas
- Retorno de `runner.py` (status, tempo de execução, mensagem final capturada, contagem de
  registros) — agente `04-orchestration.md`.
- PRD Seção 4 (RF09, RF10), Seção 7 (formato exato de `result.json`) e Seção 5.1
  (`test_reporting.py`, `test_idempotency.py`).

## Responsabilidades
1. Implementar `reporting.py`:
   - captura de screenshot da tela final (`final_screenshot.png`);
   - cálculo de acurácia (`accuracy_pct`) a partir da contagem de registros corretos;
   - extração do tempo reportado pelo próprio site, se exposto na tela de sucesso;
   - geração de `result.json` no formato exato definido na Seção 7 do PRD:
     `status`, `records_filled`, `accuracy_pct`, `execution_time_seconds`, `site_reported_time`,
     `timestamp`, `headless`.
2. Nomear/organizar os artefatos de forma consistente, sobrescrevendo execuções anteriores de forma
   previsível (sem acumular lixo em `artifacts/` a cada run).
3. Escrever `test_reporting.py`: valida cálculo de acurácia e geração de `result.json` com os
   campos esperados, usando dados simulados (sem depender do site real).
4. Escrever `test_idempotency.py`: rodar a geração de artefatos duas vezes seguidas no mesmo
   diretório não lança erro nem deixa estado inconsistente.

## Restrições (guardrails)
- **RNF08**: geração de artefatos deve ser idempotente — reexecuções sucessivas sobrescrevem de
  forma segura, nunca corrompem ou deixam artefatos parciais.
- `result.json` deve refletir exatamente o que aconteceu na execução (não arredondar/otimizar
  acurácia; se o site reportar falha, `status` deve ser `"failure"`, nunca forçado para `"success"`
  para "passar" na entrega).

## Critério de conclusão (DoD)
Após uma execução, `artifacts/` contém `result.json` válido, `final_screenshot.png` e `run.log`,
todos consistentes entre si. `pytest tests/test_reporting.py tests/test_idempotency.py` passa.

## Saída para o próximo agente
Pipeline completo (`cli.py` → `runner.py` → `reporting.py`) gerando os três artefatos exigidos, para
o agente `07-qa-testing.md` validar de ponta a ponta contra os critérios de aceite do PRD.
