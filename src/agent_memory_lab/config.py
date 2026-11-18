"""Runtime defaults for the CPU-first lab."""

import os
from pathlib import Path


def configure_cpu() -> None:
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "4"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


def database_path() -> Path:
    return Path(os.getenv("AML_DB_PATH", "local/memory.sqlite3")).expanduser()
