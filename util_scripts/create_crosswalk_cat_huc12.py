"""python script to create crosswalk table between NextGen catchments and HUC12s.

The script reads HUC12 and NextGen catchment shapefiles, identifies the best matching HUC12 for each catchment
based on maximum area overlap, and outputs a crosswalk table with the matched pairs and overlap information.

The script supports both NHF v1 and v2.2 GPKG files.
"""

from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import pandas as pd

hf_version = "nhf"  #  "nhf" or "v2.2"

id_col = "divide_id" if hf_version == "v2.2" else "div_id"
area_col = "areasqkm" if hf_version == "v2.2" else "area_sqkm"
vpu_col = "vpuid" if hf_version == "v2.2" else "vpu_id"


def create_cwt(
    shp1: gpd.GeoDataFrame, shp2: gpd.GeoDataFrame, huc_col: str, chunk_size: int = 5000
) -> pd.DataFrame:
    """Create crosswalk table between NextGen catchments and HUC12s for a given VPU."""
    # Convert to a projected CRS for accurate area calculations
    # projected_crs = "EPSG:3857" # Web Mercator; preserves shapes but distorts area, especially at high latitudes
    projected_crs = "EPSG:6933"  # Equal-area cylindrical projection; preserves area globally; alternative: "EPSG:5070" (Albers Equal Area) for CONUS only

    shp1 = shp1.to_crs(projected_crs)
    shp2 = shp2.to_crs(projected_crs)

    # Build spatial index for shp1 (used for chunked intersection)
    shp1_sindex = shp1.sindex

    # Find overlapping areas (processed in chunks to avoid memory issues)
    overlap_results = []
    for start in range(0, len(shp2), chunk_size):
        end = start + chunk_size
        shp2_chunk = shp2.iloc[start:end].copy()

        print(f"Processing chunk {start}:{end} ({end / len(shp2):.1%})")

        # Spatial prefilter: only keep shp1 polygons that may intersect this chunk
        # idx = shp1_sindex.query_bulk(shp2_chunk.geometry, predicate="intersects")[1]
        # shp1_subset = shp1.iloc[idx].drop_duplicates()

        idx = []
        for geom in shp2_chunk.geometry:
            idx.extend(shp1_sindex.intersection(geom.bounds))

        idx = list(set(idx))
        shp1_subset = shp1.iloc[idx]

        if shp1_subset.empty:
            continue

        overlap = gpd.overlay(shp2_chunk, shp1_subset, how="intersection")

        if overlap.empty:
            continue

        overlap_results.append(overlap)

    if overlap_results:
        overlap = pd.concat(overlap_results, ignore_index=True)
    else:
        overlap = gpd.GeoDataFrame(columns=[id_col, huc_col, "geometry"])

    # Find overlapping areas
    # overlap = gpd.overlay(shp2, shp1, how="intersection")

    # Compute area of each original polygon in shp2 (and convert to km^2)
    shp2["original_area"] = shp2.geometry.area / 1_000_000

    # Compute intersection area (and convert to km^2)
    overlap["overlap_area"] = overlap.geometry.area / 1_000_000

    # merge with shp2
    overlap = overlap[[id_col, huc_col, "overlap_area"]]
    shp2_tmp = shp2[[id_col, area_col, "original_area"]]
    overlap = overlap.merge(shp2_tmp, on=id_col, how="left")

    # Calculate percentage of each shp2 polygon that is covered by intersecting polygons in shp1
    overlap["overlap_percentage"] = (
        overlap["overlap_area"] / overlap["original_area"]
    ) * 100

    # Find the maximum overlapping shp1 polygon for each polygon in shp2
    max_overlap = overlap.loc[overlap.groupby(id_col)["overlap_percentage"].idxmax()]

    # identify shp2 polygons not paired with a shp1 polygon
    polys = shp2[id_col].unique()
    polys_matched = max_overlap[id_col].unique()
    polys_unmatched = [x for x in polys if x not in polys_matched]

    # Find the nearest shp1 polygon for each unmatched shp2 polygon
    nearest_matches = gpd.sjoin_nearest(
        shp2[shp2[id_col].isin(polys_unmatched)],
        shp1,
        how="left",
        distance_col="nearest_distance",
    )
    nearest_matches.rename(columns={"nearest_distance": "nearest_dist_m"}, inplace=True)
    nearest_matches = nearest_matches[[id_col, huc_col, "nearest_dist_m"]]

    # create the final huc12/divide_id crosswalk table
    cwt = pd.concat([max_overlap, nearest_matches], axis=0, ignore_index=True)

    return cwt


@lru_cache(maxsize=None)
def read_huc_layer(path: str, layer: str) -> gpd.GeoDataFrame:
    """Read and cache a GeoDataFrame by path and layer."""
    return gpd.read_file(Path(path).expanduser(), layer=layer)


def get_vpu_list(domain: str) -> list:
    """Get list of VPUs for the specified domain."""
    match domain.lower():
        case "conus":
            # fmt: off
            vpu_list = [
                "01", "02", "03N", "03S", "03W", "04", "05", "06", "07", "08",
                "09", "10L", "10U", "11", "12", "13", "14", "15", "16", "17", "18",
            ]
            # fmt: on
        case "ak":
            vpu_list = ["ak"]
        case "hi":
            vpu_list = ["hi"]
        case "prvi":
            vpu_list = ["prvi"]
        case _:
            raise Exception(f"Unsupported domain: {domain}")

    return vpu_list


def process_domain(domain: list | str):
    """Loop through the domains and read NextGen hydrofabric for the domain."""
    # Note: process conus, hi, and prvi first, since they can share the same 'shp_huc'from above;
    # for AK, a new NHD gpkg file will be used (see below)
    domains = (
        ["conus", "hi", "prvi", "ak"]
        if domain == "all"
        else domain
        if isinstance(domain, list)
        else [domain]
    )
    for domain in domains:
        # check if crosswalk file already exists; if not, create it
        outdir = Path(f"~/data/region_input/{hf_version}/cwt_ngen_huc12").expanduser()
        outdir.mkdir(exist_ok=True, parents=True)
        outfile = Path(outdir, "cwt_huc12_divide_" + domain + ".csv")

        if outfile.exists():
            print(f"Crosswalk file already exists for {domain}: {outfile}. Skip")
            continue

        print(f"Processing domain: {domain}")

        # Read HUC12 shapefiles
        if domain != "ak":
            shp_huc = read_huc_layer(
                "~/data/NHDPlusV21/NHDPlusNationalData/NationalWBDSnapshot.gdb",
                "WBDSnapshot_National",
            )
            shp_huc["VPUID"] = shp_huc["VPUID"].astype(str)
            huc_col = "HUC_12"
        else:
            shp_huc = read_huc_layer(
                "~/data/NHDPlusV21/NHD_H_Alaska_State_original.gpkg", "WBDHU12"
            ).copy()
            shp_huc["VPUID"] = "19"
            huc_col = "huc12"

        # Create ngen catchment - huc12 crosswalk; process by vpus to reduce memory usage
        vpus = get_vpu_list(domain)
        df_cwt = pd.DataFrame()
        for vpu in vpus:
            print(f"Processing VPU {vpu}")
            vpu1 = (
                vpu
                if domain == "conus"
                else "19"
                if domain == "ak"
                else "20"
                if domain == "hi"
                else "21"
            )
            shp1 = shp_huc[shp_huc["VPUID"] == vpu1]
            file_stem = f"vpu_{vpu}" if domain == "conus" else f"vpu_{vpu}_nhf_1.1.3"
            gpkg_file = Path(
                f"~/data/hydrofabric/gpkg_{hf_version}/{file_stem}.gpkg"
            ).expanduser()
            if not gpkg_file.exists():
                print(f"GPKG file does not exist for VPU {vpu}: {gpkg_file}. Skipping.")
                continue
            shp2 = gpd.read_file(gpkg_file, layer="divides")
            shp2[vpu_col] = shp2[vpu_col].astype(str)

            df = create_cwt(shp1, shp2, huc_col)
            df.rename(columns={huc_col: huc_col.lower()}, inplace=True)
            df_cwt = pd.concat([df_cwt, df])

        # Round all numeric columns to 2 decimal places
        df_cwt[df_cwt.select_dtypes(include=["float64", "int64"]).columns] = (
            df_cwt.select_dtypes(include=["float64", "int64"]).round(2)
        )

        # save crosswalk to file for use in formulation regionalization later
        df_cwt.to_csv(outfile, index=False)

        # print summary
        print(
            f"Number of catchments matched with HUC12: {len(df_cwt[df_cwt['nearest_dist_m'].isna()])}"
        )
        print(
            f"Number of catchments not matched with HUC12: {len(df_cwt[~df_cwt['nearest_dist_m'].isna()])}"
        )


if __name__ == "__main__":
    process_domain("all")
