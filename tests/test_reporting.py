"""Testes de cálculo de acurácia e geração do `result.json` (sem site real).

A maioria dos testes aqui é puramente estrutural (dicts/arquivos locais em
`tmp_path`), sem qualquer navegador. Apenas `save_screenshot`/
`generate_artifacts` precisam de um `driver` real (porque a função chama
`driver.save_screenshot`) — nesse caso reaproveitamos o mesmo padrão de
`tests/test_field_mapping.py`: um WebDriver Chrome headless local, apontado
para `about:blank` (nunca o site real, e nunca um mock de navegador).
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import pytest

from src.driver_factory import create_driver
from src.reporting import (
    RESULT_FILENAME,
    SCREENSHOT_FILENAME,
    build_result_dict,
    calculate_accuracy,
    extract_site_reported_time,
    generate_artifacts,
    save_result_json,
    save_screenshot,
)
from src.runner import RunResult


def _sample_run_result(
    status: str = "success",
    records_filled: int = 10,
    execution_time: float = 42.123456,
    completion_message: str = "Congratulations! You have succeeded in 24 seconds with 10 out of 10 records.",
) -> RunResult:
    return RunResult(
        status=status,
        records_filled=records_filled,
        execution_time_seconds=execution_time,
        completion_message=completion_message,
    )


# --------------------------------------------------------------------------
# calculate_accuracy
# --------------------------------------------------------------------------


def test_calculate_accuracy_full_records_is_100_percent():
    assert calculate_accuracy(10, total_records=10) == 100.0


def test_calculate_accuracy_partial_records():
    assert calculate_accuracy(7, total_records=10) == 70.0


def test_calculate_accuracy_zero_records_filled():
    assert calculate_accuracy(0, total_records=10) == 0.0


def test_calculate_accuracy_rounds_to_two_decimal_places():
    # 1/3 * 100 = 33.333... -> arredondado para 33.33
    assert calculate_accuracy(1, total_records=3) == 33.33


def test_calculate_accuracy_zero_total_records_avoids_zero_division():
    assert calculate_accuracy(5, total_records=0) == 0.0


def test_calculate_accuracy_negative_total_records_returns_zero():
    assert calculate_accuracy(5, total_records=-1) == 0.0


# --------------------------------------------------------------------------
# extract_site_reported_time
# --------------------------------------------------------------------------


def test_extract_site_reported_time_parses_integer_seconds():
    message = "Congratulations! You have succeeded in 24 seconds with 10 out of 10 correct."
    assert extract_site_reported_time(message) == 24.0


def test_extract_site_reported_time_parses_decimal_seconds():
    assert extract_site_reported_time("Done in 12.5 seconds.") == 12.5


def test_extract_site_reported_time_is_case_insensitive():
    assert extract_site_reported_time("Finished in 9 SECONDS total.") == 9.0


def test_extract_site_reported_time_parses_milliseconds_and_converts_to_seconds():
    """O site real reporta o tempo em milissegundos (ex. "in 4751
    milliseconds"), não em segundos — bug encontrado validando contra
    rpachallenge.com na Sprint 6."""
    message = "Congratulations!\nYour success rate is 100% ( 70 out of 70 fields) in 4751 milliseconds"
    assert extract_site_reported_time(message) == 4.751


def test_extract_site_reported_time_milliseconds_is_case_insensitive():
    assert extract_site_reported_time("Done in 500 Milliseconds.") == 0.5


def test_extract_site_reported_time_does_not_confuse_milliseconds_with_seconds():
    """"milliseconds" contém "second" como substring; o regex não pode
    interpretar erroneamente um valor em milissegundos como segundos."""
    assert extract_site_reported_time("in 4751 milliseconds") == 4.751
    assert extract_site_reported_time("in 24 seconds") == 24.0


def test_extract_site_reported_time_returns_none_when_no_number_present():
    assert extract_site_reported_time("Congratulations! Well done.") is None


def test_extract_site_reported_time_returns_none_for_empty_message():
    assert extract_site_reported_time("") is None


def test_extract_site_reported_time_returns_none_for_none_message():
    assert extract_site_reported_time(None) is None  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# build_result_dict
# --------------------------------------------------------------------------


def test_build_result_dict_has_exact_expected_keys():
    """RF10/Seção 7 do PRD: o `result.json` deve conter exatamente estes
    campos, nem mais nem menos."""
    result_dict = build_result_dict(
        _sample_run_result(), accuracy_pct=100.0, site_reported_time=24.0, headless=True
    )

    expected_keys = {
        "status",
        "records_filled",
        "accuracy_pct",
        "execution_time_seconds",
        "site_reported_time",
        "timestamp",
        "headless",
    }
    assert set(result_dict.keys()) == expected_keys


def test_build_result_dict_preserves_input_values():
    result = _sample_run_result(records_filled=10, execution_time=42.123456)
    result_dict = build_result_dict(result, accuracy_pct=100.0, site_reported_time=24.0, headless=False)

    assert result_dict["status"] == "success"
    assert result_dict["records_filled"] == 10
    assert result_dict["accuracy_pct"] == 100.0
    assert result_dict["execution_time_seconds"] == 42.12
    assert result_dict["site_reported_time"] == 24.0
    assert result_dict["headless"] is False


def test_build_result_dict_does_not_force_success_status():
    """O status deve refletir fielmente `RunResult.status`, mesmo em caso
    de falha — nunca "otimizado" para success (ver docstring de
    `build_result_dict` em `src/reporting.py`)."""
    failure_result = _sample_run_result(status="failure", records_filled=3, execution_time=5.0)
    result_dict = build_result_dict(
        failure_result, accuracy_pct=30.0, site_reported_time=None, headless=True
    )

    assert result_dict["status"] == "failure"
    assert result_dict["records_filled"] == 3
    assert result_dict["accuracy_pct"] == 30.0
    assert result_dict["site_reported_time"] is None


def test_build_result_dict_timestamp_is_valid_iso_format():
    result_dict = build_result_dict(_sample_run_result(), 100.0, 24.0, headless=True)

    # `datetime.fromisoformat` lança ValueError se o formato não for válido.
    datetime.fromisoformat(result_dict["timestamp"])


# --------------------------------------------------------------------------
# save_result_json
# --------------------------------------------------------------------------


def test_save_result_json_writes_valid_json_file(tmp_path):
    result_dict = build_result_dict(_sample_run_result(), 100.0, 24.0, headless=True)

    saved_path = save_result_json(result_dict, str(tmp_path))

    assert os.path.isfile(saved_path)
    assert os.path.basename(saved_path) == RESULT_FILENAME
    with open(saved_path, encoding="utf-8") as result_file:
        loaded = json.load(result_file)
    assert loaded == result_dict


def test_save_result_json_creates_output_dir_if_missing(tmp_path):
    output_dir = tmp_path / "nested" / "artifacts"
    result_dict = build_result_dict(_sample_run_result(), 100.0, 24.0, headless=True)

    saved_path = save_result_json(result_dict, str(output_dir))

    assert os.path.isfile(saved_path)


def test_save_result_json_does_not_leave_temporary_files_behind(tmp_path):
    """A escrita atômica (arquivo temporário + `os.replace`) não deve
    deixar nenhum `.result_*.json.tmp` residual no diretório final."""
    result_dict = build_result_dict(_sample_run_result(), 100.0, 24.0, headless=True)

    save_result_json(result_dict, str(tmp_path))

    assert os.listdir(tmp_path) == [RESULT_FILENAME]


# --------------------------------------------------------------------------
# save_screenshot / generate_artifacts (WebDriver headless real, sem site real)
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def driver():
    drv = create_driver(headless=True)
    drv.get("about:blank")
    yield drv
    drv.quit()


def test_save_screenshot_creates_file_with_fixed_name(driver, tmp_path):
    screenshot_path = save_screenshot(driver, str(tmp_path))

    assert os.path.isfile(screenshot_path)
    assert os.path.basename(screenshot_path) == SCREENSHOT_FILENAME


def test_generate_artifacts_writes_result_json_and_screenshot(driver, tmp_path):
    result = _sample_run_result(records_filled=10, execution_time=15.5)

    artifacts_dict = generate_artifacts(driver, result, output_dir=str(tmp_path), headless=True)

    assert artifacts_dict["status"] == "success"
    assert artifacts_dict["accuracy_pct"] == 100.0
    assert artifacts_dict["site_reported_time"] == 24.0  # extraído de completion_message
    assert os.path.isfile(tmp_path / SCREENSHOT_FILENAME)
    assert os.path.isfile(tmp_path / RESULT_FILENAME)


def test_generate_artifacts_accuracy_reflects_partial_completion(driver, tmp_path):
    """Um `RunResult` com menos registros preenchidos que o total esperado
    deve refletir a acurácia real (RNF05) — a função nunca "arredonda para
    100%" nem esconde uma execução parcial."""
    result = _sample_run_result(
        records_filled=7, execution_time=10.0, completion_message="Sem mensagem de conclusão."
    )

    artifacts_dict = generate_artifacts(driver, result, output_dir=str(tmp_path), headless=False)

    assert artifacts_dict["accuracy_pct"] == 70.0
    assert artifacts_dict["site_reported_time"] is None
    assert artifacts_dict["headless"] is False
