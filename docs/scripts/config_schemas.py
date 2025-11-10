from pathlib import Path
from typing import Any, Dict, List, Literal, Type, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

# from pydantic_core import PydanticUndefinedType
from nwm_region_mgr.formreg.config_schema import (
    BestFormulation,
    FormulationCostConfig,
    FormulationGeneralSettings,
    FormulationSpatialUnitConfig,
    FormulationSummaryScoreConfig,
    MetricConfig,
)
from nwm_region_mgr.formreg.config_schema import Config as FormConf
from nwm_region_mgr.parreg.config_schema import (
    AlgoGeneral,
    AlgorithmConfig,
    AttrDatasetConfig,
    DonorConfig,
    GeneralConfig,
    MetricEvalPeriod,
    MetricThreshold,
    SnowCoverConfig,
)
from nwm_region_mgr.parreg.config_schema import Config as ParConf
from nwm_region_mgr.utils.config_utils import (
    BaseGeneralConfig,
    BaseOutputConfig,
    FieldCrosswalk,
    LayerCrosswalk,
    LoggingConfig,
)

INDENT_LEVEL = 2
YAML_COMMENT_BUFFER = 5
NO_DESCRIPTION_STR = "No description provided"
DOCS_TO_CREATE = {
    "config_general.yaml": {
        "example_file_class": (BaseGeneralConfig, "general"),
        "schemas": {
            "general": BaseGeneralConfig,
            "id_col": FieldCrosswalk,
            "layer_name": LayerCrosswalk,
            "logging": LoggingConfig,
        },
    },
    "config_formreg.yaml": {
        "example_file_class": (FormConf,),
        "schemas": {
            "general": FormulationGeneralSettings,
            "spatial_unit": FormulationSpatialUnitConfig,
            "best_formulation": BestFormulation,
            "summary_score": FormulationSummaryScoreConfig,
            "metric_eval_period": MetricEvalPeriod,
            "metric": MetricConfig,
            "formulation_cost": FormulationCostConfig,
        },
    },
    "config_parreg.yaml": {
        "example_file_class": (ParConf, "general"),
        "schemas": {
            "general": GeneralConfig,
            "donor": DonorConfig,
            "metric_eval_period": MetricEvalPeriod,
            "metric_threshold": MetricThreshold,
            "attr_datasets_config": AttrDatasetConfig,
            "snow_cover": SnowCoverConfig,
            "algorithms": AlgorithmConfig,
            "algorithm": AlgoGeneral,
            "output": BaseOutputConfig,
        },
    },
}


def type_to_str(tp):
    """Convert a type hint to a readable string for markdown."""
    origin = get_origin(tp)
    args = get_args(tp)

    if origin is None:  # Simple case e.g., str
        return getattr(tp, "__name__", str(tp))
    elif origin in (list, List):
        return f"List[{type_to_str(args[0])}]" if args else "List"
    elif origin in (dict, Dict):
        return (
            f"Dict[{type_to_str(args[0])}, {type_to_str(args[1])}]" if args else "Dict"
        )
    elif origin is Literal:
        return "str = " + " \\| ".join(map(str, args))
    elif len(args) > 1:
        return " \\| ".join(type_to_str(a) for a in args)
    else:  # Catch others
        return str(tp)


def field_to_dict(field: FieldInfo) -> dict:
    """Convert a Pydantic field to a dictionary suitable for YAML generation."""
    type_ = getattr(field, "annotation", Any)

    # Description
    description = getattr(field, "description", None) or NO_DESCRIPTION_STR

    # Default value
    default = getattr(field, "default", ...)
    default_str = "required" if default is ... else default

    # Example: prefer child examples if defined
    example = getattr(field, "examples", None)
    if example is None:
        example = default_str if default_str != "required" else ""

    sub_dict = None

    # Case 1: nested BaseModel instance or type
    if isinstance(default, BaseModel):
        sub_dict = pydantic_to_dict_subclass_only(type(default), type(default))
    elif isinstance(type_, type) and issubclass(type_, BaseModel):
        sub_dict = pydantic_to_dict_subclass_only(type_, type_)
    else:
        # Case 2: dict[str, BaseModel]
        origin = get_origin(type_)
        args = get_args(type_)
        if (
            origin in (dict, Dict)
            and len(args) == 2
            and isinstance(args[1], type)
            and issubclass(args[1], BaseModel)
        ):
            value_type = args[1]
            # Always recurse on the type, ignoring the 'example' dict
            sub_dict = pydantic_to_dict_subclass_only(value_type, value_type)

    return {
        "type": type_,
        "description": description,
        "default": default_str,
        "example": example,
        "sub_dict": sub_dict,
    }


def pydantic_to_dict_subclass_only(
    model_cls: type[BaseModel],
    base_cls: type[BaseModel],
    start_fields: list[str] = ["general"],
    end_fields: list[str] = ["output", "algorithms"],
) -> dict[str, dict]:
    """Convert a Pydantic model to dict suitable for YAML generation.

    1. Orders fields with start_fields first, end_fields last.
    2. Excludes fields from base_cls only for the 'general' section.
    3. Recursively handles nested BaseModel fields including dict[str, BaseModel].
    """
    dict_rep = {}

    # Identify inherited fields (applies only to the 'general' section)
    base_fields = set(base_cls.model_fields.keys()) if model_cls != base_cls else set()

    # Compute ordered field names
    all_fields = list(model_cls.model_fields.keys())
    middle_fields = [f for f in all_fields if f not in start_fields + end_fields]
    ordered_fields = start_fields + middle_fields + end_fields

    for name in ordered_fields:
        if name not in model_cls.model_fields:
            continue

        field = model_cls.model_fields[name]

        # Only exclude inherited fields from the general section
        if name == "general" and model_cls != base_cls and name in base_fields:
            continue

        # Exclude inherited fields only for general section
        if name == "general" and model_cls != base_cls:
            general_sub_dict = {}
            for sub_name, sub_field in field.annotation.model_fields.items():
                if sub_name not in base_fields:
                    general_sub_dict[sub_name] = field_to_dict(sub_field)

            # Include description for the 'general' field itself
            dict_rep[name] = {
                "description": getattr(field, "description", NO_DESCRIPTION_STR),
                "sub_dict": general_sub_dict,
            }
            continue

        # Skip required fields without default
        if getattr(field, "default", ...) is ...:
            continue

        dict_rep[name] = field_to_dict(field)

    return dict_rep


def pydantic_to_dict(model_cls: type[BaseModel]) -> dict[str, dict]:
    """Convert a pydantic model to an easier to work with Python dict."""
    dict_rep = {}
    for name, field in model_cls.model_fields.items():
        if getattr(field, "default", None) is not None:
            dict_rep[name] = field_to_dict(field)
    return dict_rep


def dict_to_yaml(dict_rep: dict, indent: int = 0) -> list[str]:
    """Convert a python dictionary to YAML with added indent customization."""
    lines = []
    tmp_ind = " " * indent
    for i in dict_rep:
        if isinstance(dict_rep[i], dict):
            lines.append(f"{tmp_ind}{i}:")
            lines.extend(dict_to_yaml(dict_rep[i], indent + INDENT_LEVEL))
        else:
            lines.append(f"{tmp_ind}{i}: {str(dict_rep[i])}")
    return lines


def pydantic_dict_to_lines(dict_rep: dict, indent: int = 0) -> list[str]:
    """Convert a pydantic model to lines in the YAML format."""
    # Make initial dict
    lines = []
    tmp_ind = " " * indent
    for k, v in dict_rep.items():
        # Parse comment
        if v["description"] != NO_DESCRIPTION_STR:
            comment = f" #{v['description']}"
        else:
            comment = ""

        if v["sub_dict"] is None:  # Not sub pydantic class
            if isinstance(v["example"], dict):  # Handle sub dicts
                lines.append(f"{tmp_ind}{k}:{comment}")
                lines.extend(dict_to_yaml(v["example"], indent + INDENT_LEVEL))
            else:
                if isinstance(v["example"], str):  # Handle strings
                    str_ = "'" + v["example"] + "'"
                else:
                    str_ = str(v["example"])
                lines.append(f"{tmp_ind}{k}: {str_}{comment}")
        else:  # Pydantic subclass
            lines.append(f"{tmp_ind}{k}:{comment}")
            lines.extend(pydantic_dict_to_lines(v["sub_dict"], indent + INDENT_LEVEL))
    return lines


def justify_yaml_comments(lines: list[str]):
    """Update a YAML file so that comments all start at same column."""
    max_len = 0
    for i in lines:
        cur_len = len(i.split(" #")[0])
        max_len = max([cur_len, max_len])
    for ind, i in enumerate(lines):
        cur_len = len(i.split(" #")[0])
        lines[ind] = i.replace(
            " #", " #" + ("-" * ((max_len + YAML_COMMENT_BUFFER) - cur_len))
        )

    return lines


def generate_yaml_template(model_cls: type[BaseModel], top_key: str = None) -> str:
    """Generate YAML file using examples and descriptions."""
    # Convert BaseModel to dict for easier manipulation
    dict_rep = pydantic_to_dict_subclass_only(
        model_cls,
        BaseGeneralConfig,
    )

    # Build initial yaml lines
    if top_key is not None:
        lines = [f"{top_key}:"]
        indent = INDENT_LEVEL
    else:
        lines = []
        indent = 0
    lines.extend(pydantic_dict_to_lines(dict_rep, indent))
    lines = justify_yaml_comments(lines)
    return "\n".join(lines)


def generate_markdown_table(model_cls: type[BaseModel]) -> str:
    """Convert a pydantic model to a markdown table."""
    # Convert BaseModel to dict for easier manipulation
    # dict_rep = pydantic_to_dict(model_cls)
    dict_rep = pydantic_to_dict_subclass_only(model_cls, BaseGeneralConfig)

    # Make markdown table
    headers = ["Field", "Type(s)", "Description", "Default", "Example(s)"]
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]

    for name, field_dict in dict_rep.items():
        table.append(
            f"| {name} | {type_to_str(field_dict['type'])} | "
            f"{field_dict['description']} | {field_dict['default']} | {field_dict['example']} |"
        )

    return "\n".join(table)


def main(docs_to_create: dict) -> None:
    """Create markdown file documentation for the specified pydantic models."""
    lines = []
    for i in docs_to_create:
        lines.append(f"### {i}")

        lines.append("#### Example File")
        lines.append("```yaml")
        lines.append(generate_yaml_template(*docs_to_create[i]["example_file_class"]))
        lines.append("```")

        for j in docs_to_create[i]["schemas"]:
            lines.append(f"#### Schema Reference ({j})")
            lines.append(generate_markdown_table(docs_to_create[i]["schemas"][j]))

    Path("config_docs.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main(DOCS_TO_CREATE)
