"""Standalone program for running ngen simulations with regionalized parameters.

This script calls MSWM to set up an NGEN simulation and runs the NGEN simulation
  for a specified VPU using regionalized parameters. It takes various command-line arguments
  to specify the run configuration and paths to necessary files.

Sometimes the NGEN simulation may fail due to issues in the routing module. In such cases,
this script will attempt to run `nwm_routing` as a fallback to generate the routing output.

See run_ngen_vpu.sh for an example of how to run this script.
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import yaml
from mswm.build_inputs import RealizationBuilder

from nwm_region_mgr.utils.config_utils import NGENConfig
from nwm_region_mgr.utils.string_utils import recursive_substitute

logger = logging.getLogger(__name__)


def setup_logging(log_file: str | Path, log_level: int = logging.INFO):
    """Set up logging configuration."""
    # log file path
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Set up root logger so that each module can log to the same file
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear existing handlers (avoid duplicates)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File handler (use 'w' to overwrite each run)
    file_handler = logging.FileHandler(log_file, mode="w")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Log file: {log_file}")


def expand_and_verify_paths(args: dict) -> dict:
    """Expand user and resolve/validate paths in the given argparse Namespace."""
    for key, value in args.items():
        if "dir" in key or "file" in key:
            p = Path(value).expanduser().resolve()
            if not p.exists():
                raise FileNotFoundError(f"{p} does not exist")
            args[key] = p
    return args


def log_run_info(args: dict):
    """Log the run information."""
    logger.info("====== Settings for NGEN Regionalization Run ======")
    logger.info(f"VPU:            {args['vpu']}")
    logger.info(f"Run name:       {args['run_name']}")
    logger.info(f"Time range:     {args['start_time']} → {args['end_time']}")
    logger.info(f"Working dir:    {args['base_dir']}")
    logger.info(f"Parameter file: {args['par_file']}")
    logger.info(f"Pair file:      {args['pair_file']}")
    logger.info(f"GPKG file:      {args['gpkg_file']}")
    logger.info(f"MSWM template file:  {args['config_template']}")
    logger.info(f"NGEN input dir:    {args['out_dir'] / '../Input'}")
    logger.info(f"NGEN output dir:     {args['out_dir']}")
    logger.info(f"Number of procs: {args.keys()}")
    logger.info("================================================")


def create_mswm_config(args: dict):
    """Create MSWM config file based on template."""
    with open(args["config_template"], "r") as f:
        template_content = f.read()

    # format start and end times (as required by MSWM)
    start_time = datetime.strptime(args["start_time"], "%Y-%m-%dT%H:%M:%S")
    end_time = datetime.strptime(args["end_time"], "%Y-%m-%dT%H:%M:%S")
    args["start_time"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
    args["end_time"] = end_time.strftime("%Y-%m-%d %H:%M:%S")

    # Replace placeholders in the template
    config_content = template_content.format(
        vpu=args["vpu"],
        run_name=args["run_name"],
        start_time=args["start_time"],
        end_time=args["end_time"],
        par_file=args["par_file"],
        pair_file=args["pair_file"],
        gpkg_file=args["gpkg_file"],
        work_dir=args["base_dir"],
        nprocs=args["nprocs"],
    )

    # Write the new config file
    config_path = Path(args["out_dir"]).parent / "mswm.config"
    with open(config_path, "w") as f:
        f.write(config_content)

    logger.info(f"Created MSWM config file at: {config_path}")
    return config_path


def verify_ngen_run_inputs(args: dict):
    """Verify that necessary input files for NGEN run exist."""
    input_dir = Path(args["out_dir"] / "../Input").resolve()
    ngen_exe = input_dir / "ngen"
    real_file = (
        Path(args["out_dir"]).parent
        / f"{args['vpu']}_realization_config_bmi_region.json"
    )
    real_file = real_file.resolve()
    partition_file = input_dir / f"{args['vpu']}_partition_config.json"
    hydrofab_file = input_dir / Path(args["gpkg_file"]).name
    # command line argument validation
    if not ngen_exe.is_file():
        raise FileNotFoundError(f"NGEN executable not found: {ngen_exe}")
    if not real_file.is_file():
        raise FileNotFoundError(f"Realization config file not found: {real_file}")
    if not partition_file.is_file() and args["nprocs"] > 1:
        raise FileNotFoundError(f"Partition file not found: {partition_file}")
    if not hydrofab_file.is_file():
        raise FileNotFoundError(f"Hydrofabric file not found: {hydrofab_file}")
    logger.info("All NGEN command-line arguments verified.")

    # TODO: verify the module BMI config file also exists

    return ngen_exe, real_file, partition_file, hydrofab_file


def run_mswm_with_unified_logging(config_path, log_level=logging.INFO):
    """Run MSWM RealizationBuilder to build realization and BMI config files."""
    root_logger = logging.getLogger()
    saved_handlers = root_logger.handlers.copy()

    # Dedicated MSWM logger
    mswm_logger = logging.getLogger("mswm")
    mswm_logger.setLevel(log_level)
    mswm_logger.propagate = False
    mswm_logger.handlers.clear()
    for h in saved_handlers:
        mswm_logger.addHandler(h)

    # Disable propagation on all mswm sub-loggers to avoid double logging
    for name, logger_obj in logging.root.manager.loggerDict.items():
        if name.startswith("mswm") and isinstance(logger_obj, logging.Logger):
            logger_obj.handlers = mswm_logger.handlers
            logger_obj.propagate = False

    # Call MSWM
    rb = RealizationBuilder(config_path)
    rb.build_region_realization()

    # Restore root logger
    root_logger.handlers.clear()
    for h in saved_handlers:
        root_logger.addHandler(h)
    logging.getLogger("main").info("MSWM finished, logging restored.")


def build_ngen_command(args: dict) -> str:
    """Build the NGEN command string."""
    ngen_exe, real_file, partition_file, hydrofab_file = verify_ngen_run_inputs(args)

    if args["nprocs"] < 1:
        args["nprocs"] = 1
        logger.warning("Number of processors set to 1.")

    if args["nprocs"] == 1:
        logger.info("Running NGEN in serial mode.")
        cmd_str = f"""
        cd {args["out_dir"]}
        {ngen_exe} {hydrofab_file} all {hydrofab_file} all {real_file}
        """
    else:
        logger.info(f"Running NGEN in parallel mode with {args['nprocs']} processors.")
        cmd_str = f"""
        cd {args["out_dir"]}
        mpirun --allow-run-as-root -n {args["nprocs"]} {ngen_exe} {hydrofab_file} all {hydrofab_file} all {real_file} {partition_file}
        """

    return cmd_str


def run_nwm_routing(args: dict):
    """Run nwm_routing after NGEN failure (only if routing output does not exist)."""
    routing_logger = logging.getLogger("nwm_routing")
    routing_logger.propagate = False
    routing_logger.setLevel(args["log_level"])

    routing_logger.handlers.clear()
    for h in logging.getLogger().handlers:
        routing_logger.addHandler(h)

    # routing config file
    routing_config = (
        Path(args["out_dir"]).parent
        / "Input"
        / f"{args['vpu']}_troute_config_region.yaml"
    )
    if not routing_config.is_file():
        routing_logger.error(f"Routing config file not found: {routing_config}")
        raise FileNotFoundError(f"Routing config file not found: {routing_config}")

    # Parse and format start time (expects args.start_time like '2022-10-01T00:00:00')
    try:
        start_time = datetime.strptime(args["start_time"], "%Y-%m-%dT%H:%M:%S")
        start_time_str = start_time.strftime("%Y%m%d%H%M")
    except Exception:  # prevents double logging
        # Fallback: use raw string if parsing fails
        start_time_str = (
            str(args["start_time"]).replace(":", "").replace("-", "").replace("T", "")
        )

    # Expected routing output file
    routing_output = Path(args["out_dir"]) / f"troute_output_{start_time_str}.nc"
    # Check if output already exists
    if routing_output.exists():
        routing_logger.info(
            f"Routing output already exists: {routing_output}. Skipping nwm_routing run."
        )
        return

    routing_logger.info(
        f"Routing output not found ({routing_output}). Running fallback command to generate it."
    )

    # Keep track of LEVELPOOL warning lines to avoid duplicates
    warning_seen = set()
    warning_strs = ["WARNING: LEVELPOOL USING COLDSTART WATER ELEVATION"]

    # Build and run nwm_routing command
    cmd = ["python", "-m", "nwm_routing", "-f", "-V4", str(routing_config)]
    routing_logger.info(f"Running command: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
        cwd=args["out_dir"],  # Use cwd argument to change directory
    )

    for line in iter(process.stdout.readline, ""):
        line = line.rstrip()
        if not line:
            continue

        if any(warning in line for warning in warning_strs):
            if line in warning_seen:
                continue
            warning_seen.add(line)

        routing_logger.info(line)

    process.stdout.close()
    return_code = process.wait()

    if return_code != 0:
        routing_logger.error(f"nwm_routing exited with code {return_code}")
        raise subprocess.CalledProcessError(return_code, cmd)
    else:
        routing_logger.info("nwm_routing completed successfully.")


def run_ngen_with_unified_logging(args: dict):
    """Run NGEN as a subprocess and log output.

    If NGEN fails and t-route output file is not found, run nwm_routing as a fallback.

    """
    ngen_logger = logging.getLogger("ngen")
    ngen_logger.propagate = False
    ngen_logger.setLevel(args["log_level"])

    # Attach root handlers so logs go to unified log file + console
    root_handlers = logging.getLogger().handlers
    ngen_logger.handlers.clear()
    for h in root_handlers:
        ngen_logger.addHandler(h)

    # Build command string for run NGEN
    cmd = build_ngen_command(args)

    # Keep track of warning lines to avoid duplicates
    warnings_seen = set()
    warning_strs = ["[BMI WARNING]"]

    process = subprocess.Popen(
        ["bash", "-c", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
    )

    try:
        for line in iter(process.stdout.readline, ""):
            line = line.rstrip()
            if not line:
                continue

            # Filter duplicate warnings
            if any(warning in line for warning in warning_strs):
                if line in warnings_seen:
                    continue
                warnings_seen.add(line)

            ngen_logger.info(line)

            # Detect abort messages
            if "Aborted" in line or "core dumped" in line:
                aborted = True
                ngen_logger.error("Detected NGEN abort. Terminating process...")
                process.terminate()
                break

    finally:
        process.stdout.close()
        return_code = process.wait()

    if return_code != 0 or aborted:
        ngen_logger.error(f"NGEN failed with return code {return_code}.")
        ngen_logger.info("Attempting fallback: running nwm_routing...")

        run_nwm_routing(args)
        return  # Exit after fallback

    ngen_logger.info("NGEN simulation finished successfully.")


def main_workflow(
    args: dict,
):
    """Run the main workflow to build MSWM config and execute MSWM and NGEN simulations."""
    # Log run information
    log_run_info(args)

    # create MSWM config file based on template
    input_path = create_mswm_config(args)

    # Run MSWM to build realization and module BMI config files
    run_mswm_with_unified_logging(input_path)

    # Run NGEN simulation
    run_ngen_with_unified_logging(args)


def get_args() -> argparse.Namespace:
    """Parse command line arguments."""
    # Create the parser
    parser = argparse.ArgumentParser(
        description="Standalone driver for running ngen simulation for a VPU with regionalized parameters."
    )
    parser.add_argument(
        "--config_ngen", required=True, help="Path to NGEN configuration file"
    )
    args = parser.parse_args()

    return args


class NGENConfigProcessor:
    """Processor for NGEN configuration files."""

    def __init__(self, config_file: str):
        """Initialize the processor with the config file path."""
        self.config_file = config_file

    @property
    @lru_cache
    def config(self):
        """Load and process the NGEN configuration file."""
        with open(self.config_file, "r") as f:
            data = yaml.safe_load(f)
        config = NGENConfig(**data["general"])
        return self.substitute_placeholders(config)

    def to_dict(self):
        """Convert the config to a dictionary."""
        return self.config.__dict__

    def substitute_placeholders(self, config):
        """Substitute placeholders in the config with actual values.

        Args:
            config: Config object with placeholders

        Returns:
            Config object with placeholders substituted

        """
        # Create a context dictionary with general config parameters
        context = {
            "vpu": config.vpu if hasattr(config, "vpu") else None,
            "run_name": config.run_name if hasattr(config, "run_name") else None,
            "base_dir": config.base_dir if hasattr(config, "base_dir") else None,
            "start_time": config.start_time if hasattr(config, "start_time") else None,
            "end_time": config.end_time if hasattr(config, "end_time") else None,
            "nprocs": config.nprocs if hasattr(config, "nprocs") else None,
            "par_file": config.par_file if hasattr(config, "par_file") else None,
            "pair_file": config.pair_file if hasattr(config, "pair_file") else None,
            "gpgk_file": config.gpgk_file if hasattr(config, "gpgk_file") else None,
            "config_template": config.config_template
            if hasattr(config, "config_template")
            else None,
            "log_file": config.log_file if hasattr(config, "log_file") else None,
            "log_level": config.log_level if hasattr(config, "log_level") else None,
            "algorithm": config.algorithm if hasattr(config, "algorithm") else None,
        }

        # remove items with None values from context
        context = {k: v for k, v in context.items() if v is not None}

        # substitute placeholders in the config
        config = recursive_substitute(config, context)
        config.nprocs
        return config


if __name__ == "__main__":
    # get command line arguments
    args = get_args()

    config_dict = NGENConfigProcessor(args.config_ngen).to_dict()
    config_dict["run_name"] = config_dict["algorithm"]  # use algorithm as run name

    # create output directory
    out_dir = (
        Path(config_dict["base_dir"])
        / "regionalization"
        / config_dict["run_name"]
        / config_dict["vpu"]
        / "Output"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    config_dict["out_dir"] = out_dir

    # make sure log level is valid
    numeric_level = getattr(logging, config_dict["log_level"].upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {config_dict['log_level']}")
    config_dict["log_level"] = numeric_level

    # set up logging
    setup_logging(
        log_file=config_dict["log_file"] or out_dir.parent / "region.log",
        log_level=config_dict["log_level"],
    )

    # Expand paths
    args = expand_and_verify_paths(config_dict)

    try:
        main_workflow(args)
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        sys.exit(1)
