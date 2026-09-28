"""Build and render S3 directory trees for input and output data as Markdown for documentation."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import boto3

DEFAULT_INPUT_REGION_PREFIX = "nwm-tools-data/regionalization/data/inputs/"
DEFAULT_INPUT_NGEN_PREFIX = "nwm-tools-data/esmf/"
DEFAULT_OUTPUT_PREFIX = "nwm-tools-data/regionalization/data/outputs/"
DEFAULT_COMMENTS_FILE = Path(__file__).resolve().parent / "folder_file_desc.csv"
DEFAULT_MAX_FILES_PER_DIR = 10


def make_tree():
    """Create a recursively nested defaultdict for an S3 directory tree."""
    return defaultdict(make_tree)


def build_tree(s3, bucket, prefix):
    """Build a nested dictionary representing an S3 directory structure."""
    paginator = s3.get_paginator("list_objects_v2")
    root = make_tree()

    prefix = prefix.rstrip("/") + "/"

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel = key[len(prefix) :].strip("/")

            if not rel:
                continue

            parts = rel.split("/")
            current = root

            for part in parts:
                current = current[part]

    return root


def build_input_tree(s3, bucket, region_prefix, ngen_prefix):
    """Build the combined S3 tree for input data."""
    root = make_tree()

    # Regionalization input data contains the region/ and eval/ directories.
    region_tree = build_tree(
        s3,
        bucket,
        region_prefix,
    )
    root.update(region_tree)

    # ESMF data is presented as the ngen/ directory in the documentation.
    ngen_tree = build_tree(
        s3,
        bucket,
        ngen_prefix,
    )
    root["ngen"].update(ngen_tree)

    return root


def load_comments(csv_file):
    """Load comments from a CSV file into a path-to-comment dictionary."""
    comments = {}

    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            path = row["path"].strip().rstrip("/")
            comments[path] = row["comment"].strip()

    return comments


def render_tree(
    tree,
    comments,
    current_path="",
    depth=1,
    max_files_per_dir=None,
):
    """Recursively render a directory tree with comments."""
    lines = []
    entries = sorted(tree.keys())

    # Separate files from directories. In this tree representation, a leaf
    # node represents a file, while a node with children represents a directory.
    files = [entry for entry in entries if not tree[entry]]
    directories = [entry for entry in entries if tree[entry]]

    if max_files_per_dir is not None and len(files) > max_files_per_dir:
        files_to_render = files[:max_files_per_dir]
        omitted_file_count = len(files) - max_files_per_dir
    else:
        files_to_render = files
        omitted_file_count = 0

    # Show directories first, then files.
    # This keeps the tree structure easier to navigate.
    entries_to_render = directories + files_to_render

    if omitted_file_count:
        entries_to_render.append(f"... ({omitted_file_count} more files omitted)")

    for i, entry in enumerate(entries_to_render):
        is_last = i == len(entries_to_render) - 1
        connector = "└── " if is_last else "├── "

        if entry.startswith("... ("):
            lines.append(f"{'│   ' * (depth - 1)}{connector}{entry}")
            continue

        full_path = f"{current_path}/{entry}".strip("/")
        comment = comments.get(full_path, "")

        line = f"{connector}{entry}"
        if comment:
            # line = f"{line:<60} # {comment}"
            line = f"{line}      # {comment}"

        indent = "│   " * (depth - 1)
        lines.append(f"{indent}{line}")

        # Only directories have children to render.
        if tree[entry]:
            lines.extend(
                render_tree(
                    tree[entry],
                    comments,
                    current_path=full_path,
                    depth=depth + 1,
                    max_files_per_dir=max_files_per_dir,
                )
            )

    return lines


def render_md(tree, comments, header, max_files_per_dir=None):
    """Render a directory tree as a Markdown code block."""
    lines = ["```bash", header]

    lines.extend(
        render_tree(
            tree,
            comments,
            current_path=header,
            max_files_per_dir=max_files_per_dir,
        )
    )

    lines.extend(["```", ""])

    return "\n".join(lines)


def get_directory_description(directory_type):
    """Return the documentation description for an input or output directory."""
    if directory_type == "input":
        return (
            "The input directory contains three subdirectories: `region`, `ngen`, "
            "and `eval`, which store the input files used by the regionalization, "
            "NGEN simulation, and evaluation steps, respectively."
        )

    return (
        "The output directory contains three subdirectories: `region`, `ngen`, "
        "and `eval`, which store the output files generated by the regionalization, "
        "NGEN simulation, and evaluation steps, respectively."
    )


def write_tree_file(
    file_path,
    directory_type,
    tree,
    comments,
    max_files_per_dir,
):
    """Write a generated directory tree Markdown file."""
    header = f"## {directory_type.capitalize()} Directory Structure\n\n"
    description = get_directory_description(directory_type)
    description += (
        f" The directory tree below lists up to {max_files_per_dir} files "
        "per directory; additional files are omitted from the listing."
        "\n\n"
    )

    tree_header = "inputs" if directory_type == "input" else "outputs"
    md_content = render_md(
        tree,
        comments,
        header=tree_header,
        max_files_per_dir=max_files_per_dir,
    )

    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as f:
        f.write(header)
        f.write(description)
        f.write(md_content)

    print(f"Saved {directory_type} tree to {file_path}")


def main():
    parser = argparse.ArgumentParser(
        description=("Generate Markdown directory trees for S3 input and output data.")
    )

    parser.add_argument(
        "--bucket",
        default="ngwpc-dev",
        help="S3 bucket name.",
    )
    parser.add_argument(
        "--input-region-prefix",
        default=DEFAULT_INPUT_REGION_PREFIX,
        help=(
            "S3 prefix for regionalization input data "
            f"(default: {DEFAULT_INPUT_REGION_PREFIX})"
        ),
    )
    parser.add_argument(
        "--input-ngen-prefix",
        default=DEFAULT_INPUT_NGEN_PREFIX,
        help=(f"S3 prefix for NGEN input data (default: {DEFAULT_INPUT_NGEN_PREFIX})"),
    )
    parser.add_argument(
        "--output-prefix",
        default=DEFAULT_OUTPUT_PREFIX,
        help=(f"S3 prefix for output data (default: {DEFAULT_OUTPUT_PREFIX})"),
    )
    parser.add_argument(
        "--comments",
        default=DEFAULT_COMMENTS_FILE,
        help=(
            "CSV file containing path and comment columns "
            f"(default: {DEFAULT_COMMENTS_FILE})."
        ),
    )
    parser.add_argument(
        "--max-files-per-dir",
        type=int,
        default=DEFAULT_MAX_FILES_PER_DIR,
        help=(
            "Maximum number of files to display in each directory "
            f"(default: {DEFAULT_MAX_FILES_PER_DIR})."
        ),
    )

    args = parser.parse_args()

    if args.max_files_per_dir < 1:
        parser.error("--max-files-per-dir must be at least 1")

    comments = load_comments(args.comments)
    s3 = boto3.client("s3")

    output_dir = Path(__file__).resolve().parent.parent / "source" / "tech_reference"

    # Build and write the combined input tree.
    input_tree = build_input_tree(
        s3,
        args.bucket,
        args.input_region_prefix,
        args.input_ngen_prefix,
    )

    write_tree_file(
        output_dir / "input_tree.md",
        "input",
        input_tree,
        comments,
        args.max_files_per_dir,
    )

    # Build and write the output tree.
    output_tree = build_tree(
        s3,
        args.bucket,
        args.output_prefix,
    )

    write_tree_file(
        output_dir / "output_tree.md",
        "output",
        output_tree,
        comments,
        args.max_files_per_dir,
    )


if __name__ == "__main__":
    main()
