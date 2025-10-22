"""Functions to handle hydrofabric data and operations."""

import logging
from pathlib import Path

import geopandas as gpd
from shapely.geometry import GeometryCollection, Point
from shapely.ops import unary_union

from .io_utils import read_table
from .validation_utils import check_columns_dataframe

logger = logging.getLogger(__name__)


def find_gages_within_buffer(
    gage_file: Path,
    gage_id_col: str,
    buffer: float,
    gdf: gpd.GeoDataFrame = None,
    hydrofabric_file: Path = None,
    id: str = None,
) -> tuple[list, list, gpd.GeoSeries]:
    """Find gages within a buffer zone around the hydrofabric.

    Args:
        gage_file: path to the donor gage file containing gage_id, longitude, and latitude
        gage_id_col: column name for gage ID in the gage file
        buffer: buffer distance in kilometers around the hydrofabric
        gdf: optional, a GeoDataFrame of hydrofabric polygons (if provided, hydrofabric_file is ignored)
        hydrofabric_file: optional, path to the hydrofabric file (.gpkg or .shp format)
        id: optional, identifier for the hydrofabric


    Returns:
        gages: list of gages within the buffered hydrofabric
        distances: list of distances from each gage to the hydrofabric centroid
        gdf_buffered: GeoDataFrame representing the buffered hydrofabric geometry

    """
    # check if required columns are present in gage file
    required_columns = {"longitude", "latitude", gage_id_col}
    check_columns_dataframe(gage_file, required_columns)

    # read in lat/lon of all gages
    gages = read_table(gage_file)
    if gages.empty:
        raise ValueError(f"No gages found in the gage file: {gage_file}")

    # create a GeoDataFrame of gages with geometry as points
    gage_gdf = gpd.GeoDataFrame(
        gages,
        geometry=[Point(xy) for xy in zip(gages["longitude"], gages["latitude"])],
        crs="EPSG:4326",
    )

    # read the hydrofabric file
    if gdf is None:
        if hydrofabric_file is None:
            raise ValueError("Either gdf or hydrofabric_file must be provided.")
        if not hydrofabric_file.exists():
            raise FileNotFoundError(f"Hydrofabric file not found: {hydrofabric_file}")

        # read the hydrofabric file
        if hydrofabric_file.suffix.lower() == ".gpkg":
            # For GeoPackage files, read the 'divides' layer
            gdf = gpd.read_file(hydrofabric_file, layer="divides")
        elif hydrofabric_file.suffix.lower() == ".shp":
            # For Shapefile, read the file directly
            gdf = gpd.read_file(hydrofabric_file)
        else:
            raise ValueError(
                f"Unsupported hydrofabric file format: {hydrofabric_file.suffix}"
            )

    # Project to meters for accurate distance calculations
    gage_gdf = gage_gdf.to_crs(epsg=3857)
    gdf = gdf.to_crs(epsg=3857)

    # remove invalid geometries
    gdf1 = gdf[gdf.is_valid]
    if gdf1.empty:  # If no valid geometries, create a copy with buffered geometry
        if id:
            logger.debug(
                f"No valid geometries found in the hydrofabric for ID: {id}. "
                f"Creating a buffered geometry as workaround."
            )
        else:
            logger.debug(
                "No valid geometries found in the hydrofabric. Creating a buffered geometry."
            )
        gdf1 = gdf.copy()
        gdf1["geometry"] = gdf1.buffer(0)

    # dissolve all polygons into one before bufferring
    combined_geom = unary_union(gdf1.geometry)

    # Create a buffer around the VPU polygon
    gdf_buffered = combined_geom.buffer(buffer * 1000)

    # Find gages in the buffered VPU
    gages = gage_gdf[gage_gdf.geometry.within(gdf_buffered)][gage_id_col].tolist()

    # compute distances of the gages to the hydrofabric centroid
    gage_gdf = gage_gdf[gage_gdf[gage_id_col].isin(gages)]
    distances = gage_gdf.distance(combined_geom.centroid)

    # convert distances meters to kilometers and round to integer
    distances = distances / 1000
    distances = distances.round(0).astype(int)

    if not gages:
        logger.debug(
            f"No gages found for {id}. Please check the gage file and hydrofabric file."
        )

    return gages, distances, gdf_buffered


def area_weighted_average(
    gdf_fine: gpd.GeoDataFrame,
    gdf_coarse: gpd.GeoDataFrame,
    value_col: str,
    fine_id_col: str = "divide_id",
    crs_proj: str = "EPSG:5070",
) -> gpd.GeoDataFrame:
    """Map area-weighted average of `value_col` from coarse polygons to fine polygons.

    Args:
        gdf_fine: GeoDataFrame with finer polygons
        gdf_coarse: GeoDataFrame with coarser polygons and the value to be averaged
        value_col: Name of the column in gdf_coarse to average
        fine_id_col: Name of unique identifier column in gdf_fine (default is 'divide_id')
        crs_proj: Projected CRS (in meters) for accurate area computation (default is 'EPSG:5070')

    Returns:
        gdf_fine with a new column: `{value_col}_weighted`

    """
    # Reproject to projected CRS
    gdf_fine = gdf_fine.to_crs(crs_proj).copy()
    gdf_coarse = gdf_coarse.to_crs(crs_proj).copy()

    # Ensure unique ID on fine polygons
    if fine_id_col not in gdf_fine.columns:
        gdf_fine = gdf_fine.reset_index(drop=True)
        gdf_fine[fine_id_col] = gdf_fine.index

    # Ensure valid geometries before overlay
    gdf_fine["geometry"] = gdf_fine.geometry.buffer(0)
    gdf_coarse["geometry"] = gdf_coarse.geometry.buffer(0)

    # Overlay to get intersections
    intersected = gpd.overlay(
        gdf_fine[[fine_id_col, "geometry"]],
        gdf_coarse[["geometry", value_col]],
        how="intersection",
    )

    # Remove rows with unsupported GeometryCollection geometry
    intersected = intersected[
        ~intersected.geometry.apply(lambda g: isinstance(g, GeometryCollection))
    ]

    # Optionally explode multipart geometries
    intersected = intersected.explode(index_parts=True, ignore_index=True)

    # Compute area of intersection
    intersected["area"] = intersected.geometry.area

    # Weighted value = value * area
    intersected["weighted_value"] = intersected[value_col] * intersected["area"]

    # Sum weighted values and areas for each fine polygon
    area_sum = intersected.groupby(fine_id_col)["area"].sum()
    value_sum = intersected.groupby(fine_id_col)["weighted_value"].sum()

    # Compute area-weighted average
    weighted_avg = value_sum / area_sum

    # Assign back to fine GeoDataFrame
    new_col = f"{value_col}_weighted"
    gdf_fine[new_col] = gdf_fine[fine_id_col].map(weighted_avg)

    return gdf_fine
