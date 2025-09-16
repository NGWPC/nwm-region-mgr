"""Process snow cover data from HydroATLAS and calculate area-weighted averages for NextGen catchments.

To avoid memory issues, process each VPU separately.

"""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import box
from utils import area_weighted_average

# Define the attribute for snow cover percent
attr = "snw_pc_syr"  # annual average snow cover percent in subbasins

# Path to the HydroATLAS shapefile
hydroatlas_file = (
    "/home/yuqiong.liu/work/data/HydroATLAS/BasinATLAS_v10_shp/BasinATLAS_v10_lev12.shp"
)

# get all vpu ids from file names
vpu_ids = [
    f.stem.split("_")[1]
    for f in Path("/home/yuqiong.liu/work/data/gpkg_v2.2/vpu_divides").glob(
        "vpu_*.gpkg"
    )
]

# loop through each vpu to process snow cover data
for vpu in vpu_ids:
    # Define the output file path
    output_file = (
        "/home/yuqiong.liu/work/data/ngen_reg/inputs/snow_frac/vpu"
        + str(vpu)
        + "_snow_frac.parquet"
    )
    output_file = Path(output_file)
    output_file.parent.mkdir(
        parents=True, exist_ok=True
    )  # create parent directories if they don't exist
    if output_file.exists():
        print(f"Output file {output_file} already exists. Skipping VPU {vpu}.")
        continue

    print(f"Processing VPU: {vpu}")

    # NextGen gpkg file
    gpkg_file = f"/home/yuqiong.liu/work/data/gpkg_v2.2/vpu_divides/vpu_{vpu}.gpkg"
    gdf_ngen = gpd.read_file(gpkg_file, layer="divides")
    gdf_ngen = gdf_ngen[["divide_id", "geometry"]]

    bbox_geom = box(*gdf_ngen.total_bounds)
    bbox_gdf = gpd.GeoDataFrame(geometry=[bbox_geom], crs=gdf_ngen.crs)

    # Reproject the bbox polygon to WGS84
    latlon_bbox = bbox_gdf.to_crs(epsg=4326)

    # Read HydroATLAS sub-basins within the bbox
    gdf_hydroatlas = gpd.read_file(
        hydroatlas_file, layer="BasinATLAS_v10_lev12", bbox=latlon_bbox
    )
    gdf_hydroatlas = gdf_hydroatlas[[attr, "geometry"]]

    if gdf_hydroatlas.empty:
        print(f"No HydroATLAS data found for VPU {vpu}. Skipping...")
        continue

    # compute area-weighted average of snow cover percent
    gdf_ngen = area_weighted_average(
        gdf_fine=gdf_ngen,
        gdf_coarse=gdf_hydroatlas,
        value_col=attr,
        fine_id_col="divide_id",
        crs_proj="EPSG:5070",
    )

    # rename the column to "snow_frac"
    gdf_ngen.rename(columns={f"{attr}_weighted": "snow_pc_hydroatlas"}, inplace=True)

    # remove the geometry column
    gdf_ngen = gdf_ngen.drop(columns="geometry")

    # Save results to parquet file
    gdf_ngen.to_parquet(output_file, index=False)
