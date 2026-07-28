"""Orquestração do loop completo dos 10 registros do desafio.

Este módulo apenas encadeia chamadas já implementadas em `challenge_page.py`
(Page Object) e `data_loader.py` (download/parsing da planilha) — nenhuma
lógica de seletor, XPath ou parsing de planilha vive aqui (RNF04). O fluxo
de alto nível é o descrito no PRD (RF07, RF08, Seção 9):

    start() -> N rounds de fill_record()/submit() -> mensagem de conclusão

com medição de tempo total e retry controlado por round para
`StaleElementReferenceException`.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.remote.webdriver import WebDriver

from src.challenge_page import ChallengePage
from src.data_loader import download_challenge_excel, load_records_from_excel

logger = logging.getLogger(__name__)

# Número máximo de tentativas de (fill_record + submit) por round em caso de
# StaleElementReferenceException (PRD Seção 9: risco de o clique em "Submit"
# coincidir com o re-render do Angular). Deliberadamente pequeno e explícito
# — nunca um retry ilimitado; esgotadas as tentativas, a exceção original é
# propagada para o chamador (tratamento/log de falha é escopo da Sprint 4).
MAX_ATTEMPTS_PER_ROUND = 3


@dataclass
class RunResult:
    """Resultado estruturado de uma execução completa do desafio.

    Formato de retorno consumido pelos próximos agentes: logging/tratamento
    de falhas (Sprint 4) e geração de artefatos/relatório (Sprint 5). Este
    módulo não grava `result.json`, screenshot ou log — apenas expõe os
    dados brutos necessários para quem for gerar esses artefatos.

    Attributes:
        status: sempre "success" quando `RunResult` é retornado — significa
            que os `records_filled` registros foram submetidos e a
            mensagem de conclusão foi capturada. Em caso de falha, a
            exceção correspondente (ex. `TimeoutException`,
            `StaleElementReferenceException`) é propagada pelo chamador em
            vez de um `RunResult` com status de falha, permitindo que a
            Sprint 4 trate/logue a causa raiz.
        records_filled: quantidade de registros efetivamente preenchidos e
            submetidos com sucesso (round completo).
        execution_time_seconds: tempo total medido localmente — do clique em
            "Start" até a captura da mensagem de conclusão — via
            `time.monotonic()` (não depende de relógio de parede).
        completion_message: texto capturado do popup/tela de conclusão do
            site (ex. mensagem de sucesso e tempo reportado pelo próprio
            rpachallenge.com).
    """

    status: str
    records_filled: int
    execution_time_seconds: float
    completion_message: str


def run_challenge(
    driver: WebDriver,
    records: list[dict[str, str]],
    timeout: int = 10,
) -> RunResult:
    """Executa o loop completo do RPA Challenge: start -> N rounds -> conclusão.

    Assume que `driver` já está posicionado na página do desafio (ex. logo
    após `data_loader.download_challenge_excel`, que navega até
    `CHALLENGE_URL` como parte do download). Cada round é: `fill_record` do
    registro atual, `submit`, e o próximo round só é preenchido depois que
    `challenge_page._locate_input` confirma (via `WebDriverWait`) que os
    campos do novo round já estão presentes no DOM — a espera explícita
    exigida por RF07 já está embutida em `fill_record`/`submit`, então este
    módulo não duplica seletores nem lógica de espera adicional.

    Args:
        driver: WebDriver Selenium já aberto e na página do desafio.
        records: lista de registros no formato retornado por
            `data_loader.load_records_from_excel` (um round por registro,
            10 na planilha oficial).
        timeout: timeout (segundos) repassado ao `ChallengePage` para cada
            espera explícita.

    Returns:
        `RunResult` com status, tempo total, mensagem de conclusão e
        contagem de registros preenchidos.

    Raises:
        StaleElementReferenceException: se persistir após
            `MAX_ATTEMPTS_PER_ROUND` tentativas em algum round.
        TimeoutException: se algum elemento (campo, botão, popup de
            conclusão) não aparecer dentro do timeout configurado.
    """
    page = ChallengePage(driver, timeout=timeout)

    total_records = len(records)
    logger.info("Iniciando execução do desafio com %d registros.", total_records)

    start_time = time.monotonic()
    page.start()

    records_filled = 0
    for round_number, record in enumerate(records, start=1):
        _fill_and_submit_with_retry(page, record, round_number)
        records_filled += 1
        logger.info("Round %d/%d preenchido e submetido.", round_number, total_records)

    completion_message = page.wait_for_completion_message()
    execution_time_seconds = time.monotonic() - start_time

    logger.info(
        "Desafio concluído em %.2fs (%d/%d registros). Mensagem do site: %s",
        execution_time_seconds,
        records_filled,
        total_records,
        completion_message,
    )

    return RunResult(
        status="success",
        records_filled=records_filled,
        execution_time_seconds=execution_time_seconds,
        completion_message=completion_message,
    )


def run(
    driver: WebDriver,
    download_dir: str,
    timeout: int = 10,
) -> RunResult:
    """Ponto de entrada único: download -> parsing -> loop completo do desafio.

    Encadeia as três etapas ponta a ponta (RF02, RF03 e o loop de RF04-RF08)
    para que `cli.py` (sprints futuras) precise chamar apenas esta função
    após criar o `driver` com `driver_factory.create_driver`.

    Args:
        driver: WebDriver Selenium já criado (ver `driver_factory`), com
            `download_dir` configurado nas prefs de download do Chrome.
        download_dir: mesmo diretório absoluto configurado no `driver` para
            downloads, repassado a `data_loader.download_challenge_excel`.
        timeout: timeout (segundos) usado tanto para o download quanto para
            cada espera explícita do formulário.

    Returns:
        `RunResult` (ver `run_challenge`) com os dados da execução.
    """
    logger.info("Iniciando execução completa (download -> parsing -> preenchimento).")
    excel_path = download_challenge_excel(driver, download_dir, timeout=timeout)
    records = load_records_from_excel(excel_path)
    return run_challenge(driver, records, timeout=timeout)


def _fill_and_submit_with_retry(
    page: ChallengePage, record: dict[str, str], round_number: int
) -> None:
    """Preenche e submete um round, com retry controlado por round.

    Reexecuta `fill_record` + `submit` do zero (nunca reaproveitando um
    `WebElement` já localizado) em caso de `StaleElementReferenceException`
    — proteção adicional para o caso raro (PRD Seção 9) de o clique em
    "Submit" coincidir com o re-render do Angular entre uma chamada e outra
    dentro do mesmo round.

    Args:
        page: Page Object já posicionado no formulário do desafio.
        record: registro (round atual) a preencher e submeter.
        round_number: número do round (1-indexado), usado apenas para
            contexto nas mensagens de log (WARNING por tentativa, ERROR se
            esgotar as tentativas).

    Raises:
        StaleElementReferenceException: se o erro persistir após
            `MAX_ATTEMPTS_PER_ROUND` tentativas.
    """
    last_error: StaleElementReferenceException | None = None

    for attempt in range(1, MAX_ATTEMPTS_PER_ROUND + 1):
        try:
            page.fill_record(record)
            page.submit()
            return
        except StaleElementReferenceException as exc:
            last_error = exc
            logger.warning(
                "Round %d: StaleElementReferenceException na tentativa %d/%d "
                "(re-render do Angular coincidiu com a interação); "
                "tentando novamente.",
                round_number,
                attempt,
                MAX_ATTEMPTS_PER_ROUND,
            )

    assert last_error is not None
    logger.error(
        "Round %d: falha definitiva após %d tentativas por "
        "StaleElementReferenceException. Considere aumentar o timeout ou "
        "MAX_ATTEMPTS_PER_ROUND se o site estiver mais lento que o usual.",
        round_number,
        MAX_ATTEMPTS_PER_ROUND,
    )
    raise last_error
