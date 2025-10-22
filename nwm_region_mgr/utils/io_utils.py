"""Define utilities and/or help functions for file I/O.

io_utils.py

Functions:
- save_data: Save data to disk in an appropriate format based on its type and file extension
- read_table: Read a table from a file, supporting CSV and Parquet formats.

"""

from enum import Enum
from pathlib import Path
from typing import Union

import pandas as pd
import yaml
from pydantic import BaseModel

from .dict_utils import convert_enum_to_value, remove_nulls

# Module-level cache
_table_cache: dict[Path, pd.DataFrame] = {}
_file_mtime: dict[Path, float] = {}  # track modification times


def save_data(
    data: Union[pd.DataFrame, BaseModel],
    file_path: Union[str, Path],
    index: bool = False,
) -> None:
    """Save data to disk in an appropriate format based on its type and file extension.

    Args:
        data : Union[pandas.DataFrame, pydantic.BaseModel]
            The data object to save. Must be either a pandas DataFrame or a Pydantic BaseModel.

            - If `data` is a pandas DataFrame:
                - Supported file formats: `.csv`, `.parquet`.

            - If `data` is a Pydantic BaseModel:
                - Supported file format: `.yaml`.

        file_path : Union[str, pathlib.Path]
            The target file path where the data will be saved. The file extension determines the format.
        index : bool
            Whether to write row indices in the DataFrame (default: False).

    Raises:
        Exception
            If the file extension is not supported for the given data type.

        ValueError
            If `data` is neither a pandas DataFrame nor a Pydantic BaseModel.

    Notes:
        - If the directory for the specified file path does not exist, it will be created.
        - YAML files for Pydantic models are written with custom inline list formatting (if configured).

    """

    class InlineListDumper(yaml.Dumper):
        pass

    def represent_inline_list(dumper, data):
        return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)

    file_path = Path(file_path)
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(data, pd.DataFrame):
        if file_path.suffix == ".csv":
            data.to_csv(file_path, index=index)
        elif file_path.suffix == ".parquet":
            data.to_parquet(file_path, index=index)
        else:
            raise Exception(
                "Only csv and parquet formats are supported for saving DataFrame"
            )

    elif isinstance(data, BaseModel):
        if file_path.suffix != ".yaml":
            raise Exception(f"Only yaml format is supported for saving {type(data)}")

        with open(file_path, "w") as f:
            InlineListDumper.add_representer(list, represent_inline_list)
            InlineListDumper.add_representer(
                Enum, lambda dumper, data: dumper.represent_scalar("!enum", data.value)
            )

            # Convert Enum values to their string representation for YAML serialization
            data_dict = convert_enum_to_value(data.model_dump())

            # Remove None values from the data dictionary
            data_dict = remove_nulls(data_dict)

            # Dump the data to YAML file with inline list formatting
            # and without sorting keys to preserve the order of fields
            yaml.dump(
                data_dict,
                f,
                Dumper=InlineListDumper,
                sort_keys=False,
            )

    else:
        raise ValueError(
            "Unsupported data type: must be a pandas DataFrame or Pydantic BaseModel"
        )


def read_table_old(
    file_path: Path | str, dtype: dict[str, str] | None = None
) -> pd.DataFrame:
    """Read table from a csv or parquet file.

    Args:
        file_path (Path | str): Path to the file to read, with file format determined by the file extension
        (.csv or .parquet).
        dtype (dict[str, str] | None): Optional dictionary specifying the data types for specific columns.

    Returns:
        pd.DataFrame: DataFrame containing the data from the file.

    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} does not exist")

    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(file_path, dtype=dtype)
    elif suffix == ".parquet":
        df = pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    # remove leading/trailing whitespace from column names
    df.columns = df.columns.str.strip()

    return df


def read_table(
    file_path: Path | str, dtype: dict[str, str] | None = None, refresh: bool = False
) -> pd.DataFrame:
    """Read a table from CSV, TSV, or Parquet with caching and optional automatic refresh.

    Args:
        file_path (Path | str): Path to the file to read. Supported formats are CSV, TSV, and Parquet.
        dtype (dict[str, str] | None): Optional dictionary specifying the data types for specific columns.
        refresh (bool): If True, forces re-reading the file even if it is cached. Default is False.

    Returns:
        pd.DataFrame: DataFrame containing the data from the file.

    """
    file_path = Path(file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} does not exist")

    # Check if cached and file not changed
    mtime = file_path.stat().st_mtime
    if file_path in _table_cache and not refresh:
        if _file_mtime.get(file_path, 0) == mtime:
            return _table_cache[file_path]

    # Load file based on suffix
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(file_path, dtype=dtype)
    elif suffix == ".tsv":
        df = pd.read_csv(file_path, sep="\t", dtype=dtype)
    elif suffix == ".parquet":
        df = pd.read_parquet(file_path)
        if dtype:
            for col, typ in dtype.items():
                if col in df.columns:
                    df[col] = df[col].astype(typ)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    # remove leading/trailing whitespace from column names
    df.columns = df.columns.str.strip()

    # Update cache and mtime
    _table_cache[file_path] = df
    _file_mtime[file_path] = mtime

    return df
