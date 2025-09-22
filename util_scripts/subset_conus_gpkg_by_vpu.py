"""Retrieve VPU gpkg from conus.gpkg file"""

import argparse
from pathlib import Path

import geopandas as gpd


def main(vpu_str: str):
    """Extract VPU from conus.gpkg and save to new gpkg file."""
    # conus gpkg file
    conus_in = Path(
        "~/s3/hydrofabric-data/patch/7_30_25/nwm_patch_conus_nextgen.gpkg"
    ).expanduser()

    # output gpkg file
    output_gpkg = (
        Path("~/data/hydrofabric/gpkg_vpu/") / f"vpu_{vpu_str}/vpu_{vpu_str}_patch.gpkg"
    ).expanduser()
    output_gpkg.parent.mkdir(parents=True, exist_ok=True)

    # Set layers of conus geopackage
    layers = [
        "flowpaths",
        "divides",
        "lakes",
        "nexus",
        "pois",
        "hydrolocations",
        "flowpath-attributes",
        "network",
        "divide-attributes",
    ]

    # Loop through layers in gpkg, filtering by vpu_str
    for layer in layers:
        print(f"Processing layer: {layer}")

        # Read in conus geopackage layer
        gdf = gpd.read_file(conus_in, layer=layer)

        # Filter by VPU id
        filter_gdf = gdf[gdf["vpuid"] == vpu_str]

        # Fill layers with missing geometries
        if "geometry" not in filter_gdf.columns:
            filter_gdf = filter_gdf.copy()
            filter_gdf["geometry"] = None
            filter_gdf = gpd.GeoDataFrame(filter_gdf, geometry="geometry")
            filter_gdf.set_crs(crs="EPSG:5070", inplace=True)

        # Save to geopackage layer
        filter_gdf.to_file(output_gpkg, layer=layer, driver="GPKG")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract VPU from conus.gpkg")
    parser.add_argument(
        "--vpu", required=True, help="VPU identifier (e.g., 09, 10L, 10U)"
    )
    args = parser.parse_args()

    print(f"Extracting VPU {args.vpu} from CONUS geopackage...")
    main(args.vpu)
    print(f"VPU {args.vpu} geopackage created successfully.")
