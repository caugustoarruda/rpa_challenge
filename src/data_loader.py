"""Download da planilha do desafio e parsing para registros.

Este módulo tem duas responsabilidades independentes (funções puras, sem
estado compartilhado):

1. `download_challenge_excel`: clica no botão "Download Excel" da página do
   RPA Challenge (já aberta no `driver`) e aguarda, via polling sobre o
   sistema de arquivos, a conclusão do download.
2. `load_records_from_excel`: lê um arquivo `.xlsx` já baixado e retorna a
   lista de registros no formato consumido pelo restante da automação.

Contrato de dados (consumido por `challenge_page.fill_record(record)`):
    Cada registro é um `dict[str, str]` com exatamente estas chaves,
    idênticas aos nomes de coluna da planilha do desafio:
        - "First Name"
        - "Last Name"
        - "Company Name"
        - "Role in Company"
        - "Address"
        - "Email"
        - "Phone Number"
    `load_records_from_excel` retorna `list[dict[str, str]]`, uma entrada
    por linha da planilha (10 registros na planilha oficial do desafio).
"""

from __future__ import annotations

import glob
import logging
import os
import time

import pandas as pd
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# Colunas obrigatórias, na ordem em que aparecem na planilha oficial do
# desafio. Usadas tanto para validar o parsing quanto para documentar o
# contrato de dados retornado.
EXPECTED_COLUMNS = [
    "First Name",
    "Last Name",
    "Company Name",
    "Role in Company",
    "Address",
    "Email",
    "Phone Number",
]

CHALLENGE_URL = "https://rpachallenge.com/"

# Nome fixo e previsível dado ao arquivo baixado, garantindo idempotência
# (RNF08): cada download sobrescreve o anterior em vez de acumular cópias
# incrementadas (`(1)`, `(2)`, ...) que o Chrome cria por padrão.
DOWNLOADED_FILENAME = "challenge.xlsx"


def download_challenge_excel(
    driver: WebDriver,
    download_dir: str,
    timeout: int = 30,
) -> str:
    """Clica em "Download Excel" em rpachallenge.com e aguarda o download.

    Assume que `driver` já foi criado com `download_dir` configurado via
    `driver_factory.create_driver` (prefs de download apontando para o
    mesmo diretório). A espera pela conclusão do download é feita por
    polling explícito sobre o sistema de arquivos (nunca `time.sleep()`
    fixo), verificando a existência do arquivo final e a ausência de
    arquivos temporários `.crdownload`/`.tmp` em progresso.

    Para garantir idempotência (RNF08), quaisquer arquivos `.xlsx`/`.crdownload`
    remanescentes de execuções anteriores são removidos do diretório antes do
    clique, e o arquivo baixado é renomeado para um nome fixo
    (`DOWNLOADED_FILENAME`) ao final, evitando acúmulo de cópias
    (`challenge(1).xlsx`, `challenge(2).xlsx`, ...) geradas pelo Chrome.

    Args:
        driver: WebDriver Selenium já aberto (não precisa estar
            necessariamente em `CHALLENGE_URL`; esta função navega até lá).
        download_dir: diretório absoluto configurado como destino de
            download do Chrome (deve ser o mesmo passado a
            `create_driver(download_dir=...)`).
        timeout: tempo máximo (segundos) para clicar no botão e para o
            download concluir.

    Returns:
        Caminho absoluto do arquivo `.xlsx` baixado.

    Raises:
        TimeoutException: se o botão de download não ficar clicável ou o
            download não concluir dentro do tempo limite.
    """
    download_dir = os.path.abspath(download_dir)
    os.makedirs(download_dir, exist_ok=True)
    _clear_previous_downloads(download_dir)

    logger.info("Iniciando download da planilha do desafio em %s.", CHALLENGE_URL)
    driver.get(CHALLENGE_URL)

    try:
        download_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[self::a or self::button][contains(., 'Download')]")
            )
        )
    except TimeoutException:
        logger.error(
            "Botão de download não ficou clicável em %ss em %s. Verifique se o "
            "site está no ar ou se o texto/tag do botão mudou.",
            timeout,
            CHALLENGE_URL,
        )
        raise
    download_button.click()

    downloaded_path = _wait_for_download(download_dir, timeout=timeout)

    final_path = os.path.join(download_dir, DOWNLOADED_FILENAME)
    if os.path.abspath(downloaded_path) != os.path.abspath(final_path):
        if os.path.exists(final_path):
            os.remove(final_path)
        os.rename(downloaded_path, final_path)

    logger.info("Download da planilha concluído: %s", final_path)
    return final_path


def _clear_previous_downloads(download_dir: str) -> None:
    """Remove planilhas e downloads incompletos de execuções anteriores.

    Mantém o diretório limpo antes de um novo download para que o polling
    de conclusão (`_wait_for_download`) não confunda um arquivo antigo com o
    resultado do download atual, e para que múltiplas execuções seguidas
    (RNF08) nunca acumulem arquivos duplicados.
    """
    patterns = ["*.xlsx", "*.xls", "*.crdownload", "*.tmp"]
    for pattern in patterns:
        for stale_file in glob.glob(os.path.join(download_dir, pattern)):
            os.remove(stale_file)


def _wait_for_download(
    download_dir: str,
    timeout: int,
    poll_interval: float = 0.25,
) -> str:
    """Faz polling no `download_dir` até um `.xlsx` completo aparecer.

    Considera o download em andamento enquanto existir qualquer arquivo
    temporário (`.crdownload`/`.tmp`) no diretório. Este polling manual é o
    equivalente, para o sistema de arquivos, do `WebDriverWait` usado para
    esperar elementos do DOM — a alternativa a `time.sleep()` fixo exigida
    pela RNF02.

    Raises:
        TimeoutException: se nenhum arquivo `.xlsx` completo aparecer dentro
            do prazo.
    """
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        in_progress = glob.glob(os.path.join(download_dir, "*.crdownload"))
        in_progress += glob.glob(os.path.join(download_dir, "*.tmp"))
        completed = glob.glob(os.path.join(download_dir, "*.xlsx"))

        if completed and not in_progress:
            return completed[0]

        time.sleep(poll_interval)

    logger.error(
        "Download não concluído em %ss no diretório '%s'. Verifique conexão de "
        "rede ou se o Chrome bloqueou o download (permissões/prefs).",
        timeout,
        download_dir,
    )
    raise TimeoutException(
        f"Download não concluído em {timeout}s (diretório: {download_dir})"
    )


def load_records_from_excel(file_path: str) -> list[dict[str, str]]:
    """Lê a planilha `.xlsx` do desafio e retorna a lista de registros.

    Args:
        file_path: caminho para o arquivo `.xlsx` baixado do desafio.

    Returns:
        Lista de dicts, um por linha da planilha, com as chaves definidas em
        `EXPECTED_COLUMNS` (ver docstring do módulo para o contrato completo
        consumido por `challenge_page.fill_record`).

    Raises:
        FileNotFoundError: se `file_path` não existir.
        ValueError: se o arquivo existir mas não puder ser lido como Excel
            válido (corrompido/formato inesperado), ou se estiver faltando
            alguma das colunas esperadas.
    """
    logger.info("Iniciando parsing da planilha '%s'.", file_path)

    if not os.path.isfile(file_path):
        logger.error(
            "Planilha do desafio não encontrada em '%s'. O download pode não "
            "ter sido concluído ou o caminho está incorreto.",
            file_path,
        )
        raise FileNotFoundError(
            f"Planilha do desafio não encontrada em '{file_path}'. "
            "Verifique se o download foi concluído antes de tentar ler os "
            "registros."
        )

    try:
        # dtype=str evita que colunas numéricas (ex. Phone Number sem
        # formatação de texto na planilha) sejam inferidas como int/float e
        # ganhem sufixo ".0" ao converter para string, o que quebraria a
        # acurácia do preenchimento (RF03/RNF05).
        dataframe = pd.read_excel(file_path, engine="openpyxl", dtype=str)
    except Exception as exc:
        logger.error(
            "Falha ao ler '%s' como planilha Excel válida (arquivo "
            "corrompido ou em formato inesperado): %s",
            file_path,
            exc,
        )
        raise ValueError(
            f"Não foi possível ler '{file_path}' como planilha Excel válida. "
            "O arquivo pode estar corrompido ou em formato inesperado."
        ) from exc

    missing_columns = [col for col in EXPECTED_COLUMNS if col not in dataframe.columns]
    if missing_columns:
        logger.error(
            "Planilha '%s' não contém as colunas esperadas: %s. Colunas "
            "encontradas: %s.",
            file_path,
            missing_columns,
            list(dataframe.columns),
        )
        raise ValueError(
            f"Planilha '{file_path}' não contém as colunas esperadas: "
            f"{missing_columns}. Colunas encontradas: {list(dataframe.columns)}."
        )

    dataframe = dataframe[EXPECTED_COLUMNS].fillna("")

    records = dataframe.astype(str).to_dict(orient="records")
    logger.info("Parsing concluído: %d registros extraídos de '%s'.", len(records), file_path)
    return records
