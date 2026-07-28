"""Entrypoint de linha de comando da automação do RPA Challenge.

A CLI faz o parsing dos argumentos e executa o fluxo ponta a ponta
(`src.runner.run`: download -> parsing -> preenchimento dos 10 rounds ->
mensagem de conclusão). A geração de artefatos (`result.json`, screenshot)
é responsabilidade da Sprint 5 (`reporting.py`, ainda não conectado aqui) —
por ora o `RunResult` retornado é apenas logado em INFO. A estrutura de
logging e tratamento de falhas (try/except/finally com código de saída
não-zero) garante que qualquer exceção esperada do domínio (timeout,
elemento não encontrado, download/parsing falho) aborte a execução de forma
auditável, em vez de travar silenciosamente.
"""

import argparse
import logging
import sys

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)

from src.driver_factory import create_driver
from src.logging_config import configure_logging
from src.runner import run

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Automates the rpachallenge.com dynamic form challenge.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser without a visible UI window.",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/",
        help="Directory where execution artifacts are written (default: artifacts/).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout (seconds) for each explicit wait: download, form fields "
        "and completion message (default: 30).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    configure_logging(args.output_dir)

    logger.info(
        "Iniciando execução do RPA Challenge (headless=%s, output_dir=%s, "
        "timeout=%ss).",
        args.headless,
        args.output_dir,
        args.timeout,
    )

    driver = None
    try:
        # `download_dir` precisa ser o mesmo repassado a `run()` para que o
        # Chrome salve a planilha onde `data_loader` espera encontrá-la.
        driver = create_driver(headless=args.headless, download_dir=args.output_dir)
        result = run(driver, download_dir=args.output_dir, timeout=args.timeout)
        logger.info(
            "Execução concluída: %d registros preenchidos em %.2fs. "
            "Mensagem do site: %s",
            result.records_filled,
            result.execution_time_seconds,
            result.completion_message,
        )
    except (
        TimeoutException,
        NoSuchElementException,
        StaleElementReferenceException,
        FileNotFoundError,
        ValueError,
    ) as exc:
        # Exceções esperadas do domínio (RF11/Seção 9 do PRD): logadas com
        # contexto e propagadas como falha explícita — nunca engolidas.
        logger.error(
            "Execução abortada por falha esperada do domínio: %s",
            exc,
            exc_info=True,
        )
        sys.exit(1)
    except Exception:
        # Qualquer outro erro não previsto também deve abortar com código
        # de saída não-zero, nunca travar silenciosamente.
        logger.error("Execução abortada por erro inesperado.", exc_info=True)
        sys.exit(1)
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    main()
