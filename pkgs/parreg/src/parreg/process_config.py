import yaml
from typing import Any
from pydantic import BaseModel,ValidationError
import re
from pathlib import Path
from . import config_schema as cs

def recursive_substitute(model: Any, context: dict[str, Any]) -> Any:
    """
    Recursively substitute placeholders in a Pydantic model, dictionary, or string.
    
    Args:
        model: A Pydantic model instance, a dictionary, or a string.
        context: A dictionary of substitution variables.
    
    Return:
        The Pydantic model instance, dictionary or string after substitution

    """

    if isinstance(model, BaseModel):
        # For Pydantic models, iterate over their fields
        items = model.__dict__.items()
    elif isinstance(model, dict):
        # For dictionaries, iterate over the keys and values
        items = model.items()
    elif isinstance(model, str):
        # For strings, perform the substitution directly
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, model)
        new_value = model
        for match in matches:
            if match in context:
                new_value = new_value.replace(f'{{{match}}}', str(context[match]))
        return new_value  # Return the modified string if it's just a string
    else:
        # If the model is not a dictionary, string, or BaseModel, return it unchanged
        return model

    # Iterate over items in the model (whether it's a BaseModel or dictionary)
    for field_name, value in items:
        if isinstance(value, (BaseModel, dict, str)):
            # Recursively substitute for nested models, dictionaries, or strings
            new_value = recursive_substitute(value, context)
            if isinstance(model, BaseModel):
                setattr(model, field_name, new_value)
            else:
                model[field_name] = new_value

    return model


def validate_by_section(config:dict) -> dict:
    """
    Perform pydantic validation separately for different sections of the config file to 
    allow specific validation for certain sections

    Args:
        config: dictionary of config prior to validation
    
    Return:
        Dictionary of config after validation

    """

    section_map = {
        'general': cs.GeneralConfig,
        'file_io': cs.FileIOConfig,
        'algorithms': cs.Algorithm,
    }

    algorithm_map = {
        'general': cs.AlgoGeneral,
        'gower': cs.Gower,
        'urf': cs.URF,
        'kmeans': cs.KMeans,
        'kmedoids': cs.KMedoids,
        'hdbscan': cs.HDBSCAN,
        'birch': cs.Birch,
    }

    valid_config = dict()
    for section_name, section_content in config.items():

        if section_name != 'algorithms':
            section = section_map[section_name]
            valid_config[section_name] = section(**section_content)
        else:
            # Loop through each algorithm 
            general = section_content["general"]
            validated_algorithms = {}
            for alg_name, alg_specific in section_content.items():

                alg1 = algorithm_map[alg_name]

                if alg_name == "general":                    
                    validated_algorithms[alg_name] = alg1(**alg_specific)
                if alg_name not in algorithm_map:
                    raise ValueError(f"No model defined for algorithm: {alg_name}")

                # Merge general algorithm into specific algorithm
                merged = {**general, **alg_specific}

                # Validate
                validated_algorithms[alg_name] = alg1(**merged) 

            valid_config[section_name] = validated_algorithms 

    return valid_config       

def load_and_validate_config(file_path: str):
    """
    Load a YAML file, validate its structure using Pydantic, and substitue placeholders in the config.

    Args: 
        file_path: path to the config file
    
    """
    try:
        with open(Path(file_path), "r") as file:
            data = yaml.safe_load(file)
        
        # validate the config
        validated_config = validate_by_section(data)
        config = cs.Config(**validated_config)

        # substitute placeholders in the config
        context = {
            "domain": config.general.domain,
            "run_name": config.general.run_name,
            "base_dir": config.file_io.base_dir,
        }        
        config = recursive_substitute(config, context) 

        return config
        
    except ValidationError as e:
        raise Exception(f'Validation Error: {e}')
    except Exception as e:
        raise Exception(f'Error loading YAML file: {e}')
