# Agente: Aquisição e Parsing de Dados

## Objetivo
Baixar a planilha de dados do RPA Challenge de forma automatizada e transformá-la em uma estrutura
de dados confiável (lista de registros) que os demais módulos possam consumir.

## Escopo
- `src/data_loader.py`.
- Configuração do diretório de download do Chrome (via `driver_factory.py`, em coordenação com o
  agente `01-project-setup.md` caso precise de ajuste).
- `tests/test_data_loader.py`.

## Entradas
- WebDriver configurado (`driver_factory.py`, entregue pelo agente `01-project-setup.md`).
- PRD Seção 4 (RF02, RF03) e Seção 5.1 (`test_data_loader.py`).

## Responsabilidades
1. Navegar até `rpachallenge.com` e localizar/clicar no botão "Download Excel".
2. Aguardar a conclusão do download com espera explícita sobre o sistema de arquivos (ex.: polling
   com `WebDriverWait`-like até o arquivo existir e não estar mais em estado `.crdownload`) — nunca
   `time.sleep()` fixo como mecanismo primário.
3. Implementar `data_loader.py`: função que lê o `.xlsx` (via pandas/openpyxl) e retorna uma lista
   de 10 registros, um dict/objeto por linha, com todas as colunas: First Name, Last Name, Company
   Name, Role in Company, Address, Email, Phone Number.
4. Definir e documentar o contrato de dados retornado (nomes de chave exatos) — este contrato é
   consumido diretamente pelo agente `03-form-automation.md` em `fill_record(record)`.
5. Tratar planilha ausente/corrompida com erro explícito e mensagem acionável (sem stack trace cru
   sem contexto).
6. Escrever `test_data_loader.py` usando uma planilha de exemplo local (fixture), sem depender do
   site real.

## Restrições (guardrails)
- **RNF01/RNF02**: sincronização com o sistema de arquivos e com o clique de download deve usar
  espera explícita, não `sleep()` fixo.
- **RNF08 (idempotência de execução)**: rodar o download duas vezes seguidas no mesmo diretório não
  pode falhar nem deixar arquivos duplicados/corrompidos que quebrem a próxima leitura.
- Não versionar a planilha baixada nem arquivos de download reais no repositório.

## Critério de conclusão (DoD)
Dado um teste local com planilha de exemplo, os 10 registros são extraídos corretamente com todas
as colunas esperadas, validado por teste unitário (`pytest tests/test_data_loader.py`).

## Saída para o próximo agente
Lista de registros (formato de dict documentado) pronta para o agente `03-form-automation.md`
mapear cada coluna para o seletor do campo correspondente no formulário.
