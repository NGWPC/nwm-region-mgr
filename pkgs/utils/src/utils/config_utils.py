"""Utility functions for loading and validating configuration files using Pydantic and YAML.

config_utils.py

Functions:
    - load_and_validate_config: Load a YAML file, validate its structure using Pydantic, and substitute placeholders in the config.

"""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from .io_utils import save_data
from .string_utils import recursive_substitute

logger = logging.getLogger(__name__)


def load_and_validate_config(file_path: str, config_schema: BaseModel = Field(...)) -> BaseModel:
    """Load a YAML file, validate its structure using Pydantic, and substitute placeholders in the config.

    Args:
        file_path: path to the config file
        config_schema: Pydantic model to validate the config structure

    Returns:
        Config object with validated structure

    """
    try:
        with open(Path(file_path), "r") as file:
            data = yaml.safe_load(file)

        # validate the config
        config = config_schema(**data)

        return config

    except ValidationError as e:
        raise Exception(f"Validation Error: {e}")
    except Exception as e:
        raise Exception(f"Error loading YAML file: {e}")


def substitute_placeholders(config: BaseModel) -> BaseModel:
    """Substitute placeholders in the config with actual values.

    Args:
        config: Config object with placeholders

    Returns:
        Config object with placeholders substituted

    """
    # resolve placeholders in the config
    context = {
        "domain": config.general.domain,
        "run_name": config.general.run_name,
        "base_dir": config.general.base_dir,
        "vpu_list": config.general.vpu_list,
    }
    config = recursive_substitute(config, context)

    return config


def save_config(config: BaseModel, filename: str = None) -> None:
    """Save the final configuration after validation and substitution.

    Args:
        config: Config object to save
        filename: Optional file name to save the config. If not provided, the path must be a file.

    Raises:
        ValueError: If the output path is a directory and no file name is provided.

    """
    # save final config after validation and substitution
    out = config.output.config_final
    if out.save:
        logger.info(f"Saving final config to {out.path}")
        if Path(out.path).suffix != "":  # if the path is a file
            save_data(config, Path(out.path))
        elif Path(out.path).suffix == "":  # if the path is a directory
            if filename and out.format:
                save_data(config, Path(out.path, filename + "." + out.format))
            else:
                raise ValueError(
                    f"save_config: filename and format must be provided if path is a directory: {out.path}"
                )
    else:
        logger.info("Not saving the final config.")
