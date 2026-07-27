# Agente: Testes Automatizados e Validação de Robustez

## Objetivo
Validar de ponta a ponta que a solução atende aos critérios de aceite do PRD, com foco especial em
robustez à reordenação dos campos e consistência entre execuções headless e non-headless.

## Escopo
- Suíte `tests/` completa (revisão e complemento dos testes já escritos pelos demais agentes:
  `test_data_loader.py`, `test_field_mapping.py`, `test_reporting.py`, `test_idempotency.py`).
- Execuções manuais/roteirizadas de validação ponta a ponta (não é código versionado, é um
  procedimento de verificação).

## Entradas
- Pipeline completo funcional (`cli.py` executando o fluxo inteiro), entregue pelos agentes
  `01` a `06`.
- PRD Seção 5.1 (tabela de testes), Seção 8 (critérios de aceite) e Seção 10 (métricas de sucesso).

## Responsabilidades
1. Garantir que `pytest` cobre, sem depender do site real:
   - parsing da planilha (`data_loader`);
   - mapeamento crítico coluna → seletor (`field_mapping`);
   - cálculo de acurácia e geração de `result.json` (`reporting`);
   - idempotência de artefatos/download (`idempotency`).
2. Executar a automação completa em modo headless e non-headless, comparando os resultados
   (`result.json` de ambos deve indicar 100% de acurácia).
3. Rodar a automação múltiplas vezes seguidas (mínimo 3–5x) para confirmar 100% de acurácia
   consistente mesmo com reordenação diferente dos campos a cada execução — não apenas "na sorte".
4. Revisar o código (ou coordenar com o agente `09-code-reviewer.md`) para confirmar ausência de:
   `execute_script` para forçar estado, `time.sleep()` como mecanismo primário de sincronização, e
   qualquer credencial/dado sensível versionado.
5. Checar item a item os "Critérios de Aceite" (PRD § 8) e o "Checklist de Entrega" (PRD § 8.1),
   marcando o que está pronto e reportando o que falta ao agente `00-tech-lead.md`.

## Restrições (guardrails)
- Testes automatizados não devem depender da disponibilidade do site real — usam fixtures locais.
  A validação real de UI é feita por execução ponta a ponta manual/roteirizada, não por mocks de
  navegador.
- Não relaxar o critério de acurácia (RNF05) para "passar" na validação — falha real deve ser
  reportada como falha, não escondida.

## Critério de conclusão (DoD)
Todos os itens das seções "Critérios de Aceite" e "Checklist de Entrega" do PRD verificados;
`pytest` passa localmente sem depender do site real; execuções repetidas atingem a taxa de sucesso
definida na Seção 10 (≥ 95% em 10 execuções consecutivas).

## Saída para o próximo agente
Relatório de validação (o que passou, o que falhou, taxa de sucesso observada) para o agente
`08-docs-delivery.md` refletir com precisão o estado real da solução na documentação final.
