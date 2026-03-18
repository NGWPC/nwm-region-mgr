"""Main entry point for formulation/parameter regionalization and NGEN simulation.

This module reads a set of configuration files and executes formulation
regionalization, parameter regionalization, or NGEN simulation depending
on the selected option.
"""

from __future__ import annotations

import argparse
import logging
from argparse import RawTextHelpFormatter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

import matplotlib

from nwm_region_mgr.formreg import config_schema as fcs
from nwm_region_mgr.formreg.process_config import (
    FormulationRegionalizationProcessor,
)
from nwm_region_mgr.parreg import config_schema as pcs
from nwm_region_mgr.parreg.manual_pairings import ManualPairer
from nwm_region_mgr.parreg.process_config import ParameterRegionalizationProcessor

logger = logging.getLogger(__name__)
matplotlib.use("Agg")


@dataclass(frozen=True)
class ConfigFiles:
    """Standard configuration file names."""

    general: str = "config_general.yaml"
    formreg: str = "config_formreg.yaml"
    parreg: str = "config_parreg.yaml"
    ngen: str = "config_ngen.yaml"


CONFIG = ConfigFiles()

# required config files for each option
OPTIONS = Literal["formreg", "parreg", "ngen"]
REQUIRED_CONFIG_FILES: dict[OPTIONS, tuple[str, ...]] = {
    "formreg": (
        CONFIG.general,
        CONFIG.formreg,
    ),
    "parreg": (
        CONFIG.general,
        CONFIG.formreg,
        CONFIG.parreg,
    ),
    "ngen": (
        CONFIG.general,
        CONFIG.ngen,
    ),
}


def _resolve_config_files(
    config_dir: Path,
    option: OPTIONS,
) -> dict[str, Path]:
    """Resolve and validate config files required for the given option."""
    required = REQUIRED_CONFIG_FILES[option]
    config_paths = {name: config_dir / name for name in required}

    missing = [str(p) for p in config_paths.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing required config files for option '{option}':\n"
            + "\n".join(missing)
        )

    return config_paths


def _run_formreg(
    frp: FormulationRegionalizationProcessor,
) -> None:
    """Run formulation regionalization."""
    for vpu in frp.config.general.vpu_list:
        logger.info("Running formulation regionalization for VPU %s", vpu)
        frp.run_formreg_for_vpu(
            vpu,
            frp.get_output_file_path(
                "formulation",
                vpu,
                use_stem_suffix=True,
            ),
        )


def _run_parreg(
    frp: FormulationRegionalizationProcessor,
    rp: ParameterRegionalizationProcessor,
) -> None:
    """Run parameter regionalization (includes formulation regionalization)."""
    for vpu in rp.config.general.vpu_list:
        logger.info("Running parameter regionalization for VPU %s", vpu)
        rp.run_parreg_for_vpu(vpu, frp)

    mp = ManualPairer(rp.config)
    for vpu in rp.config.general.vpu_list:
        logger.info("Running manual pairings for VPU %s", vpu)
        mp.run_manual_pairing(vpu, rp, frp)


def _run_ngen(
    config_files: list[Path],
) -> None:
    """Run NGEN simulations."""
    # option dependent imports
    from nwm_region_mgr.ngen import config_schema as ngen_config_schema
    from nwm_region_mgr.ngen.process_config import NgenSimulationProcessor

    nsp = NgenSimulationProcessor(
        config_file=config_files,
        config_schema=ngen_config_schema.Config,
    )

    for vpu in nsp.config.general.vpu_list:
        logger.info("Running NGEN simulation for VPU %s", vpu)
        nsp.run_ngen_for_vpu(vpu)


def _build_formreg_processor(file_general, file_formreg):
    """Build formulation regionalization processor."""
    return FormulationRegionalizationProcessor(
        config_file=[file_general, file_formreg],
        config_schema=fcs.Config,
    )


def main(
    config_dir: Path,
    option: OPTIONS,
    sample_size: int | None = None,
) -> None:
    """Execute regionalization or NGEN simulation."""
    logger.info("Starting nwm_region_mgr")
    logger.info("Config directory: %s", config_dir)
    logger.info("Run option: %s", option)
    if sample_size is not None:
        logger.info("Sample size: %d", sample_size)

    config_paths = _resolve_config_files(config_dir, option)

    # create formreg processor for formreg / parreg cases
    if option in {"formreg", "parreg"}:
        frp = _build_formreg_processor(
            file_general=config_paths[CONFIG.general],
            file_formreg=config_paths[CONFIG.formreg],
        )

    if option == "formreg":
        _run_formreg(frp)

    elif option == "parreg":
        rp = ParameterRegionalizationProcessor(
            config_file=[
                config_paths[CONFIG.general],
                config_paths[CONFIG.formreg],
                config_paths[CONFIG.parreg],
            ],
            config_schema=pcs.Config,
            sample_size=sample_size,
        )
        _run_parreg(frp, rp)

    elif option == "ngen":
        _run_ngen(
            [
                config_paths[CONFIG.general],
                config_paths[CONFIG.ngen],
            ]
        )

    logger.info("Completed %s", option)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter)

    parser.add_argument(
        "config_dir",
        type=Path,
        help=(
            "Path to directory containing configuration files.\n\n"
            "Required files depend on mode:\n"
            f"  formreg : {CONFIG.general}, {CONFIG.formreg}\n"
            f"  parreg  : {CONFIG.general}, {CONFIG.formreg}, {CONFIG.parreg}\n"
            f"  ngen    : {CONFIG.general}, {CONFIG.ngen}\n"
        ),
    )

    parser.add_argument(
        "option",
        nargs="?",
        choices=get_args(OPTIONS),
        default="parreg",
        help=(
            "Run option:\n"
            "  formreg : formulation regionalization only\n"
            "  parreg  : formulation + parameter regionalization (default)\n"
            "  ngen    : NGEN simulation only"
        ),
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Sample size for parameter regionalization",
    )

    args = parser.parse_args()
    main(args.config_dir, args.option, sample_size=args.sample_size)
