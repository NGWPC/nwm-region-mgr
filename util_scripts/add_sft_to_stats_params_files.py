from pathlib import Path

import pandas as pd

stat_dir = Path("../data/inputs/region/calval_stats")
param_dir = Path("../data/inputs/region/pseudo_calib_params")

stat_file_pattern = "stat_calval_all"
param_file_pattern = "sampled_params"

column_name = "formulation"
modules = ("cfe-s", "cfe-x")
insert_modules = ["smp", "sft"]
append_str = "_".join(insert_modules)

domains = ["conus", "ak", "hi", "prvi"]


def update_formulation(df: pd.DataFrame) -> pd.DataFrame:
    """Insert modules after specified modules in the formulation column."""
    if column_name not in df.columns:
        print(f"Skipping file (no '{column_name}' column)")
        return df

    def insert_module(val: str) -> str:
        if pd.isna(val):
            return val

        parts = val.split()

        i = 0
        while i < len(parts):
            if parts[i].lower() in modules:
                # avoid duplicate insertion
                if parts[i + 1 : i + 3] == insert_modules:
                    i += 1
                    continue

                parts[i + 1 : i + 1] = insert_modules  # insert both modules
                i += 3  # skip past inserted modules
            else:
                i += 1

        return " ".join(parts)

    mask = df[column_name].str.contains(
        "|".join(modules),
        case=False,
        na=False,
        regex=True,
    )

    df.loc[mask, column_name] = df.loc[mask, column_name].apply(insert_module)

    return df


def process_files(directory: Path, file_pattern: str, extension: str):
    """Process files in the specified directory matching the pattern and extension."""
    for domain in domains:
        file = directory / f"{file_pattern}_{domain}.{extension}"

        if not file.exists():
            print(f"Skipping missing file: {file}")
            continue

        print(f"Processing {extension.upper()}: {file.name}")

        # read
        if extension == "parquet":
            df = pd.read_parquet(file)
        elif extension == "csv":
            df = pd.read_csv(file)
        else:
            raise ValueError(f"Unsupported extension: {extension}")

        # replace formulation
        df = update_formulation(df)

        # write
        out_file = directory / f"{file_pattern}_{domain}_{append_str}.{extension}"

        if extension == "parquet":
            df.to_parquet(out_file, index=False)
        elif extension == "csv":
            df.to_csv(out_file, index=False)


if __name__ == "__main__":
    """Add modules to formulation column in stats and params files."""
    # stats
    process_files(stat_dir, stat_file_pattern, "parquet")

    # params
    process_files(param_dir, param_file_pattern, "csv")
