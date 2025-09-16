"""Add vpuid to the divides layers of oCONUS gpkgs by getting it from the divide-attributes layer."""

import sqlite3

import fiona
import geopandas as gpd
import pandas as pd


def update_divides_with_vpuid(in_gpkg: str, out_gpkg: str):
    """Update the divides layer in a GPKG file by adding vpuid from the divide-attributes layer."""
    print(f"Old GPKG: {in_gpkg}")

    # Read divides and attributes
    divides = gpd.read_file(in_gpkg, layer="divides")
    divide_attrs = gpd.read_file(in_gpkg, layer="divide-attributes")

    # Merge vpuid from attributes
    divides_with_vpuid = divides.merge(
        divide_attrs[["divide_id", "vpuid"]], on="divide_id", how="left"
    )

    # Get list of layers
    layers = fiona.listlayers(in_gpkg)

    # Copy layers into new GPKG
    for layer in layers:
        print(f"Processing layer: {layer}")
        try:
            gdf = gpd.read_file(in_gpkg, layer=layer)

            if "geometry" in gdf and gdf.geometry.notnull().any():
                # Spatial layer
                if layer == "divides":
                    gdf = divides_with_vpuid
                gdf.to_file(out_gpkg, layer=layer, driver="GPKG")
            else:
                # Non-spatial table → use pandas + sqlite
                df = pd.read_sql_query(
                    f'SELECT * FROM "{layer}"', sqlite3.connect(in_gpkg)
                )
                with sqlite3.connect(out_gpkg) as conn_out:
                    df.to_sql(layer, conn_out, if_exists="replace", index=False)

        except Exception as e:
            print(f"⚠️ Could not process layer {layer}: {e}")

    print(f"✅ New GPKG written: {out_gpkg}")


# Example usage
vpus = ["ak", "hi", "prvi"]
for vpu in vpus:
    old_gpkg = f"/home/yuqiong.liu/work/data/gpkg_v2.2/vpu_divides/vpu_{vpu}_old.gpkg"
    new_gpkg = f"/home/yuqiong.liu/work/data/gpkg_v2.2/vpu_divides/vpu_{vpu}.gpkg"

    update_divides_with_vpuid(old_gpkg, new_gpkg)
