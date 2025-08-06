"""Define utilities and/or help functions for string manipulation.

string_utils.py

Functions:
- expand_with_vpu: Expand a string with {vpu_list} placeholders using a list of VPU codes from the context.
- recursive_substitute: Recursively substitute placeholders in a Pydantic model, dictionary, or string.

"""

from itertools import product
from typing import Any

from pydantic import BaseModel

# def expand_with_vpu(string_with_vpu: str, context: dict) -> dict:
#     """Expand a string with {vpu_list} placeholders.

#     Expand a string with {vpu_list} placeholders using a list of VPU codes from the context.
#     Returns a dictionary where keys are vpu codes and values are the formatted strings.
#     """
#     if "{vpu_list}" not in string_with_vpu or "vpu_list" not in context:
#         return {"default": string_with_vpu.format(**context)}

#     return {vpu: string_with_vpu.format(**{**context, "vpu_list": vpu}) for vpu in context["vpu_list"]}


# def recursive_substitute(obj: Any, context: dict) -> Any:
#     """Recursively substitute placeholders.

#     Recursively substitute placeholders in config, be it a Pydantic model, dictionary, or string.

#     Args:
#         obj: A Pydantic model instance, a dictionary, or a string.
#         context: A dictionary of substitution variables.

#     Returns:
#         The Pydantic model instance, dictionary or string after substitution

#     """
#     if isinstance(obj, BaseModel):
#         # Convert Pydantic model to dict, substitute, then reconstruct the model
#         data = obj.model_dump()
#         substituted = recursive_substitute(data, context)
#         return obj.__class__(**substituted)

#     elif isinstance(obj, dict):
#         return {k: recursive_substitute(v, context) for k, v in obj.items()}

#     elif isinstance(obj, str):
#         try:
#             if "{vpu_list}" in obj and "vpu_list" in context:
#                 # If the string contains {vpu} and vpu_list is in context, expand it and substitute the placeholders
#                 return expand_with_vpu(obj, context)
#             else:  # Otherwise, just substitute the placeholders
#                 return obj.format(**context)
#         except KeyError:
#             return obj  # leave unchanged if context is incomplete

#     else:
#         return obj  # return as-is if not str, dict, or BaseModel


def expand_with_lists(template_str: str, context: dict) -> dict | str:
    """Expand a string with list placeholders using Cartesian product.

    Always returns a dict if any list placeholders are involved — even if only one result.
    Otherwise, returns a plain substituted string.
    """
    # Find all list-type keys in context used in the string
    list_keys = [k for k in context if isinstance(context[k], list) and f"{{{k}}}" in template_str]

    if not list_keys:
        # No list placeholders → do a simple substitution
        return template_str.format(**context)

    # Get all combinations of list values
    combinations = list(product(*[context[k] for k in list_keys]))

    result = {}
    for combo in combinations:
        sub_context = context.copy()
        sub_context.update(dict(zip(list_keys, combo)))
        key = "_".join(str(v) for v in combo)
        result[key] = template_str.format(**sub_context)

    return result


def recursive_substitute(obj: Any, context: dict) -> Any:
    """Recursively substitute placeholders in nested structures."""
    if isinstance(obj, BaseModel):
        data = obj.model_dump()
        substituted = recursive_substitute(data, context)
        return obj.__class__(**substituted)

    elif isinstance(obj, dict):
        return {k: recursive_substitute(v, context) for k, v in obj.items()}

    elif isinstance(obj, str):
        try:
            return expand_with_lists(obj, context)
        except KeyError:
            return obj  # leave unchanged if substitution fails

    else:
        return obj


def recursive_substitute_multi_lists(obj: Any, context: dict) -> Any:
    """Recursively substitute placeholders, handling multiple lists with Cartesian expansion."""
    if isinstance(obj, BaseModel):
        data = obj.model_dump()
        substituted = recursive_substitute_multi_lists(data, context)
        return obj.__class__(**substituted)

    elif isinstance(obj, dict):
        return {k: recursive_substitute_multi_lists(v, context) for k, v in obj.items()}

    elif isinstance(obj, str):
        try:
            # Identify list-type variables that appear in the string
            list_keys = [k for k, v in context.items() if isinstance(v, list) and f"{{{k}}}" in obj]

            if not list_keys:
                return obj.format(**context)

            # Create combinations of list values
            list_values = [context[k] for k in list_keys]
            print(f"List keys: {list_keys}, List values: {list_values}")
            combinations = list(product(*list_values))
            print(f"Combinations: {combinations}")

            # Generate expanded strings for each combination
            results = []
            for combo in combinations:
                print(f"Processing combination: {combo}")
                print(combo)
                temp_context = context.copy()
                temp_context.update(dict(zip(list_keys, combo)))
                results.append(obj.format(**temp_context))

            return results

        except KeyError:
            return obj  # Leave unchanged if context is incomplete

    else:
        return obj
