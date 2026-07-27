# Agentes especialistas — RPA Challenge

Esta pasta descreve, em texto puro e **agnóstico de ferramenta de IA**, os agentes especialistas
recomendados para construir a automação definida em [`../PRD.md`](../PRD.md). Cada arquivo é uma
especificação de papel (role spec) — não um plugin, config ou prompt engastado em um produto
específico. Pode ser usada como:

- Subagentes do Claude Code (`.claude/agents/`), copiando a descrição para um arquivo com
  frontmatter próprio.
- Custom modes / agents do Cursor, Windsurf, Cline, Aider, etc.
- Simplesmente prompts colados manualmente em qualquer chat de LLM, um por sessão/tarefa.
- Personas para revisão humana (ex.: checklist de PR) quando não há IA envolvida.

Nenhum arquivo aqui assume uma API, formato de tool-list ou sintaxe de configuração de um
fornecedor específico de IA.

## Como usar

1. Trabalhe **um agente por vez**, na ordem sugerida pelo roadmap (`PRD.md` § 11) — cada agente
   corresponde a uma ou mais sprints e assume que as anteriores foram concluídas.
2. Ao iniciar uma sessão com um agente, forneça a ele: o arquivo do agente, o `PRD.md` completo e o
   estado atual do repositório (ex. `git status`, `git log`).
3. O agente **09 (Revisor de Qualidade e Guardrails)** é transversal: pode ser invocado a qualquer
   momento (não só ao final) para validar que o código produzido pelos demais agentes respeita as
   restrições não-funcionais do PRD (RNF01–RNF09).
4. Todo agente deve recusar trabalho fora do seu escopo declarado e sinalizar explicitamente quando
   uma tarefa pedida pertence a outro agente da lista.

## Índice de agentes

| Arquivo | Papel | Sprint(s) do PRD |
|---|---|---|
| [`00-tech-lead.md`](./00-tech-lead.md) | Tech Lead / Arquiteto — coordena os demais agentes, mantém a arquitetura da Seção 6 coerente | Transversal |
| [`01-project-setup.md`](./01-project-setup.md) | Setup do projeto | Sprint 0 |
| [`02-data-acquisition.md`](./02-data-acquisition.md) | Aquisição e parsing de dados | Sprint 1 |
| [`03-form-automation.md`](./03-form-automation.md) | Motor de identificação e preenchimento de formulário | Sprint 2 |
| [`04-orchestration.md`](./04-orchestration.md) | Orquestração do loop de execução | Sprint 3 |
| [`05-logging-resilience.md`](./05-logging-resilience.md) | Logging e tratamento de falhas | Sprint 4 |
| [`06-reporting-evidence.md`](./06-reporting-evidence.md) | Artefatos e relatório de resultado | Sprint 5 |
| [`07-qa-testing.md`](./07-qa-testing.md) | Testes automatizados e validação de robustez | Sprint 6 |
| [`08-docs-delivery.md`](./08-docs-delivery.md) | Documentação e entrega final | Sprint 7 |
| [`09-code-reviewer.md`](./09-code-reviewer.md) | Revisor de qualidade e guardrails do PRD | Transversal |

## Convenção de cada arquivo de agente

Todo arquivo segue a mesma estrutura, para que qualquer ferramenta de IA (ou humano) consiga
extrair rapidamente o essencial:

- **Objetivo** — o que este agente entrega, em uma frase.
- **Escopo** — arquivos/módulos pelos quais é responsável (mapeados na Seção 6 do PRD).
- **Entradas** — o que precisa receber antes de começar (arquivos, decisões, artefatos de outro agente).
- **Responsabilidades** — lista de tarefas concretas.
- **Restrições (guardrails)** — o que este agente **nunca** deve fazer, geralmente citando o
  requisito não-funcional (RNF) do PRD que a proíbe.
- **Critério de conclusão (DoD)** — como saber que o trabalho está pronto, herdado da sprint
  correspondente do PRD.
- **Saída para o próximo agente** — o que deve ser entregue/comunicado ao encerrar.
