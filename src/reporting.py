"""Cálculo de acurácia, captura de screenshot e geração do `result.json`.

Este módulo consome o `RunResult` retornado por `runner.run`/`run_challenge`
(Sprint 3/4) e produz as evidências exigidas pelo desafio (RF09, RF10, Seção
7 do PRD): screenshot da tela final, arquivo `result.json` no formato exato
especificado e o cálculo de acurácia a partir da contagem de registros
preenchidos. Nenhuma lógica de navegação/seletor vive aqui — apenas leitura
do estado já capturado (`driver.save_screenshot`, texto do popup de
conclusão) e escrita de arquivos.

Idempotência (RNF08): os nomes dos artefatos são fixos
(`final_screenshot.png`, `result.json`) e cada geração sobrescreve o
resultado da execução anterior — nenhum arquivo acumula entre execuções. A
escrita do `result.json` é feita em arquivo temporário seguido de
`os.replace`, garantindo que uma reexecução nunca deixe o arquivo em estado
parcial/corrompido caso o processo seja interrompido no meio da escrita.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver

from src.runner import RunResult

logger = logging.getLogger(__name__)

# Total de registros esperados pelo desafio oficial (PRD Seção 2: planilha
# fixa de 10 registros). Usado como denominador padrão do cálculo de
# acurácia; exposto como parâmetro em `calculate_accuracy`/`generate_artifacts`
# para permitir testes com outros totais sem alterar o comportamento de
# produção.
TOTAL_RECORDS = 10

# Nomes fixos e previsíveis dos artefatos (RNF08): cada execução sobrescreve
# o arquivo da execução anterior em vez de acumular cópias com timestamp.
SCREENSHOT_FILENAME = "final_screenshot.png"
RESULT_FILENAME = "result.json"

# Regex tolerante para extrair o tempo reportado pelo próprio site a partir
# do texto do popup de conclusão (ex. "... in 24 seconds ..." ou, como o site
# real reporta, "... in 4751 milliseconds ..."). Deliberadamente permissiva
# quanto ao texto ao redor do número: essa extração é tratada pelo PRD
# (Sprint 5) como "nice to have" — se o formato da mensagem mudar,
# `extract_site_reported_time` deve retornar `None` em vez de lançar exceção.
SITE_TIME_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(millisecond|second)s?", re.IGNORECASE)


def calculate_accuracy(records_filled: int, total_records: int = TOTAL_RECORDS) -> float:
    """Calcula a acurácia (%) a partir dos registros efetivamente preenchidos.

    Args:
        records_filled: quantidade de registros preenchidos e submetidos com
            sucesso (ver `RunResult.records_filled`).
        total_records: total de registros esperados pelo desafio (10 na
            planilha oficial).

    Returns:
        Percentual (0.0 a 100.0) de registros preenchidos em relação ao
        total esperado, arredondado a 2 casas decimais. Retorna 0.0 se
        `total_records` for menor ou igual a zero, evitando
        `ZeroDivisionError`.
    """
    if total_records <= 0:
        return 0.0
    accuracy = (records_filled / total_records) * 100
    return round(accuracy, 2)


def extract_site_reported_time(completion_message: str) -> float | None:
    """Extrai o tempo (em segundos) reportado pelo próprio site, se exposto.

    A mensagem de conclusão do rpachallenge.com costuma incluir o tempo total
    gasto (ex. "... in 24 seconds ..."). Como esse texto não é um contrato
    estável do site (pode mudar de formato numa atualização), a extração é
    "melhor esforço": qualquer falha de parsing resulta em `None`, nunca em
    exceção propagada.

    Args:
        completion_message: texto capturado por
            `ChallengePage.wait_for_completion_message`.

    Returns:
        Tempo em segundos reportado pelo site (convertido a partir de
        milissegundos quando for essa a unidade usada na mensagem), ou
        `None` se não for possível extrair um número da mensagem.
    """
    if not completion_message:
        return None

    match = SITE_TIME_PATTERN.search(completion_message)
    if match is None:
        return None

    try:
        value = float(match.group(1))
    except ValueError:
        return None

    if match.group(2).lower() == "millisecond":
        return round(value / 1000, 3)
    return value


def save_screenshot(driver: WebDriver, output_dir: str) -> str:
    """Salva um screenshot da tela atual em `<output_dir>/final_screenshot.png`.

    Usa `driver.save_screenshot`, captura de tela real (não
    `execute_script`/manipulação de DOM) — permitido por RNF06. O nome do
    arquivo é fixo para que execuções sucessivas sobrescrevam o screenshot
    anterior (RNF08), sem acumular capturas de execuções antigas.

    Args:
        driver: WebDriver Selenium ainda aberto, idealmente posicionado na
            tela final (mensagem de conclusão) do desafio.
        output_dir: diretório onde o screenshot deve ser salvo.

    Returns:
        Caminho absoluto do arquivo de screenshot salvo.
    """
    os.makedirs(output_dir, exist_ok=True)
    screenshot_path = os.path.abspath(os.path.join(output_dir, SCREENSHOT_FILENAME))

    saved = driver.save_screenshot(screenshot_path)
    if not saved:
        logger.warning(
            "driver.save_screenshot retornou False para '%s'; o screenshot "
            "pode não ter sido salvo corretamente.",
            screenshot_path,
        )
    else:
        logger.info("Screenshot da tela final salvo em '%s'.", screenshot_path)

    return screenshot_path


def build_result_dict(
    result: RunResult,
    accuracy_pct: float,
    site_reported_time: float | None,
    headless: bool,
) -> dict[str, Any]:
    """Monta o dict de `result.json` no formato exato da Seção 7 do PRD.

    O `status` é repassado exatamente como veio de `RunResult` — nunca
    forçado para `"success"`: se uma execução futura passar a reportar
    falha (ex. `RunResult.status == "failure"`), o relatório deve refletir
    isso fielmente, sem "otimizar" o resultado para a entrega.

    Args:
        result: resultado bruto da execução (`runner.run`/`run_challenge`).
        accuracy_pct: percentual calculado por `calculate_accuracy`.
        site_reported_time: tempo (segundos) extraído por
            `extract_site_reported_time`, ou `None` se não disponível.
        headless: se a execução rodou em modo headless.

    Returns:
        Dict pronto para serialização JSON, com exatamente os campos:
        `status`, `records_filled`, `accuracy_pct`, `execution_time_seconds`,
        `site_reported_time`, `timestamp`, `headless`.
    """
    return {
        "status": result.status,
        "records_filled": result.records_filled,
        "accuracy_pct": accuracy_pct,
        "execution_time_seconds": round(result.execution_time_seconds, 2),
        "site_reported_time": site_reported_time,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "headless": headless,
    }


def save_result_json(result_dict: dict[str, Any], output_dir: str) -> str:
    """Serializa `result_dict` em `<output_dir>/result.json` de forma atômica.

    Escreve primeiro em um arquivo temporário no mesmo diretório e só então
    o promove com `os.replace` para o nome final (`result.json`) — garante
    que reexecuções (RNF08) sobrescrevam o arquivo de forma segura, sem
    deixá-lo truncado/parcial caso o processo seja interrompido durante a
    escrita.

    Args:
        result_dict: dict já no formato de `build_result_dict`.
        output_dir: diretório onde `result.json` deve ser salvo.

    Returns:
        Caminho absoluto do `result.json` salvo.
    """
    os.makedirs(output_dir, exist_ok=True)
    final_path = os.path.abspath(os.path.join(output_dir, RESULT_FILENAME))

    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(final_path), prefix=".result_", suffix=".json.tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            json.dump(result_dict, tmp_file, indent=2, ensure_ascii=False)
            tmp_file.write("\n")
        os.replace(tmp_path, final_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    logger.info("Relatório de resultado salvo em '%s'.", final_path)
    return final_path


def generate_artifacts(
    driver: WebDriver,
    result: RunResult,
    output_dir: str,
    headless: bool,
    total_records: int = TOTAL_RECORDS,
) -> dict[str, Any]:
    """Gera os artefatos de evidência da execução (RF09, RF10).

    Orquestra, nesta ordem, a captura do screenshot final (o `driver` ainda
    precisa estar aberto), o cálculo de acurácia, a extração best-effort do
    tempo reportado pelo site e a gravação de `result.json`. Deve ser
    chamada antes de `driver.quit()` — depois de fechado o driver não é mais
    possível capturar o screenshot.

    Args:
        driver: WebDriver Selenium ainda aberto, na tela final do desafio.
        result: `RunResult` retornado por `runner.run`.
        output_dir: diretório onde os artefatos são salvos (mesmo
            `output_dir`/`args.output_dir` usado pelo restante do pipeline).
        headless: se a execução rodou em modo headless.
        total_records: total de registros esperados (10 por padrão).

    Returns:
        O dict gravado em `result.json` (útil para logging em `cli.py`).
    """
    save_screenshot(driver, output_dir)

    accuracy_pct = calculate_accuracy(result.records_filled, total_records)
    site_reported_time = extract_site_reported_time(result.completion_message)

    result_dict = build_result_dict(result, accuracy_pct, site_reported_time, headless)
    save_result_json(result_dict, output_dir)

    return result_dict
