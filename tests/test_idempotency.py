"""Testes de idempotência de execução (RNF08), sem depender do site real.

RNF08 exige que rodar a automação (download + geração de artefatos) múltiplas
vezes seguidas no mesmo diretório não falhe por causa de arquivos/estado de
uma execução anterior. Este arquivo concentra os testes que exercitam
explicitamente o cenário "rodar duas vezes seguidas", cobrindo as três frentes
que geram artefatos em disco:

1. `data_loader`: limpeza do diretório de download antes de cada rodada.
2. `reporting`: geração de `result.json`/screenshot (nomes fixos,
   sobrescrita atômica).
3. `logging_config`: reconfiguração do logger sem duplicar handlers/linhas.

Cada frente já tem alguma cobertura unitária isolada em seu próprio arquivo de
teste (`test_data_loader.py`, `test_reporting.py`); aqui o foco é
especificamente o comportamento em uma segunda chamada consecutiva.
"""

from __future__ import annotations

import json
import logging
import os

import pytest

from src.data_loader import _clear_previous_downloads, _wait_for_download
from src.driver_factory import create_driver
from src.logging_config import LOG_FILENAME, _HANDLER_MARKER, configure_logging
from src.reporting import (
    RESULT_FILENAME,
    SCREENSHOT_FILENAME,
    build_result_dict,
    generate_artifacts,
    save_result_json,
    save_screenshot,
)
from src.runner import RunResult


def _sample_run_result(records_filled: int, status: str = "success") -> RunResult:
    return RunResult(
        status=status,
        records_filled=records_filled,
        execution_time_seconds=10.0,
        completion_message="Congratulations! ... in 20 seconds ...",
    )


# --------------------------------------------------------------------------
# data_loader: idempotência do diretório de download
# --------------------------------------------------------------------------


def test_download_directory_survives_two_consecutive_download_cycles(tmp_path):
    """Simula duas rodadas completas de download no mesmo diretório
    (limpar resíduos -> aguardar arquivo -> repetir), reproduzindo o padrão
    usado por `download_challenge_excel` sem precisar de navegador/site
    real. A segunda rodada não pode falhar nem "ver" arquivos da primeira."""
    download_dir = str(tmp_path)

    for round_number in range(1, 3):
        _clear_previous_downloads(download_dir)
        assert os.listdir(download_dir) == [], (
            f"Rodada {round_number}: diretório deveria estar vazio após a limpeza."
        )

        (tmp_path / "challenge.xlsx").write_bytes(f"conteudo-rodada-{round_number}".encode())

        completed_path = _wait_for_download(download_dir, timeout=2, poll_interval=0.1)
        assert os.path.isfile(completed_path)
        with open(completed_path, "rb") as completed_file:
            assert completed_file.read() == f"conteudo-rodada-{round_number}".encode()


def test_clear_previous_downloads_removes_files_left_by_a_previous_round(tmp_path):
    """Resíduos de uma primeira "execução" (xlsx final + .crdownload
    abandonado) não podem sobreviver à limpeza que antecede a segunda."""
    (tmp_path / "challenge.xlsx").write_bytes(b"rodada-1")
    (tmp_path / "outro.xlsx.crdownload").write_bytes(b"parcial-abandonado")

    _clear_previous_downloads(str(tmp_path))

    assert os.listdir(str(tmp_path)) == []

    # A segunda rodada de download deve funcionar normalmente no diretório
    # já limpo, sem qualquer interferência da primeira.
    (tmp_path / "challenge.xlsx").write_bytes(b"rodada-2")
    completed_path = _wait_for_download(str(tmp_path), timeout=2, poll_interval=0.1)
    with open(completed_path, "rb") as completed_file:
        assert completed_file.read() == b"rodada-2"


# --------------------------------------------------------------------------
# reporting: idempotência de result.json / screenshot
# --------------------------------------------------------------------------


def test_save_result_json_twice_in_a_row_overwrites_without_error(tmp_path):
    first_dict = build_result_dict(_sample_run_result(10), 100.0, 20.0, headless=True)
    second_dict = build_result_dict(_sample_run_result(8, status="failure"), 80.0, None, headless=False)

    path_first = save_result_json(first_dict, str(tmp_path))
    path_second = save_result_json(second_dict, str(tmp_path))

    assert path_first == path_second
    assert os.listdir(tmp_path) == [RESULT_FILENAME]

    with open(path_second, encoding="utf-8") as result_file:
        loaded = json.load(result_file)
    assert loaded == second_dict
    assert loaded["records_filled"] == 8
    assert loaded["status"] == "failure"


def test_save_result_json_ten_consecutive_calls_never_accumulate_files(tmp_path):
    """Reforça RNF08 com uma sequência mais longa do que "só duas vezes",
    já que a Seção 10 do PRD trata explicitamente de execuções repetidas."""
    for i in range(10):
        result_dict = build_result_dict(_sample_run_result(i), float(i * 10), None, headless=(i % 2 == 0))
        save_result_json(result_dict, str(tmp_path))

    assert os.listdir(tmp_path) == [RESULT_FILENAME]
    with open(tmp_path / RESULT_FILENAME, encoding="utf-8") as result_file:
        loaded = json.load(result_file)
    assert loaded["records_filled"] == 9  # última chamada do loop (i=9)


@pytest.fixture(scope="module")
def driver():
    drv = create_driver(headless=True)
    drv.get("about:blank")
    yield drv
    drv.quit()


def test_save_screenshot_twice_in_a_row_overwrites_single_file(driver, tmp_path):
    first_path = save_screenshot(driver, str(tmp_path))
    second_path = save_screenshot(driver, str(tmp_path))

    assert first_path == second_path
    assert os.listdir(tmp_path) == [SCREENSHOT_FILENAME]


def test_generate_artifacts_twice_in_a_row_reflects_only_the_last_run(driver, tmp_path):
    """Rodar a geração completa de artefatos duas vezes seguidas no mesmo
    `output_dir` (como aconteceria em duas execuções consecutivas da CLI)
    não deve lançar erro nem deixar `result.json`/screenshot de execuções
    diferentes coexistindo — apenas o resultado da última chamada."""
    first_result = _sample_run_result(10)
    second_result = _sample_run_result(9, status="failure")

    generate_artifacts(driver, first_result, output_dir=str(tmp_path), headless=True)
    artifacts_dict = generate_artifacts(driver, second_result, output_dir=str(tmp_path), headless=False)

    assert sorted(os.listdir(tmp_path)) == sorted([RESULT_FILENAME, SCREENSHOT_FILENAME])

    with open(tmp_path / RESULT_FILENAME, encoding="utf-8") as result_file:
        loaded = json.load(result_file)
    assert loaded == artifacts_dict
    assert loaded["records_filled"] == 9
    assert loaded["status"] == "failure"
    assert loaded["headless"] is False


# --------------------------------------------------------------------------
# logging_config: idempotência da configuração do logger
# --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_root_logger_state():
    """Evita que os testes de logging desta suíte vazem handlers/estado
    global para o restante da sessão do `pytest` (o logger raiz é
    compartilhado pelo processo inteiro)."""
    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    yield

    for handler in list(root_logger.handlers):
        if handler not in original_handlers:
            root_logger.removeHandler(handler)
            handler.close()
    root_logger.setLevel(original_level)


def test_configure_logging_twice_does_not_duplicate_handlers(tmp_path):
    configure_logging(str(tmp_path))
    configure_logging(str(tmp_path))

    root_logger = logging.getLogger()
    marked_handlers = [h for h in root_logger.handlers if getattr(h, _HANDLER_MARKER, False)]

    # Exatamente um FileHandler + um StreamHandler, mesmo após a segunda
    # chamada — nunca 4 handlers acumulados.
    assert len(marked_handlers) == 2


def test_configure_logging_twice_does_not_duplicate_log_lines(tmp_path):
    configure_logging(str(tmp_path))
    configure_logging(str(tmp_path))

    test_logger = logging.getLogger("tests.test_idempotency")
    test_logger.info("mensagem-unica-de-idempotencia")

    log_path = tmp_path / LOG_FILENAME
    content = log_path.read_text(encoding="utf-8")

    assert content.count("mensagem-unica-de-idempotencia") == 1
