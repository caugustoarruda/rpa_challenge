"""Testes do mapeamento crítico coluna -> seletor (`challenge_page.py`).

Não dependem do site real: as fixtures são páginas HTML estáticas geradas
dinamicamente em `tmp_path`, reproduzindo a estrutura de DOM observada em
rpachallenge.com (bloco `<rpa1-field>` com `<label>` + `<input
ng-reflect-name="...">`). Como o Selenium/Chrome já é dependência central de
todo o projeto (não uma dependência extra criada só para o teste), os testes
que precisam confirmar a localização real do elemento usam um WebDriver
headless local, apontado para `file://<fixture>` em vez de `rpachallenge.com`.

Os testes puramente estruturais (cobertura/ambiguidade do mapa
`FIELD_SELECTORS`) não abrem navegador algum.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By

from src.challenge_page import (
    FIELD_SELECTORS,
    START_BUTTON_XPATH,
    SUBMIT_BUTTON_CSS,
    ChallengePage,
)
from src.data_loader import EXPECTED_COLUMNS
from src.driver_factory import create_driver

COLUMNS = list(EXPECTED_COLUMNS)


def _slugify(column: str) -> str:
    """Converte um nome de coluna em um `id` de elemento previsível para uso
    exclusivo nas fixtures de teste (não tem relação com o `id` aleatório
    que o site real gera a cada round)."""
    return "input-" + column.lower().replace(" ", "-")


def _ng_reflect_name(column: str) -> str:
    """Extrai o valor de `ng-reflect-name` esperado a partir do seletor CSS
    definido em `FIELD_SELECTORS`, garantindo que a fixture sempre reflita o
    que a produção espera (sem duplicar o mapeamento coluna -> atributo)."""
    css = FIELD_SELECTORS[column]["css"]
    match = re.search(r"ng-reflect-name='([^']+)'", css)
    assert match, f"Seletor CSS de '{column}' não contém ng-reflect-name: {css}"
    return match.group(1)


def _build_form_html(
    order: list[str],
    missing_ng_reflect_for: str | None = None,
    prefill_residual_value: bool = False,
) -> str:
    """Monta uma página HTML standalone reproduzindo a estrutura do
    formulário do RPA Challenge, com os campos na ordem `order`.

    Args:
        order: ordem visual dos campos nesta fixture (simula a reordenação
            entre rounds do site real).
        missing_ng_reflect_for: se informado, o `<input>` dessa coluna é
            gerado sem o atributo `ng-reflect-name`, simulando o risco
            documentado na Seção 9 do PRD (atributo estável mudando numa
            atualização do site) e forçando o uso do fallback por `<label>`.
        prefill_residual_value: se `True`, cada `<input>` já nasce com um
            valor residual (`value="residual"`), usado para comprovar que
            `fill_record` chama `clear()` antes de `send_keys()`.
    """
    field_blocks = []
    for column in order:
        marker_id = _slugify(column)
        ng_attr = ""
        if column != missing_ng_reflect_for:
            ng_attr = f" ng-reflect-name=\"{_ng_reflect_name(column)}\""
        value_attr = ' value="residual"' if prefill_residual_value else ""
        field_blocks.append(
            f"""
            <div class="col s6 m6 l6">
              <rpa1-field>
                <div>
                  <label>{column}</label>
                  <input{ng_attr} id="{marker_id}" name="{marker_id}"{value_attr}>
                </div>
              </rpa1-field>
            </div>
            """
        )

    fields_html = "\n".join(field_blocks)

    return f"""<!DOCTYPE html>
<html lang="en">
<body>
  <button onclick="document.getElementById('marker').innerText='start-clicked'">Start</button>
  <div id="marker">idle</div>
  <form novalidate>
    <div class="row">
      {fields_html}
    </div>
    <input
      class="btn uiColorButton"
      type="submit"
      value="Submit"
      onclick="document.getElementById('marker').innerText='submit-clicked'; return false;"
    >
  </form>
</body>
</html>
"""


def _write_fixture(tmp_path: Path, name: str, html: str) -> str:
    """Escreve `html` em `tmp_path/name` e retorna a URL `file://` correspondente."""
    fixture_path = tmp_path / name
    fixture_path.write_text(html, encoding="utf-8")
    return fixture_path.resolve().as_uri()


# --------------------------------------------------------------------------
# Testes estruturais do mapa coluna -> seletor (sem navegador)
# --------------------------------------------------------------------------


def test_field_selectors_cover_every_expected_column():
    """Nenhuma coluna do contrato de `data_loader` pode ficar sem mapeamento."""
    assert set(FIELD_SELECTORS) == set(EXPECTED_COLUMNS)


def test_field_selectors_have_no_ambiguous_or_duplicate_selectors():
    """Cada seletor (primário e fallback) deve ser único entre as colunas —
    caso contrário, dois campos diferentes poderiam ser preenchidos com o
    mesmo elemento (mapeamento ambíguo)."""
    css_selectors = [selectors["css"] for selectors in FIELD_SELECTORS.values()]
    xpath_selectors = [selectors["xpath_fallback"] for selectors in FIELD_SELECTORS.values()]

    assert len(css_selectors) == len(set(css_selectors))
    assert len(xpath_selectors) == len(set(xpath_selectors))


def test_field_selectors_xpath_fallback_matches_exact_column_label():
    """O fallback por `<label>` deve referenciar literalmente o nome da
    coluna, evitando ambiguidade entre colunas com nomes parecidos (ex.
    'Role in Company' vs. qualquer outra)."""
    for column, selectors in FIELD_SELECTORS.items():
        assert f"'{column}'" in selectors["xpath_fallback"]


def test_fill_record_raises_keyerror_for_incomplete_record_without_touching_driver():
    """Falha rápido e claro se o registro não tiver todas as colunas
    obrigatórias, sem sequer precisar de um WebDriver real."""
    page = ChallengePage(driver=None)  # driver nunca é usado antes do KeyError
    incomplete_record = {column: "valor" for column in COLUMNS[:-1]}

    with pytest.raises(KeyError):
        page.fill_record(incomplete_record)


# --------------------------------------------------------------------------
# Testes funcionais contra fixtures HTML locais (WebDriver headless real)
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def driver():
    drv = create_driver(headless=True)
    yield drv
    drv.quit()


@pytest.mark.parametrize(
    "order",
    [
        COLUMNS,
        list(reversed(COLUMNS)),
        COLUMNS[3:] + COLUMNS[:3],
    ],
    ids=["ordem-original", "ordem-invertida", "ordem-rotacionada"],
)
def test_locate_input_finds_correct_field_regardless_of_visual_order(driver, tmp_path, order):
    """Mesmo alternando a ordem visual dos campos (simulando a reordenação
    entre rounds do site real), cada coluna deve ser localizada no elemento
    correto — nunca por posição/índice (RNF01)."""
    html = _build_form_html(order)
    driver.get(_write_fixture(tmp_path, "form.html", html))

    page = ChallengePage(driver, timeout=5)

    for column in COLUMNS:
        element = page._locate_input(column)
        assert element.get_attribute("id") == _slugify(column)


def test_locate_input_falls_back_to_label_when_ng_reflect_name_is_missing(driver, tmp_path):
    """Se `ng-reflect-name` deixar de existir (risco documentado na Seção 9
    do PRD), o campo ainda deve ser localizado corretamente via fallback por
    `<label>`."""
    missing_column = "Email"
    html = _build_form_html(COLUMNS, missing_ng_reflect_for=missing_column)
    driver.get(_write_fixture(tmp_path, "fallback.html", html))

    page = ChallengePage(driver, timeout=5)
    element = page._locate_input(missing_column)

    assert element.get_attribute("id") == _slugify(missing_column)
    assert element.get_attribute("ng-reflect-name") is None


def test_fill_record_clears_residual_value_and_sets_correct_value_per_column(driver, tmp_path):
    """`fill_record` deve limpar valor residual (RF06) e preencher cada
    campo com o valor correspondente à sua própria coluna, mesmo com a
    ordem embaralhada."""
    shuffled_order = COLUMNS[2:] + COLUMNS[:2]
    html = _build_form_html(shuffled_order, prefill_residual_value=True)
    driver.get(_write_fixture(tmp_path, "fill.html", html))

    page = ChallengePage(driver, timeout=5)
    record = {column: f"valor-{index}" for index, column in enumerate(COLUMNS)}

    page.fill_record(record)

    for column in COLUMNS:
        element = driver.find_element(By.ID, _slugify(column))
        assert element.get_attribute("value") == record[column]
        assert "residual" not in element.get_attribute("value")


def test_start_button_locator_clicks_unique_start_button(driver, tmp_path):
    """O seletor de `start()` deve localizar e clicar no botão único de
    início, sem depender de índice de posição."""
    html = _build_form_html(COLUMNS)
    driver.get(_write_fixture(tmp_path, "start.html", html))

    page = ChallengePage(driver, timeout=5)
    page.start()

    marker = driver.find_element(By.ID, "marker")
    assert marker.text == "start-clicked"


def test_submit_button_locator_clicks_unique_submit_button(driver, tmp_path):
    """O seletor de `submit()` deve localizar e clicar no botão único de
    envio, sem depender de índice de posição."""
    html = _build_form_html(COLUMNS)
    driver.get(_write_fixture(tmp_path, "submit.html", html))

    page = ChallengePage(driver, timeout=5)
    page.submit()

    marker = driver.find_element(By.ID, "marker")
    assert marker.text == "submit-clicked"


def test_wait_for_completion_message_includes_sibling_success_rate_line(driver, tmp_path):
    """No DOM real, o título "Congratulations!" e a linha com a taxa de
    sucesso/tempo são elementos irmãos dentro do mesmo container. A
    detecção de conclusão (RF08) deve continuar funcionando só com
    "Congratulations", mas o texto retornado deve ser enriquecido
    (best-effort) com a linha irmã para permitir a extração de
    `site_reported_time` (Seção 7 do PRD)."""
    html = """<!DOCTYPE html>
<html><body>
  <div>
    <h4>Congratulations!</h4>
    <p>Your success rate is 100% ( 70 out of 70 fields) in 4751 milliseconds</p>
  </div>
</body></html>
"""
    fixture_url = _write_fixture(tmp_path, "completion.html", html)
    driver.get(fixture_url)

    page = ChallengePage(driver, timeout=5)
    message = page.wait_for_completion_message()

    assert "Congratulations" in message
    assert "4751 milliseconds" in message


def test_wait_for_completion_message_works_without_success_rate_line(driver, tmp_path):
    """A detecção de conclusão não pode depender da linha de "success
    rate": se o site mudar essa redação (ou ela não existir), a mensagem
    ainda deve ser capturada com sucesso, sem lançar `TimeoutException`."""
    html = """<!DOCTYPE html>
<html><body>
  <div><h4>Congratulations!</h4></div>
</body></html>
"""
    fixture_url = _write_fixture(tmp_path, "completion_bare.html", html)
    driver.get(fixture_url)

    page = ChallengePage(driver, timeout=5)
    message = page.wait_for_completion_message()

    assert "Congratulations" in message


def test_start_and_submit_selectors_reference_single_elements_in_fixture(driver, tmp_path):
    """Confirma que os seletores de `start()`/`submit()` não são ambíguos:
    exatamente um elemento cada na fixture local."""
    html = _build_form_html(COLUMNS)
    driver.get(_write_fixture(tmp_path, "buttons.html", html))

    assert len(driver.find_elements(By.XPATH, START_BUTTON_XPATH)) == 1
    assert len(driver.find_elements(By.CSS_SELECTOR, SUBMIT_BUTTON_CSS)) == 1
