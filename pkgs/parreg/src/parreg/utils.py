"""This module defines utility or help functions"""

import pandas as pd
import yaml
from pathlib import Path
from typing import Union
from pydantic import BaseModel
from typing import Optional, List, Dict, Set, Union, Any
import pyarrow.parquet as pq


def remove_nulls(d):
    """
    Recursively remove None values from a dictionary or list.
    This function traverses the input data structure and removes any keys with None values
    or any elements that are None in lists. It also removes empty dictionaries.
    
    Parameters
    ----------
    d : dict or list
        The input data structure to clean. It can be a dictionary or a list. 
    
    Returns 
    -------
    dict or list
        The cleaned data structure with None values and empty dictionaries removed.

    """
    
    if isinstance(d, dict):
        return {
            k: remove_nulls(v)
            for k, v in d.items()
            if v is not None and remove_nulls(v) != {}
        }
    elif isinstance(d, list):
        return [remove_nulls(v) for v in d if v is not None]
    else:
        return d
    

def save_data(data: Union[pd.DataFrame, BaseModel], file_path: Union[str, Path]):
    """
    Save data to disk in an appropriate format based on its type and file extension.

    Parameters
    ----------
    data : Union[pandas.DataFrame, pydantic.BaseModel]
        The data object to save. Must be either a pandas DataFrame or a Pydantic BaseModel.

        - If `data` is a pandas DataFrame:
            - Supported file formats: `.csv`, `.parquet`.

        - If `data` is a Pydantic BaseModel:
            - Supported file format: `.yaml`.

    file_path : Union[str, pathlib.Path]
        The target file path where the data will be saved. The file extension determines the format.

    Raises
    ------
    Exception
        If the file extension is not supported for the given data type.

    ValueError
        If `data` is neither a pandas DataFrame nor a Pydantic BaseModel.

    Notes
    -----
    - If the directory for the specified file path does not exist, it will be created.
    - YAML files for Pydantic models are written with custom inline list formatting (if configured).
    """

    class InlineListDumper(yaml.Dumper):
        pass

    def represent_inline_list(dumper, data):
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

    file_path = Path(file_path)
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
    
    if isinstance(data, pd.DataFrame):
        if file_path.suffix == ".csv":
            data.to_csv(file_path, index=False)
        elif file_path.suffix == '.parquet':
            data.to_parquet(file_path, index=False,)
        else:
            raise Exception('Only csv and parquet formats are supported for saving DataFrame')
    
    elif isinstance(data, BaseModel):
        if file_path.suffix != '.yaml':
            raise Exception(f'Only yaml format is supported for saving {type(data)}')
        
        with open(file_path, "w") as f:
            InlineListDumper.add_representer(list, represent_inline_list)
            yaml.dump(remove_nulls(data.model_dump()), f, Dumper=InlineListDumper, sort_keys=False)
    
    else:
        raise ValueError("Unsupported data type: must be a pandas DataFrame or Pydantic BaseModel")
    
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

    missing_cols = set(columns) - set(columns_present)
    if missing_cols:
        raise ValueError(f"Missing columns in {file}: {missing_cols}")

def read_table(file_path):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} does not exist")

    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file_path)
    elif suffix == ".parquet":
        return pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")