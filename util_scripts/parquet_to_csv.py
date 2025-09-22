from pathlib import Path

import pandas as pd


def parquet_to_csv(
    parquet_file: Path | str, csv_file: Path | str | None = None
) -> Path:
    """
    Convert a parquet file to a CSV file.

    Args:
        parquet_file (Path | str): Path to the input parquet file.
        csv_file (Path | str | None): Path to the output CSV file.
                                      If None, same name as parquet but with .csv extension.

    Returns:
        Path: Path to the output CSV file.
    """
    parquet_file = Path(parquet_file)
    if csv_file is None:
        csv_file = parquet_file.with_suffix(".csv")
    else:
        csv_file = Path(csv_file)

    # Read parquet
    df = pd.read_parquet(parquet_file)

    # Write CSV
    df.to_csv(csv_file, index=False)

    return csv_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert a parquet file to CSV format."
    )
    parser.add_argument(
        "parquet_file", type=Path, help="Path to the input parquet file."
    )
    parser.add_argument(
        "--csv_file",
        type=Path,
        default=None,
        help="Path to the output CSV file. If not provided, will use the same name as the parquet file with .csv extension.",
    )
    args = parser.parse_args()

    output_csv = parquet_to_csv(args.parquet_file, args.csv_file)
    print(f"Converted {args.parquet_file} to {output_csv}")
