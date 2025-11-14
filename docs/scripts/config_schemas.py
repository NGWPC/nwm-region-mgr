"""Generate documentation for configuration schemas and sample configs used in nwm-region-mgr."""

from pathlib import Path
from typing import Any, Dict, List, Literal, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from nwm_region_mgr.formreg.config_schema import (
    BestFormulation,
    FormulationCostConfig,
    FormulationGeneralSettings,
    FormulationOutputConfig,
    FormulationSpatialUnitConfig,
    FormulationSummaryScoreConfig,
    MetricConfig,
)
from nwm_region_mgr.formreg.config_schema import Config as FormConf
from nwm_region_mgr.parreg.config_schema import (
    HDBSCAN,
    URF,
    AlgoGeneral,
    AlgorithmConfig,
    AttrDatasetConfig,
    AvailableAttrsConfig,
    Birch,
    DonorConfig,
    GeneralConfig,
    Gower,
    KMeans,
    KMedoids,
    MetricEvalPeriod,
    MetricThreshold,
    ParameterOutputConfig,
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
            "metrics": MetricConfig,
            "formulation_cost": FormulationCostConfig,
            "output": FormulationOutputConfig,
            "BaseOutputConfig": BaseOutputConfig,
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
            "attr_datasets": AvailableAttrsConfig,
            "snow_cover": SnowCoverConfig,
            "algorithms": AlgorithmConfig,
            "algo_general": AlgoGeneral,
            "gower": Gower,
            "kmeans": KMeans,
            "kmedoids": KMedoids,
            "birch": Birch,
            "hdbscan": HDBSCAN,
            "output": ParameterOutputConfig,
            "BaseOutputConfig": BaseOutputConfig,
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


def field_to_dict(field: FieldInfo, value: Any = None, omit_none: bool = True) -> dict:
    """Convert a Pydantic field to a dict for YAML/schema generation."""
    type_ = getattr(field, "annotation", Any)
    description = getattr(field, "description", None) or NO_DESCRIPTION_STR

    # Handle default or default_factory
    if value is not None:
        default_value = value
    elif getattr(field, "default_factory", None) is not None:
        try:
            default_value = field.default_factory()
        except Exception:
            default_value = "<factory>"
    elif getattr(field, "default", ...) is not ...:
        default_value = field.default
    else:
        default_value = "required"

    # Handle examples: prefer outer field examples if present
    example = getattr(field, "examples", None)
    if example is None:
        example = default_value if default_value != "required" else ""

    sub_dict = None

    # Handle nested BaseModel
    if isinstance(default_value, BaseModel):
        sub_dict = pydantic_to_dict(
            type(default_value),
            type(default_value),
            instance=default_value,
            outer_examples=example,
        )
    elif isinstance(type_, type) and issubclass(type_, BaseModel):
        sub_dict = pydantic_to_dict(type_, type_, outer_examples=example)
    else:
        # Dict[str, BaseModel]
        origin = get_origin(type_)
        args = get_args(type_)
        if (
            origin in (dict, Dict)
            and len(args) == 2
            and isinstance(args[1], type)
            and issubclass(args[1], BaseModel)
        ):
            value_type = args[1]
            if isinstance(default_value, dict):
                # Map examples if provided
                if isinstance(example, dict):
                    sub_dict = {
                        k: pydantic_to_dict(
                            value_type, value_type, outer_examples=example.get(k)
                        )
                        for k in default_value.keys()
                    }
                else:
                    sub_dict = {
                        k: pydantic_to_dict(value_type, value_type)
                        for k in default_value.keys()
                    }
            else:
                sub_dict = pydantic_to_dict(value_type, value_type)
    return {
        "type": type_,
        "description": description,
        "default": default_value,
        "example": example,
        "sub_dict": sub_dict,
    }


def pydantic_to_dict(
    model_cls: type[BaseModel],
    base_cls: type[BaseModel],
    instance: BaseModel | None = None,
    outer_examples: Any = None,
    start_fields: list[str] = ["general"],
    end_fields: list[str] = ["output", "algorithms"],
) -> dict[str, dict]:
    """Convert a Pydantic model to dict, optionally using an instance.

    Only child-only fields are included in the 'general' section.
    Always starts with start_fields and ends with end_fields.

    """
    dict_rep = {}

    # Fields inherited from base_cls (to exclude in general)
    base_fields = set(base_cls.model_fields.keys()) if model_cls != base_cls else set()

    # Ordered field names
    all_fields = list(model_cls.model_fields.keys())
    middle_fields = [f for f in all_fields if f not in start_fields + end_fields]
    ordered_fields = start_fields + middle_fields + end_fields

    for name in ordered_fields:
        if name not in model_cls.model_fields:
            continue
        field = model_cls.model_fields[name]

        # Handle 'general' section: only child-only fields
        if name == "general" and model_cls != base_cls:
            general_sub_dict = {}
            for sub_name, sub_field in field.annotation.model_fields.items():
                if sub_name not in base_fields:
                    # Pass instance value if present
                    value = (
                        getattr(instance.general, sub_name, None) if instance else None
                    )
                    general_sub_dict[sub_name] = field_to_dict(sub_field, value=value)

            dict_rep[name] = {
                "description": getattr(field, "description", NO_DESCRIPTION_STR),
                "sub_dict": general_sub_dict,
            }
            continue

        # Other sections: all fields
        value = getattr(instance, name, None) if instance else None
        dict_rep[name] = field_to_dict(field, value=value)

        # Override example with outer_examples if provided
        if isinstance(outer_examples, dict) and name in outer_examples:
            dict_rep[name]["example"] = outer_examples[name]

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


def is_dict_of_basemodel(field_dict: dict) -> bool:
    """Check if a field dict represents a Dict[str, BaseModel]-like field."""
    type_ = field_dict.get("type")
    if type_ is None:
        return False
    origin = get_origin(type_)
    args = get_args(type_)
    return (
        origin in (dict, Dict)
        and len(args) == 2
        and isinstance(args[1], type)
        and issubclass(args[1], BaseModel)
    )


def pydantic_dict_to_lines(dict_rep: dict, indent: int = 0) -> list[str]:
    """Convert a pydantic model to lines in the YAML format."""
    lines = []
    tmp_ind = " " * indent

    for k, v in dict_rep.items():
        comment = (
            f" #{v.get('description')}"
            if v.get("description") != NO_DESCRIPTION_STR
            else ""
        )

        # If sub_dict exists, recurse except for fields of type dict{str, BaseModel}, so that examples defined in
        # format of dict{str: BaseModel} are preserved.
        if v.get("sub_dict") is not None and not is_dict_of_basemodel(v):
            lines.append(f"{tmp_ind}{k}:{comment}")
            lines.extend(pydantic_dict_to_lines(v["sub_dict"], indent + INDENT_LEVEL))
            continue

        # Skip fields without examples
        if v.get("example") is None:
            continue

        # Convert value to string
        val = v["example"]
        if isinstance(val, str):
            val = f"'{val}'"
        elif isinstance(val, dict):
            lines.append(f"{tmp_ind}{k}:{comment}")
            lines.extend(dict_to_yaml(val, indent + INDENT_LEVEL))
            continue

        lines.append(f"{tmp_ind}{k}: {val}{comment}")

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
    dict_rep = pydantic_to_dict(
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
    dict_rep = pydantic_to_dict(model_cls, BaseGeneralConfig)

    # remove those fields that are not child-only in 'general' section
    if model_cls in (FormulationGeneralSettings, GeneralConfig):
        base_fields = set(BaseGeneralConfig.model_fields.keys())
        for k in list(dict_rep.keys()):
            if k in base_fields:
                dict_rep.pop(k)

    # Make markdown table
    headers = ["Field", "Type(s)", "Default", "Example(s)", "Description"]
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]

    for name, field_dict in dict_rep.items():
        table.append(
            f"| {name} | {type_to_str(field_dict['type'])} | "
            f"{field_dict['default']} | {field_dict['example']} | {field_dict['description']} |"
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
