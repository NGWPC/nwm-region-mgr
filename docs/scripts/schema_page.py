import os
from io import BytesIO
from pathlib import Path

import boto3
import fiona
import geopandas as gpd
import pandas as pd
import yaml
from dotenv import load_dotenv

CONFIG_DIR = "sample_files/configs"
OUT_PATH_INPUT_DATA = "docs/source/tech_reference/input_data.rst"
OUT_PATH_OUTPUT_DATA = "docs/source/tech_reference/output_data.rst"


def initialize_s3_client():
    """Initialize and return an S3 client using credentials from environment variables."""
    # Load environment variables from .env
    load_dotenv()  # looks for .env in current folder

    # Read AWS credentials from environment
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")  # optional default region
    aws_token = os.getenv("AWS_SESSION_TOKEN")  # session token

    # Initialize S3 client
    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
        aws_session_token=aws_token,
    )
    return s3


def get_sample_input_files(yaml_files: list[str]) -> dict[str, str]:
    all_config = {}
    for yaml_path in yaml_files:
        with open(yaml_path, "r") as f:
            config = yaml.safe_load(f)
        all_config = deep_merge_keep_both(all_config, config)

    path_dict = unpack_dict(all_config)
    file_dict = {}
    for k, v in path_dict.items():
        v = v.replace("{domain}", all_config["general"]["domain"])
        v = v.replace("{run_name}", all_config["general"]["run_name"])
        v = v.replace("{base_dir}", all_config["general"]["base_dir"])
        v = v.replace("{vpu_list}", all_config["general"]["vpu_list"][0])

        if not os.path.exists(v) or not os.path.isfile(v):
            continue
        if "output" in k.lower():
            continue
        file_dict[k] = v
    return file_dict


def get_sample_output_files() -> dict[str, str]:
    """Return a dictionary of sample output file paths on S3 for different output types."""
    base_dir = Path("regionalization/data/sample_outputs/test")
    vpu = "03S"
    outputs = {
        "attr_data_final": base_dir
        / "attr_data_final"
        / f"attr_conus_vpu{vpu}.parquet",
        "formulations": base_dir / "formulations" / f"form_conus_vpu{vpu}.parquet",
        "formulations_pars": base_dir
        / "formulations"
        / f"form_conus_vpu{vpu}_pars.parquet",
        "pairs_gower": base_dir / "pairs" / f"pairs_gower_conus_vpu{vpu}.parquet",
        "pairs_kmeans": base_dir / "pairs" / f"pairs_kmeans_conus_vpu{vpu}.parquet",
        "pairs_msw": base_dir / "pairs" / f"pairs_kmeans_conus_vpu{vpu}_mswm.csv",
        "params": base_dir / "params" / f"formulation_params_gower_conus_vpu{vpu}.csv",
        # "spatial_distance": base_dir
        # / "spatial_distance"
        # / f"donor_receiver_dist_conus_vpu{vpu}.parquet",
        "summary_score": base_dir / "summary_score" / f"score_conus_vpu{vpu}.parquet",
    }

    descriptions = {
        "attr_data_final": (
            "Final attribute data for all catchments used during regionalization. "
            "Columns: divide_id, is_donor (whether the catchment is a donor), and various attributes "
            "prefixed by their corresponding dataset name."
        ),
        "formulations": "Formulation assignments for all catchments.",
        "formulations_pars": "Formulation parameters for all catchments.",
        "pairs_gower": "Gower distance pairs between donor and receiver catchments.",
        "pairs_kmeans": "K-means clustering pairs between donor and receiver catchments.",
        "pairs_msw": "Selected donor-receiver pairs for MSW-M regionalization.",
        "params": "Parameters used for each formulation in the regionalization.",
        # "spatial_distance": "Spatial distances between donor and receiver catchments.",
        "summary_score": "Summary scores for each catchment after regionalization.",
    }
    return outputs, descriptions


def schema_to_rst(df: pd.DataFrame, title: str, description: str = "") -> str:
    """Convert a pandas DataFrame schema to an RST list-table."""
    lines = []

    # Title
    lines.append(f"{title}")
    lines.append("-" * len(title))
    lines.append("")

    # Optional description
    if description:
        lines.append(description)
        lines.append("")

    # Table header
    lines.append(".. list-table::")
    lines.append("   :header-rows: 1\n")
    lines.append("   * - Column\n     - Type\n     - Nullable")

    nullables = (
        df.isnull().any().to_dict()
        if len(df) > 0
        else {c: "unknown" for c in df.columns}
    )

    for col, dtype in df.dtypes.items():
        lines.append(f"   * - {col}\n     - {dtype}\n     - {nullables[col]}\n")

    lines.append("")
    return "\n".join(lines)


def process_file(
    title: str,
    path: str,
    s3_client=None,
    bucket: str = "ngwpc-dev",
    description: str = "",
) -> str:
    """Load a file (csv, parquet, gpkg, gdb) and return an RST schema string."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if s3_client is None:
            if ext == ".csv":
                df = pd.read_csv(path, nrows=1000)  # sample for speed
            elif ext == ".parquet":
                df = pd.read_parquet(path, engine="pyarrow")
            elif ext in [".gpkg", ".gdb"]:
                if gpd is None:
                    raise RuntimeError("geopandas required for GPKG/GDB")
                layers = fiona.listlayers(path)
                rst_blocks = []
                for layer in layers:
                    gdf = gpd.read_file(path, layer=layer, rows=1000)
                    rst_blocks.append(schema_to_rst(gdf, f"{title} (layer: {layer})"))
                return "\n\n".join(rst_blocks)
            else:
                return
        else:
            response = s3_client.get_object(Bucket=bucket, Key=str(path))
            if ext == ".csv":
                df = pd.read_csv(BytesIO(response["Body"].read()), nrows=1000)
            elif ext == ".parquet":
                df = pd.read_parquet(BytesIO(response["Body"].read()), engine="pyarrow")
            else:
                return
    except Exception as e:
        return f".. warning:: Failed to read {path} ({e})"

    return schema_to_rst(df, title, description=description)


def unpack_dict(d: dict, root: str = "") -> list[str]:
    if len(root) > 0:
        root += "."
    out = {}
    for k, v in d.items():
        if isinstance(v, str):
            out[root + k] = v
        if isinstance(v, list):
            if isinstance(v[0], str):
                out[root + k] = v[0]
        if isinstance(v, dict):
            out = out | unpack_dict(v, root + k)
    return out


def deep_merge_keep_both(d1, d2):
    merged = dict(d1)
    for k, v in d2.items():
        if k not in merged:
            merged[k] = v
        else:
            if isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = deep_merge_keep_both(merged[k], v)
            else:
                # conflict → keep both in list
                if not isinstance(merged[k], list):
                    merged[k] = [merged[k]]
                merged[k].append(v)
    return merged


def main(
    file_dict: dict[str, str],
    output_rst,
    s3_client=None,
    descriptions: dict[str, str] = {},
):
    all_schemas = ["Schemas", "=======", ""]

    for k, v in file_dict.items():
        schema = process_file(
            k, v, s3_client=s3_client, description=descriptions.get(k, "")
        )
        if schema is not None:
            all_schemas.append(schema)
            all_schemas.append("\n")
    all_schemas.append(".. toctree::\n   :maxdepth: 2")
    with open(output_rst, "w") as f:
        f.write("\n".join(all_schemas))


if __name__ == "__main__":
    # process input data schemas
    yaml_files = list(Path(CONFIG_DIR).glob("*.yaml"))
    yaml_files = [
        f
        for f in yaml_files
        if f.name
        in [
            "config_formreg.yaml",
            "config_parreg.yaml",
            "config_general.yaml",
        ]
    ]  # only process "general", "formreg", "parreg" configs

    main(get_sample_input_files(yaml_files), OUT_PATH_INPUT_DATA, s3_client=None)

    # process output data schemas
    s3_client = initialize_s3_client()
    output_files, descriptions = get_sample_output_files()
    main(
        output_files,
        OUT_PATH_OUTPUT_DATA,
        s3_client=s3_client,
        descriptions=descriptions,
    )
