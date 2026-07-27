# Agente: Logging e Tratamento de Falhas

## Objetivo
Tornar a execução auditável e resiliente: toda etapa relevante fica registrada em log, e falhas
esperadas são tratadas com mensagens acionáveis em vez de travar silenciosamente ou vazar stack
traces sem contexto.

## Escopo
- `src/logging_config.py`.
- Chamadas de log inseridas nos pontos-chave de `runner.py`, `data_loader.py` e
  `challenge_page.py` (em coordenação com os agentes donos desses módulos — este agente define o
  padrão e os pontos de instrumentação, não reescreve a lógica de negócio deles).

## Entradas
- `runner.py` funcional de ponta a ponta (agente `04-orchestration.md`).
- PRD Seção 4 (RF11) e Seção 9 (tabela de riscos e mitigações).

## Responsabilidades
1. Implementar `logging_config.py`: configuração centralizada de logger com níveis (INFO/DEBUG/
   ERROR), formato consistente (timestamp, nível, módulo, mensagem) e saída para
   `artifacts/run.log` além do console.
2. Definir os pontos-chave de log que cada módulo deve emitir: início da execução, download
   concluído, cada round preenchido, cada submissão, conclusão do desafio, e qualquer erro.
3. Tratar explicitamente as exceções esperadas listadas no PRD: timeout de espera explícita,
   elemento não encontrado, falha de download — cada uma com mensagem acionável que aponte a causa
   provável.
4. Garantir que qualquer falha real (não recuperável pelo retry do agente `04`) aborta a execução
   com código de saída não-zero em `cli.py`.

## Restrições (guardrails)
- Não silenciar exceções com `except: pass` ou equivalente — toda exceção capturada deve ser
  logada com contexto suficiente para diagnóstico.
- Não usar logging como substituto de tratamento de erro: erros que impedem a conclusão do
  desafio devem propagar e resultar em `status: "failure"` no relatório final (agente `06`), não
  apenas um log de aviso.

## Critério de conclusão (DoD)
Ao forçar um erro (ex. seletor inválido temporário), o log em `artifacts/run.log` aponta
claramente a causa e o processo termina com status de falha (código de saída não-zero), sem travar
silenciosamente.

## Saída para o próximo agente
`logging_config.py` integrado e pontos de log cobrindo todo o fluxo, para o agente
`06-reporting-evidence.md` gerar `result.json` consistente com o que foi logado.
