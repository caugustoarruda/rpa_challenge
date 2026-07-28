"""Configuração centralizada de logging da execução da automação.

Ponto único de configuração (RF11) para que todos os demais módulos usem
`logging.getLogger(__name__)` e produzam saída consistente — mesmo formato,
mesmo nível — tanto em arquivo (`<output_dir>/run.log`) quanto no console.
Deliberadamente simples: apenas o módulo `logging` da stdlib, sem wrapper ou
dependência externa (ver `.agents/05-logging-resilience.md`).
"""

from __future__ import annotations

import logging
import os

# Formato consistente exigido pelo PRD (RF11, Seção 9): timestamp, nível,
# módulo de origem e mensagem — suficiente para localizar a causa de uma
# falha sem precisar reler o código-fonte.
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILENAME = "run.log"

# Atributo usado para marcar os handlers criados por esta função, permitindo
# distingui-los de qualquer handler que outra parte do processo (ex. pytest)
# já tenha adicionado ao logger raiz.
_HANDLER_MARKER = "_rpa_challenge_handler"


def configure_logging(output_dir: str, level: int = logging.INFO) -> logging.Logger:
    """Configura o logger raiz com saída simultânea em arquivo e console.

    Idempotente (RNF08): chamar esta função múltiplas vezes no mesmo
    processo não duplica handlers nem, portanto, linhas repetidas no log —
    os handlers adicionados por uma chamada anterior são removidos antes de
    recriá-los.

    Args:
        output_dir: diretório onde `run.log` deve ser escrito; é criado se
            ainda não existir.
        level: nível mínimo de log a ser emitido (INFO por padrão; DEBUG
            para diagnóstico detalhado, ex. cada campo preenchido em um
            round).

    Returns:
        O logger raiz já configurado. Os módulos da aplicação não precisam
        usar o valor de retorno diretamente — basta chamar
        `logging.getLogger(__name__)` depois que `configure_logging` tiver
        rodado uma vez (tipicamente no início de `cli.main`).
    """
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, LOG_FILENAME)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root_logger.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    setattr(file_handler, _HANDLER_MARKER, True)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    setattr(console_handler, _HANDLER_MARKER, True)
    root_logger.addHandler(console_handler)

    return root_logger
