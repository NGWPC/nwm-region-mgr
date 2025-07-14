"""Define utilities and/or help functions for validation.

validation_utils.py

Functions:
- check_columns: Check if the required columns are present in a file.

"""

from pathlib import Path
from typing import Set

import pandas as pd
import pyarrow.parquet as pq


def check_columns(file: Path | str, columns: Set[str]):
    """Check if the required columns are present in the file."""
    if isinstance(file, str):
        file = Path(file)

    if not file.exists():
        raise FileNotFoundError(f"File not found: {file}")

    suffix = file.suffix.lower()
    if suffix == ".csv":
        columns_present = [col.lower() for col in pd.read_csv(file, nrows=0).columns.tolist()]
    elif suffix == ".parquet":
        columns_present = [col.lower() for col in pq.ParquetFile(file).schema.names]
    else:
        raise ValueError("Only .csv and .parquet files are supported")

    # Check for missing columns (case insensitive)
    missing_cols = {col.lower() for col in columns} - {col.lower() for col in columns_present}
    if missing_cols:
        raise ValueError(f"Missing columns (case insensitive) in {file}: {missing_cols}")
