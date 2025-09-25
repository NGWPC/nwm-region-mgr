"""Standalone program for running ngen simulations with regionalized parameters.

This script calls MSWM to set up an NGEN simulation and runs the NGEN simulation
  for a specified VPU using regionalized parameters. It takes various command-line arguments
  to specify the run configuration and paths to necessary files.

See run_ngen_vpu.sh for an example of how to run this script.
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from mswm.build_inputs import RealizationBuilder

logger = logging.getLogger(__name__)


def setup_logging(out_dir: str | Path):
    """Set up logging configuration."""
    # log file path
    out_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(out_dir).parent / "region.log"

    # Set up root logger so that each module can log to the same file
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Clear existing handlers (avoid duplicates)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")


def expand_and_verify_paths(args: argparse.Namespace) -> argparse.Namespace:
    """Expand user and resolve/validate paths in the given argparse Namespace."""
    for key, value in vars(args).items():
        if "dir" in key or "file" in key:
            p = Path(value).expanduser().resolve()
            if not p.exists():
                raise FileNotFoundError(f"{p} does not exist")
            setattr(args, key, p)
    return args


def log_run_info(args: argparse.Namespace):
    """Log the run information."""
    logger.info("====== Settings for NGEN Regionalization Run ======")
    logger.info(f"VPU:            {args.vpu}")
    logger.info(f"Run name:       {args.run_name}")
    logger.info(f"Time range:     {args.start_time} → {args.end_time}")
    logger.info(f"Working dir:    {args.work_dir}")
    logger.info(f"Parameter file: {args.par_file}")
    logger.info(f"Pair file:      {args.pair_file}")
    logger.info(f"Forcing dir:    {args.forcing_dir}")
    logger.info(f"GPKG file:      {args.gpkg_file}")
    logger.info(f"Template file:  {args.config_template_file}")
    logger.info(f"NGEN venv path: {args.ngen_venv_path}")
    logger.info("================================================")


def create_mswm_config(args: argparse.Namespace):
    """Create MSWM config file based on template."""
    with open(args.config_template_file, "r") as f:
        template_content = f.read()

    # format start and end times (as required by MSWM)
    start_time = datetime.strptime(args.start_time, "%Y-%m-%dT%H:%M:%S")
    end_time = datetime.strptime(args.end_time, "%Y-%m-%dT%H:%M:%S")
    args.start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
    args.end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")

    # Replace placeholders in the template
    config_content = template_content.format(
        vpu=args.vpu,
        run_name=args.run_name,
        start_time=args.start_time,
        end_time=args.end_time,
        par_file=args.par_file,
        pair_file=args.pair_file,
        forcing_dir=args.forcing_dir,
        gpkg_file=args.gpkg_file,
        work_dir=args.work_dir,
        nprocs=args.nprocs,
    )

    # Write the new config file
    config_path = Path(args.out_dir).parent / "mswm.config"
    with open(config_path, "w") as f:
        f.write(config_content)

    logger.info(f"Created MSWM config file at: {config_path}")
    return config_path


def verify_ngen_run_inputs(args: argparse.Namespace):
    """Verify that necessary input files for NGEN run exist."""
    input_dir = Path(args.out_dir / "../Input").resolve()
    ngen_exe = input_dir / "ngen"
    real_file = (
        Path(args.out_dir).parent / f"{args.vpu}_realization_config_bmi_region.json"
    )
    real_file = real_file.resolve()
    partition_file = input_dir / f"{args.vpu}_partition_config.json"
    hydrofab_file = input_dir / Path(args.gpkg_file).name

    if not ngen_exe.is_file():
        raise FileNotFoundError(f"NGEN executable not found: {ngen_exe}")
    if not real_file.is_file():
        raise FileNotFoundError(f"Realization config file not found: {real_file}")
    if not partition_file.is_file():
        raise FileNotFoundError(f"Partition file not found: {partition_file}")
    if not hydrofab_file.is_file():
        raise FileNotFoundError(f"Hydrofabric file not found: {hydrofab_file}")
    logger.info("All necessary NGEN input files verified.")

    return ngen_exe, real_file, partition_file, hydrofab_file


def run_ngen_simulation(args: argparse.Namespace):
    """Run the NGEN simulation using MSWM."""
    # make sure input files for ngen run exist
    ngen_exe, real_file, partition_file, hydrofab_file = verify_ngen_run_inputs(args)

    # Build the shell command as a string
    cmd_str = f"""
    source {args.ngen_venv_path}/bin/activate
    cd {args.out_dir}
    mpirun -n {args.nprocs} {ngen_exe} {hydrofab_file} all {hydrofab_file} all {real_file} {partition_file}
    """

    logger.info("Running NGEN simulation with command:")
    logger.info(cmd_str)

    # get logger for ngen simulation
    ngen_logger = logging.getLogger("ngen.simulation")
    ngen_logger.setLevel(logging.INFO)

    # Run the command in a subprocess, streaming stdout/stderr
    process = subprocess.Popen(
        ["bash", "-c", cmd_str],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )

    # Stream output live into logger
    for line in process.stdout:
        ngen_logger.info(line.strip())

    process.stdout.close()
    return_code = process.wait()

    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, cmd_str)


def main_workflow(
    args: argparse.Namespace,
):
    """Run the main workflow."""
    # Log run information
    log_run_info(args)

    # create MSWM config file based on template
    input_path = create_mswm_config(args)

    # build realization and module BMI config files
    rb = RealizationBuilder(input_path=input_path)
    rb.build_region_realization()
    logger.info("MSWM processing completed.")

    # Run NGEN simulation
    run_ngen_simulation(args)
    logger.info("NGEN simulation completed.")


def get_args() -> argparse.Namespace:
    """Parse command line arguments."""
    # Create the parser
    parser = argparse.ArgumentParser(
        description="Standalone driver for running ngen simulation with regionalized parameters."
    )
    parser.add_argument("--vpu", required=True, help="VPU identifier (e.g., vpu_09)")
    parser.add_argument("--run_name", required=True, help="Name of this run")
    parser.add_argument(
        "--work_dir", required=True, type=Path, help="Working directory"
    )
    parser.add_argument(
        "--start_time", required=True, help="Start time (YYYY-MM-DDTHH:MM:SS)"
    )
    parser.add_argument(
        "--end_time", required=True, help="End time (YYYY-MM-DDTHH:MM:SS)"
    )
    parser.add_argument("--par_file", required=True, help="Path to parameter file")
    parser.add_argument(
        "--pair_file", required=True, help="Path to donor/receiver pair file"
    )
    parser.add_argument(
        "--forcing_dir", required=True, help="Path to forcing directory"
    )
    parser.add_argument(
        "--gpkg_file", required=True, help="Path to hydrofabric GPKG file"
    )
    parser.add_argument(
        "--config_template_file",
        required=True,
        help="Path to configuration template file",
    )
    parser.add_argument(
        "--ngen_venv_path",
        required=True,
        help="Path to the NGEN virtual environment",
    )
    parser.add_argument(
        "--nprocs",
        type=int,
        default=2,
        help="Number of processors for parallel NGEN run (default: 2)",
    )
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    # get command line arguments
    args = get_args()

    # create output directory
    out_dir = args.work_dir / "regionalization" / args.run_name / args.vpu / "Output"
    out_dir.mkdir(parents=True, exist_ok=True)
    args.out_dir = out_dir

    # set up logging
    setup_logging(out_dir=args.out_dir)

    # Expand paths
    args = expand_and_verify_paths(args)

    try:
        main_workflow(args)
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        sys.exit(1)
