"""Entrypoint de linha de comando da automação do RPA Challenge.

Nesta etapa a CLI apenas faz o parsing dos argumentos e executa um smoke
test de abertura/fechamento do navegador via `driver_factory`. O fluxo real
do desafio (aquisição de dados, preenchimento do formulário, relatório) é
conectado em sprints posteriores, quando `runner.py` orquestrar o fluxo
completo.
"""

import argparse

from src.driver_factory import create_driver


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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    driver = create_driver(headless=args.headless)
    driver.quit()


if __name__ == "__main__":
    main()
