"""Entrypoint de linha de comando da automação do RPA Challenge.

A CLI faz o parsing dos argumentos e executa o fluxo ponta a ponta
(`src.runner.run`: download -> parsing -> preenchimento dos 10 rounds ->
mensagem de conclusão), seguido da geração dos artefatos de evidência
(`src.reporting.generate_artifacts`: screenshot final e `result.json`,
RF09/RF10). A geração dos artefatos acontece ainda dentro do bloco `try`,
antes do `finally` que fecha o driver — a captura de screenshot depende do
navegador ainda estar aberto. A estrutura de logging e tratamento de falhas
(try/except/finally com código de saída não-zero) garante que qualquer
exceção esperada do domínio (timeout, elemento não encontrado,
download/parsing falho) aborte a execução de forma auditável, em vez de
travar silenciosamente.
"""

import argparse
import logging
import sys
import time

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)

from src.driver_factory import create_driver
from src.logging_config import configure_logging
from src.reporting import generate_artifacts
from src.runner import RunResult, run

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
    start_time = time.monotonic()
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

        # Artefatos precisam ser gerados com o driver ainda aberto (o
        # screenshot final depende disso) — por isso ficam dentro do `try`,
        # antes do `finally` que chama `driver.quit()`.
        artifacts = generate_artifacts(
            driver,
            result,
            output_dir=args.output_dir,
            headless=args.headless,
        )
        logger.info("Artefatos de evidência gerados em '%s': %s", args.output_dir, artifacts)
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
        _generate_failure_artifacts(driver, args, start_time, exc)
        sys.exit(1)
    except Exception as exc:
        # Qualquer outro erro não previsto também deve abortar com código
        # de saída não-zero, nunca travar silenciosamente.
        logger.error("Execução abortada por erro inesperado.", exc_info=True)
        _generate_failure_artifacts(driver, args, start_time, exc)
        sys.exit(1)
    finally:
        if driver is not None:
            driver.quit()


def _generate_failure_artifacts(
    driver, args: argparse.Namespace, start_time: float, exc: Exception
) -> None:
    """Gera artefatos em modo melhor-esforço quando a execução falha.

    O critério de aceite do PRD (Seção 8) exige `result.json`/screenshot "a
    cada execução", não só nas bem-sucedidas. Como `runner.run` propaga a
    exceção em vez de devolver um `RunResult` parcial em caso de falha, aqui
    montamos um `RunResult` sintético com `status="failure"` só para deixar
    evidência da tentativa. Qualquer erro nessa captura (ex. driver já
    inválido) é apenas logado como warning — nunca deve mascarar a exceção
    original que já está sendo propagada via `sys.exit(1)`.
    """
    if driver is None:
        return

    try:
        failure_result = RunResult(
            status="failure",
            records_filled=0,
            execution_time_seconds=time.monotonic() - start_time,
            completion_message=str(exc),
        )
        artifacts = generate_artifacts(
            driver,
            failure_result,
            output_dir=args.output_dir,
            headless=args.headless,
        )
        logger.info(
            "Artefatos de evidência (falha) gerados em '%s': %s",
            args.output_dir,
            artifacts,
        )
    except Exception:
        logger.warning(
            "Não foi possível gerar artefatos de evidência após a falha.",
            exc_info=True,
        )


if __name__ == "__main__":
    main()
