"""Testes do parsing de planilha e da espera de download (sem site real).

A planilha de exemplo é gerada dinamicamente em `tmp_path` (fixture
`sample_excel_path`) em vez de versionada como binário no repositório,
evitando dependência de arquivo `.xlsx` externo.
"""

from __future__ import annotations

import os

import pandas as pd
import pytest

from src.data_loader import (
    EXPECTED_COLUMNS,
    _clear_previous_downloads,
    _wait_for_download,
    load_records_from_excel,
)

SAMPLE_ROWS = [
    {
        "First Name": f"First{i}",
        "Last Name": f"Last{i}",
        "Company Name": f"Company{i}",
        "Role in Company": f"Role{i}",
        "Address": f"Address {i}, City",
        "Email": f"user{i}@example.com",
        "Phone Number": f"555000{i:04d}",
    }
    for i in range(10)
]


@pytest.fixture
def sample_excel_path(tmp_path):
    """Cria uma planilha `.xlsx` de exemplo com 10 registros válidos."""
    path = tmp_path / "sample_challenge.xlsx"
    pd.DataFrame(SAMPLE_ROWS).to_excel(path, index=False, engine="openpyxl")
    return str(path)


def test_load_records_returns_ten_records_with_expected_keys(sample_excel_path):
    records = load_records_from_excel(sample_excel_path)

    assert len(records) == 10
    for record, expected in zip(records, SAMPLE_ROWS):
        assert set(record.keys()) == set(EXPECTED_COLUMNS)
        for column in EXPECTED_COLUMNS:
            assert record[column] == expected[column]


def test_load_records_returns_list_of_plain_dicts(sample_excel_path):
    records = load_records_from_excel(sample_excel_path)

    assert isinstance(records, list)
    assert all(isinstance(record, dict) for record in records)


def test_load_records_missing_file_raises_clear_error(tmp_path):
    missing_path = str(tmp_path / "does_not_exist.xlsx")

    with pytest.raises(FileNotFoundError, match="não encontrada"):
        load_records_from_excel(missing_path)


def test_load_records_corrupted_file_raises_value_error(tmp_path):
    corrupted_path = tmp_path / "corrupted.xlsx"
    corrupted_path.write_text("isto não é um arquivo xlsx válido")

    with pytest.raises(ValueError, match="não foi possível ler|Não foi possível ler"):
        load_records_from_excel(str(corrupted_path))


def test_load_records_missing_columns_raises_value_error(tmp_path):
    path = tmp_path / "missing_columns.xlsx"
    pd.DataFrame([{"First Name": "A", "Last Name": "B"}]).to_excel(
        path, index=False, engine="openpyxl"
    )

    with pytest.raises(ValueError, match="colunas esperadas"):
        load_records_from_excel(str(path))


def test_wait_for_download_ignores_in_progress_crdownload(tmp_path):
    """O polling não deve considerar o download concluído enquanto houver
    um arquivo `.crdownload` temporário no diretório."""
    final_file = tmp_path / "challenge.xlsx"
    in_progress = tmp_path / "challenge.xlsx.crdownload"
    final_file.write_bytes(b"conteudo")
    in_progress.write_bytes(b"parcial")

    with pytest.raises(Exception):
        _wait_for_download(str(tmp_path), timeout=1, poll_interval=0.1)


def test_wait_for_download_returns_path_once_completed(tmp_path):
    final_file = tmp_path / "challenge.xlsx"
    final_file.write_bytes(b"conteudo")

    result = _wait_for_download(str(tmp_path), timeout=2, poll_interval=0.1)

    assert os.path.abspath(result) == os.path.abspath(str(final_file))


def test_clear_previous_downloads_removes_stale_files(tmp_path):
    """RNF08: arquivos de execuções anteriores não devem sobreviver a uma
    nova rodada de download, evitando duplicatas que quebrem a leitura."""
    stale_xlsx = tmp_path / "old.xlsx"
    stale_partial = tmp_path / "old.xlsx.crdownload"
    stale_xlsx.write_bytes(b"velho")
    stale_partial.write_bytes(b"parcial")

    _clear_previous_downloads(str(tmp_path))

    assert not stale_xlsx.exists()
    assert not stale_partial.exists()


def test_clear_previous_downloads_is_idempotent_on_empty_dir(tmp_path):
    """Chamar a limpeza duas vezes seguidas em diretório vazio não falha."""
    _clear_previous_downloads(str(tmp_path))
    _clear_previous_downloads(str(tmp_path))


def test_load_records_strips_trailing_whitespace_from_column_headers(tmp_path):
    """A planilha real do desafio expõe ao menos uma coluna com espaço à
    direita no cabeçalho (ex. "Last Name "), o que fazia o parsing falhar
    com "coluna esperada ausente" antes da normalização em
    `load_records_from_excel` (bug encontrado validando contra o site real
    na Sprint 6)."""
    path = tmp_path / "padded_headers.xlsx"
    rows = [dict(row) for row in SAMPLE_ROWS]
    dataframe = pd.DataFrame(rows).rename(columns={"Last Name": "Last Name "})
    dataframe.to_excel(path, index=False, engine="openpyxl")

    records = load_records_from_excel(str(path))

    assert len(records) == 10
    for record, expected in zip(records, SAMPLE_ROWS):
        assert set(record.keys()) == set(EXPECTED_COLUMNS)
        assert record["Last Name"] == expected["Last Name"]


def test_load_records_numeric_phone_column_has_no_trailing_zero(tmp_path):
    """Coluna numérica (ex. Phone Number sem formatação de texto na planilha,
    especialmente com algum valor ausente forçando dtype float64) não pode
    virar string com sufixo ".0" ao ser convertida (RF03/RNF05)."""
    path = tmp_path / "numeric_phone.xlsx"
    rows = [dict(row) for row in SAMPLE_ROWS]
    rows[0]["Phone Number"] = 5551234  # int -> planilha grava como número
    rows[1]["Phone Number"] = None  # força a coluna para float64 no pandas
    pd.DataFrame(rows).to_excel(path, index=False, engine="openpyxl")

    records = load_records_from_excel(str(path))

    assert records[0]["Phone Number"] == "5551234"
    assert ".0" not in records[0]["Phone Number"]
