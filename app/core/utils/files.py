"""File helper utilities used by attachment services."""
from pathlib import Path
from typing import Tuple


def split_filename(filename: str) -> Tuple[str, str]:
    path = Path(filename)
    return path.stem, path.suffix
