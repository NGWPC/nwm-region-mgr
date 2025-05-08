import yaml
from typing import Any
from pydantic import BaseModel,ValidationError
import re
from pathlib import Path
from . import config_schema as cs

def expand_with_vpu(string_with_vpu: str, context: dict) -> list:
    """
    Expand a string with {vpu_list} placeholders using a list of VPU codes from the context.
    """
    
    if "{vpu_list}" not in string_with_vpu or "vpu_list" not in context:
        return [string_with_vpu.format(**context)]
    return [string_with_vpu.format(**{**context, "vpu_list": vpu}) for vpu in context["vpu_list"]]


def recursive_substitute(obj: Any, context: dict) -> Any:
    """
    Recursively substitute placeholders in config, be it a Pydantic model, dictionary, or string.
    Args:
        obj: A Pydantic model instance, a dictionary, or a string.
        context: A dictionary of substitution variables.

    Returns:
        The Pydantic model instance, dictionary or string after substitution
    """
    
    if isinstance(obj, BaseModel):
        # Convert Pydantic model to dict, substitute, then reconstruct the model
        data = obj.model_dump()
        substituted = recursive_substitute(data, context)
        return obj.__class__(**substituted)
    
    elif isinstance(obj, dict):
        return {k: recursive_substitute(v, context) for k, v in obj.items()}
    
    elif isinstance(obj, str):
        try:
            if '{vpu_list}' in obj and 'vpu_list' in context:
                # If the string contains {vpu} and vpu_list is in context, expand it and substitute the placeholders
                return expand_with_vpu(obj, context)            
            else: # Otherwise, just substitute the placeholders
                return obj.format(**context)
        except KeyError:
            return obj  # leave unchanged if context is incomplete

    else:
        return obj  # return as-is if not str, dict, or BaseModel
    

def validate_by_section(config:dict) -> dict:
    """
    Perform pydantic validation separately for different sections of the config file to 
    allow specific validation for certain sections

    Args:
        config: dictionary of config prior to validation
    
    Return:
        Dictionary of config after validation

    """
    # Define the mapping of section names to Pydantic models
    section_map = {
        'general': cs.GeneralConfig,
        'donor': cs.DonorConfig,
        'attr_datasets': cs.AttrDatasets,
        'output': cs.OutputConfig,
        'algorithms': cs.AlgorithmConfig,
    }

    # Define the mapping of algorithm names to Pydantic models
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

def find_occurrences(obj, target, path=""):
    """
    Recursively find occurrences of a target string in a Pydantic model, dictionary, or list.
    
    Args:
        obj: The object to search (can be a Pydantic model, dictionary, or list).
        target: The target string to find. 
    
    returns:
        A list of paths where the target string occurs.
    """
    occurrences = []

    if isinstance(obj, BaseModel):
        obj = obj.model_dump(exclude_unset=True)

    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            occurrences.extend(find_occurrences(v, target, new_path))
    
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            occurrences.extend(find_occurrences(item, target, new_path))
    
    elif isinstance(obj, str):
        if target in obj:
            occurrences.append(path)
    
    return occurrences


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

        # resolve placeholders in the config
        context = {
            "domain": config.general.domain,
            "run_name": config.general.run_name,
            "base_dir": config.general.base_dir,
            "vpu_list": config.general.vpu_list,
        }
        config = recursive_substitute(config, context)

        # additional validation after substitution
        config.donor.check_files()

        return config
        
    except ValidationError as e:
        raise Exception(f'Validation Error: {e}')
    except Exception as e:
        raise Exception(f'Error loading YAML file: {e}')
