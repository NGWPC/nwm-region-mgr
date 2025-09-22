from pathlib import Path

from mswm.build_inputs import RealizationBuilder

input_path = Path(
    "~/repos/nwm-region-mgr/sample_files/configs/mswm_config.sh"
).expanduser()

rb = RealizationBuilder(input_path=input_path)
rb.build_region_realization()
