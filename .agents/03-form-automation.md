# Agente: Motor de Identificação e Preenchimento de Formulário

## Objetivo
Implementar o Page Object do desafio: localizar cada campo do formulário dinâmico por atributo
estável (não por posição visual) e prover as ações de `start`, `fill_record` e `submit`.

## Escopo
- `src/challenge_page.py`.
- Mapa coluna da planilha → seletor estável do campo (documentado dentro do próprio módulo).
- `tests/test_field_mapping.py`.

## Entradas
- Contrato de dados de `data_loader.py` (chaves exatas dos registros), entregue pelo agente
  `02-data-acquisition.md`.
- PRD Seção 4 (RF04, RF05, RF06), Seção 6 ("Estratégia de identificação de campos") e Seção 9
  (riscos relacionados a `ng-reflect-name` e `StaleElementReferenceException`).

## Responsabilidades
1. Inspecionar o DOM real do desafio e identificar o atributo estável de cada input (ex.
   `ng-reflect-name`), documentando um fallback por `placeholder`/label caso o atributo mude.
2. Implementar `challenge_page.py` como Page Object, isolando todos os seletores (XPath/CSS) da
   lógica de orquestração:
   - `start()` — clica no botão de início do desafio.
   - `fill_record(record)` — para cada campo, localiza o elemento por atributo estável, `clear()`
     antes de preencher e usa `send_keys()`; nunca reaproveita `WebElement` obtido em round anterior.
   - `submit()` — clica em "Submit".
3. Toda espera antes de interagir com um elemento deve ser explícita (`WebDriverWait` +
   `expected_conditions`), nunca `sleep()` fixo como mecanismo primário.
4. Construir e manter o mapa coluna → seletor num único lugar, sem duplicação, garantindo que
   nenhuma coluna fica sem mapeamento e que não há mapeamento ambíguo/duplicado.
5. Escrever `test_field_mapping.py` cobrindo esse mapeamento (o "mapeamento crítico" citado na
   Seção 5.1 do PRD) usando fixtures de HTML/JSON locais — sem depender do site real.
6. Validar manualmente (non-headless) que um round de preenchimento acerta o campo certo mesmo após
   a reordenação visual entre execuções.

## Restrições (guardrails)
- **RNF01**: proibido usar índice de posição no DOM ou coordenadas de tela para identificar campos.
- **RNF06**: proibido usar `execute_script` para setar valores ou disparar eventos artificialmente
  — toda interação é via `send_keys`/`click` reais.
- **RNF02**: proibido `time.sleep()` fixo como mecanismo primário de sincronização (permitido
  apenas como fallback mínimo e documentado, se estritamente necessário).
- Não implementar o loop de 10 rounds nem a medição de tempo total — isso é do agente
  `04-orchestration.md`. Este agente entrega apenas as ações de um único round.

## Critério de conclusão (DoD)
Rodando 1 round manualmente (non-headless), todos os campos são preenchidos corretamente mesmo
alternando a ordem visual entre execuções. `pytest tests/test_field_mapping.py` passa sem depender
do site real.

## Saída para o próximo agente
`challenge_page.py` com `start()`, `fill_record(record)` e `submit()` prontos e testados
individualmente, para o agente `04-orchestration.md` encadear os 10 rounds.
