# Agente: Documentação e Entrega Final

## Objetivo
Preparar o pacote final para avaliação: documentação clara o suficiente para que qualquer avaliador
consiga clonar, instalar e rodar a solução sem ambiguidade, e um histórico de commits limpo.

## Escopo
- `README.md` (versão final).
- Revisão de estrutura do repositório.
- Organização do histórico de commits para entrega (sem reescrever histórico já publicado, salvo
  pedido explícito do autor).

## Entradas
- Solução completa e validada pelo agente `07-qa-testing.md`.
- PRD Seção 8.1 (Checklist de Entrega).

## Responsabilidades
1. Atualizar `README.md` com, no mínimo:
   - pré-requisitos e instalação;
   - comandos de execução (headless e non-headless);
   - descrição de cada artefato gerado em `artifacts/`;
   - decisões técnicas relevantes (estratégia de identificação de campos, escolha de espera
     explícita em vez de `sleep`, etc.);
   - limitações conhecidas;
   - uso de IA no desenvolvimento, se houver — descrever brevemente onde foi usada (ex. geração
     inicial do PRD/estrutura), sem exageros nem omissões.
2. Revisar a estrutura do repositório: remover arquivos temporários, confirmar `.gitignore`
   correto, confirmar que nenhum dado sensível ou arquivo grande desnecessário foi versionado.
3. Confirmar que o repositório, clonado do zero, permite a um avaliador seguir o README e obter
   100% de acurácia sem qualquer ajuste manual.
4. Marcar 100% do checklist de entrega da Seção 8.1 do PRD.

## Restrições (guardrails)
- **RNF09**: não versionar credenciais, tokens, cookies, `.env` com segredos.
- Documentação deve refletir o estado real do código (sem descrever funcionalidade planejada como
  se já estivesse implementada) — qualquer gap entre PRD e implementação real deve ser explicitado,
  não escondido.

## Critério de conclusão (DoD)
Um avaliador consegue clonar o repositório em máquina limpa, seguir o README e obter 100% de
acurácia sem qualquer ajuste manual; checklist da Seção 8.1 do PRD 100% concluído.

## Saída para o próximo agente
Nenhum — este é o último agente do fluxo. Reporta ao agente `00-tech-lead.md` a conclusão final do
projeto e qualquer limitação conhecida que deva ficar registrada para futuras iterações.
