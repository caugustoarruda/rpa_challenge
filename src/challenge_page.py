"""Page Object do rpachallenge.com: seletores estáveis e ações do formulário.

## Estrutura do DOM (inspecionado em rpachallenge.com, Angular)

Após clicar em "Start", o formulário é renderizado como uma lista de campos
(`<rpa1-field>`) dentro de `<div class="row">`. Cada campo tem, mesmo com a
posição visual embaralhada a cada round, a seguinte estrutura estável:

    <rpa1-field ng-reflect-dictionary-value="First Name" ...>
      <div ...>
        <label>First Name</label>
        <input ng-reflect-name="labelFirstName" id="<aleatório>" name="<aleatório>">
      </div>
    </rpa1-field>

Dois atributos permanecem estáveis entre rounds (o que muda é apenas a
*posição* do bloco `<rpa1-field>` dentro do `<div class="row">`):

1. `ng-reflect-name` no `<input>` — atributo de depuração que o Angular expõe
   refletindo o `[name]` do `FormControl` (ex.: `labelFirstName`,
   `labelLastName`, `labelCompanyName`, `labelRole`, `labelAddress`,
   `labelEmail`, `labelPhone`). É o seletor **primário** usado aqui.
2. O texto do `<label>` irmão do `<input>`, que reproduz literalmente o nome
   da coluna da planilha (ex. "First Name", "Role in Company"). Usado como
   **fallback** documentado (RNF01/Seção 9 do PRD) caso `ng-reflect-name`
   deixe de existir em uma atualização futura do site — o `id`/`name`
   gerados aleatoriamente a cada render **não** são estáveis e por isso
   nunca são usados para localizar campos.

O botão "Submit" é um `<input type="submit" value="Submit">` único na
página (fora da lista de campos reordenável), e o botão "Start" é um
`<button>` com texto "Start", presentes uma única vez cada — não sofrem
reordenação, mas ainda assim são localizados por atributo/texto, nunca por
índice.
"""

from __future__ import annotations

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.data_loader import EXPECTED_COLUMNS

# Mapa único coluna da planilha -> seletores do campo correspondente.
# Fonte única da verdade (RF05/Seção 6 do PRD): nenhuma outra estrutura
# duplica esse mapeamento em `challenge_page.py` nem em outro módulo.
#
# - "css": seletor primário, por `ng-reflect-name` (atributo estável).
# - "xpath_fallback": seletor alternativo, pelo texto do `<label>` irmão do
#   input, usado apenas se o seletor primário não localizar o elemento a
#   tempo (ex. atributo removido em uma atualização do site).
FIELD_SELECTORS: dict[str, dict[str, str]] = {
    "First Name": {
        "css": "input[ng-reflect-name='labelFirstName']",
        "xpath_fallback": "//label[normalize-space(.)='First Name']/following-sibling::input[1]",
    },
    "Last Name": {
        "css": "input[ng-reflect-name='labelLastName']",
        "xpath_fallback": "//label[normalize-space(.)='Last Name']/following-sibling::input[1]",
    },
    "Company Name": {
        "css": "input[ng-reflect-name='labelCompanyName']",
        "xpath_fallback": "//label[normalize-space(.)='Company Name']/following-sibling::input[1]",
    },
    "Role in Company": {
        "css": "input[ng-reflect-name='labelRole']",
        "xpath_fallback": "//label[normalize-space(.)='Role in Company']/following-sibling::input[1]",
    },
    "Address": {
        "css": "input[ng-reflect-name='labelAddress']",
        "xpath_fallback": "//label[normalize-space(.)='Address']/following-sibling::input[1]",
    },
    "Email": {
        "css": "input[ng-reflect-name='labelEmail']",
        "xpath_fallback": "//label[normalize-space(.)='Email']/following-sibling::input[1]",
    },
    "Phone Number": {
        "css": "input[ng-reflect-name='labelPhone']",
        "xpath_fallback": "//label[normalize-space(.)='Phone Number']/following-sibling::input[1]",
    },
}

# Garante, na importação do módulo, que o mapa acima cobre exatamente as
# colunas do contrato de dados de `data_loader.py` — nenhuma coluna sem
# mapeamento e nenhuma coluna extra. O mesmo invariante é reforçado por
# `tests/test_field_mapping.py`.
assert set(FIELD_SELECTORS) == set(EXPECTED_COLUMNS), (
    "FIELD_SELECTORS deve mapear exatamente as colunas de "
    "data_loader.EXPECTED_COLUMNS."
)

# Botões únicos na página (não fazem parte da lista de campos reordenável).
START_BUTTON_XPATH = "//button[normalize-space(.)='Start']"
SUBMIT_BUTTON_CSS = "input[type='submit']"

DEFAULT_TIMEOUT = 10


class ChallengePage:
    """Page Object do formulário dinâmico do RPA Challenge.

    Concentra todos os seletores (XPath/CSS) do desafio; nenhum outro módulo
    do projeto deve conter lógica de localização de elementos. Expõe três
    ações correspondentes a um único round do desafio — o encadeamento dos
    10 rounds é responsabilidade do módulo de orquestração (`runner.py`).
    """

    def __init__(self, driver: WebDriver, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.driver = driver
        self.timeout = timeout

    def start(self) -> None:
        """Clica em "Start" e aguarda o formulário (primeiro round) renderizar.

        Usa `WebDriverWait`/`expected_conditions` tanto para o botão ficar
        clicável quanto para confirmar que ao menos um campo do formulário
        já está presente no DOM antes de devolver o controle ao chamador.
        """
        wait = WebDriverWait(self.driver, self.timeout)

        start_button = wait.until(EC.element_to_be_clickable((By.XPATH, START_BUTTON_XPATH)))
        start_button.click()

        # Qualquer um dos seletores primários serve como sinal de que o
        # formulário foi renderizado; combinamos todos numa única consulta
        # CSS (lista separada por vírgula) para não depender de um campo
        # específico ser o "primeiro" a aparecer.
        any_field_css = ", ".join(selectors["css"] for selectors in FIELD_SELECTORS.values())
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, any_field_css)))

    def fill_record(self, record: dict[str, str]) -> None:
        """Preenche um round do formulário com os valores de `record`.

        Para cada coluna esperada, localiza o input correspondente **a
        partir do DOM atual** (nunca reaproveitando `WebElement` de uma
        chamada anterior, o que evitaria `StaleElementReferenceException`
        após o re-render do Angular), limpa o campo com `clear()` e digita
        o valor com `send_keys()` — sem qualquer `execute_script` (RNF06).

        Args:
            record: dict com exatamente as chaves de
                `data_loader.EXPECTED_COLUMNS` (contrato de
                `data_loader.load_records_from_excel`).

        Raises:
            KeyError: se `record` não contiver alguma coluna obrigatória.
            NoSuchElementException: se um campo não puder ser localizado nem
                pelo seletor primário nem pelo fallback.
        """
        missing_columns = [column for column in FIELD_SELECTORS if column not in record]
        if missing_columns:
            raise KeyError(
                f"Registro não contém as colunas obrigatórias: {missing_columns}."
            )

        for column in FIELD_SELECTORS:
            value = record[column]
            input_element = self._locate_input(column)
            input_element.clear()
            input_element.send_keys(value)

    def submit(self) -> None:
        """Clica em "Submit", re-localizando o botão a partir do DOM atual."""
        wait = WebDriverWait(self.driver, self.timeout)
        submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, SUBMIT_BUTTON_CSS)))
        submit_button.click()

    def _locate_input(self, column: str) -> WebElement:
        """Localiza o `<input>` de `column` pelo seletor primário, com fallback.

        Tenta primeiro o seletor por `ng-reflect-name` (estável entre
        rounds); se o elemento não ficar clicável dentro do timeout,
        tenta o fallback por texto do `<label>` associado (Seção 9 do PRD:
        mitigação para o risco de o atributo estável mudar numa atualização
        do site).
        """
        selectors = FIELD_SELECTORS[column]
        wait = WebDriverWait(self.driver, self.timeout)

        try:
            return wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selectors["css"]))
            )
        except TimeoutException:
            pass

        try:
            return wait.until(
                EC.element_to_be_clickable((By.XPATH, selectors["xpath_fallback"]))
            )
        except TimeoutException as exc:
            raise NoSuchElementException(
                f"Campo '{column}' não encontrado nem pelo seletor primário "
                f"('{selectors['css']}') nem pelo fallback "
                f"('{selectors['xpath_fallback']}')."
            ) from exc
