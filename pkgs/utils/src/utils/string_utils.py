"""Define utilities and/or help functions for string manipulation.

string_utils.py

Functions:
- expand_with_vpu: Expand a string with {vpu_list} placeholders using a list of VPU codes from the context.
- recursive_substitute: Recursively substitute placeholders in a Pydantic model, dictionary, or string.

"""

from typing import Any

from pydantic import BaseModel


def expand_with_vpu(string_with_vpu: str, context: dict) -> dict:
    """Expand a string with {vpu_list} placeholders.

    Expand a string with {vpu_list} placeholders using a list of VPU codes from the context.
    Returns a dictionary where keys are vpu codes and values are the formatted strings.
    """
    if "{vpu_list}" not in string_with_vpu or "vpu_list" not in context:
        return {"default": string_with_vpu.format(**context)}

    return {vpu: string_with_vpu.format(**{**context, "vpu_list": vpu}) for vpu in context["vpu_list"]}


def recursive_substitute(obj: Any, context: dict) -> Any:
    """Recursively substitute placeholders.

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
            if "{vpu_list}" in obj and "vpu_list" in context:
                # If the string contains {vpu} and vpu_list is in context, expand it and substitute the placeholders
                return expand_with_vpu(obj, context)
            else:  # Otherwise, just substitute the placeholders
                return obj.format(**context)
        except KeyError:
            return obj  # leave unchanged if context is incomplete

    else:
        return obj  # return as-is if not str, dict, or BaseModel
