import argparse
import random
from pathlib import Path

import geopandas as gpd


def create_divide_symlinks(
    input_dir: Path | str,
    gpkg_file: Path | str,
    output_dir: Path | str,
    divide_col: str = "divide_id",
    csv_ext: str = ".csv",
):
    """For each divide_id in the gpkg file, create a symbolic link to a random CSV file.

    Args:
        input_dir (Path | str): Root folder containing .csv files (searched recursively).
        gpkg_file (Path | str): Path to the gpkg file containing divide_id.
        output_dir (Path | str): Folder where symbolic links will be created.
        divide_col (str): Column in gpkg file containing divide IDs.
        csv_ext (str): Extension of input files (default: '.csv').

    """
    input_dir = Path(input_dir)
    gpkg_file = Path(gpkg_file)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1) Collect all csv files
    csv_files = list(input_dir.rglob(f"*{csv_ext}"))
    if not csv_files:
        raise FileNotFoundError(f"No {csv_ext} files found in {input_dir}")

    # 2) Get unique divide_ids
    gdf = gpd.read_file(gpkg_file)
    if divide_col not in gdf.columns:
        raise KeyError(f"Column '{divide_col}' not found in {gpkg_file}")
    divide_ids = gdf[divide_col].dropna().unique()

    # 3) Create symlinks
    for divide_id in divide_ids:
        target_csv = random.choice(csv_files)  # randomly pick one file
        symlink_path = output_dir / f"{divide_id}.csv"

        # Remove if symlink/file already exists
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()

        # Create symbolic link
        symlink_path.symlink_to(target_csv.resolve())

    print(f"Created {len(divide_ids)} symlinks in {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create symbolic links for divide IDs to random forcing CSV files."
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        required=True,
        help="Root folder containing .csv forcing files (searched recursively).",
    )
    parser.add_argument(
        "--gpkg_file",
        type=str,
        required=True,
        help="Path to the gpkg file containing divide_id.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Folder where symbolic links will be created.",
    )
    parser.add_argument(
        "--divide_col",
        type=str,
        default="divide_id",
        help="Column in gpkg file containing divide IDs (default: 'divide_id').",
    )
    parser.add_argument(
        "--csv_ext",
        type=str,
        default=".csv",
        help="Extension of input files (default: '.csv').",
    )

    args = parser.parse_args()

    create_divide_symlinks(
        input_dir=args.input_dir,
        gpkg_file=args.gpkg_file,
        output_dir=args.output_dir,
        divide_col=args.divide_col,
        csv_ext=args.csv_ext,
    )
