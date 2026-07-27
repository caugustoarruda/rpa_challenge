"""Criação e configuração do WebDriver Selenium (Chrome)."""

import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def create_driver(headless: bool = False, download_dir: str | None = None) -> webdriver.Chrome:
    """Cria e inicia uma instância configurada do Chrome WebDriver.

    Depende exclusivamente do Selenium Manager nativo (Selenium 4.x) para
    resolver o binário do ChromeDriver, sem necessidade de instalação manual.

    Args:
        headless: roda o Chrome sem janela visível.
        download_dir: caminho absoluto ou relativo onde o Chrome deve salvar
            arquivos baixados. Opcional nesta etapa; o fluxo de download em
            si é implementado em uma sprint posterior (aquisição de dados).

    Returns:
        Uma instância do Chrome WebDriver pronta para uso. Quem chamar é
        responsável por invocar `driver.quit()` ao final.
    """
    options = Options()

    if headless:
        # O modo headless "new" renderiza de forma mais próxima de uma janela
        # normal do Chrome do que a flag legada "--headless", mantendo as
        # execuções headless/non-headless mais consistentes (ver RNF07 e a
        # tabela de riscos na Seção 9 do PRD).
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")

    if download_dir:
        download_dir = os.path.abspath(download_dir)
        os.makedirs(download_dir, exist_ok=True)
        options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
            },
        )

    driver = webdriver.Chrome(options=options)

    if headless and download_dir:
        # O Chrome headless desabilita downloads de arquivo por padrão, por
        # motivos de segurança; este comando CDP reabilita para o diretório
        # configurado.
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": download_dir},
        )

    return driver
