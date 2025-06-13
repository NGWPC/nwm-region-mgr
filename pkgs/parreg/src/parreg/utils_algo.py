import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from pyproj import CRS
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def ensure_projected(gdf: gpd.GeoDataFrame, target_crs: str = "EPSG:5070") -> gpd.GeoDataFrame:
    """Reprojects a GeoDataFrame to a projected CRS if currently in geographic CRS."""
    crs = CRS.from_user_input(gdf.crs)
    if crs.is_geographic:
        return gdf.to_crs(target_crs)
    return gdf


def compute_pairwise_centroid_distances(
    group_a: gpd.GeoDataFrame,
    group_b: gpd.GeoDataFrame,
    id_col_a: str = "divide_id",
    id_col_b: str = "divide_id",
    id_col_a_return: str = "donor_id",
    id_col_b_return: str = "receiver_id",
    distance_threshold: float = None,
    n_jobs: int = -1,  # Use all available cores
) -> pd.DataFrame:
    """
    Compute pairwise distances between centroids of two GeoDataFrames.

    Parameters
    ----------
    group_a : gpd.GeoDataFrame
        The first GeoDataFrame containing geometries and IDs.
    group_b : gpd.GeoDataFrame
        The second GeoDataFrame containing geometries and IDs.
    id_col_a : str, optional
        The name of the ID column in group_a. Default is "id".
    id_col_b : str, optional
        The name of the ID column in group_b. Default is "id".
    id_col_a_return : str, optional
        The name of the ID column to return from group_a. Default is "donor_id".
    id_col_b_return : str, optional
        The name of the ID column to return from group_b. Default is "receiver_id".
    distance_threshold : float, optional
        If provided, only distances less than or equal to this value will be included in the output.
    n_jobs : int, optional
        The number of jobs to run in parallel. Default is -1, which uses all available cores.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the centroid distances between each pair of polygons from the two GeoDataFrames in (km),
        where the columns are indexed by polygon ids from group_a, and the rows are indexed by polygon ids from group_b.
    """

    # Precompute centroids to speed up
    centroids_a = group_a.geometry.centroid
    centroids_b = group_b.geometry.centroid

    # Ensure projected centroids_a and centroids_b so that pairwise distance can be properly calculated
    centroids_a = ensure_projected(centroids_a)
    centroids_b = ensure_projected(centroids_b)

    a_ids = group_a[id_col_a].values
    b_ids = group_b[id_col_b].values

    def compute_distances_for_a(i):
        centroid_a = centroids_a.iloc[i]
        distances = centroids_b.distance(centroid_a)

        result = []
        for j, dist in enumerate(distances):
            if distance_threshold is None or dist <= distance_threshold:
                result.append(
                    {
                        f"{id_col_a_return}": a_ids[i],
                        f"{id_col_b_return}": b_ids[j],
                        "centroid_distance": round(dist / 1000),  # Convert to km
                    }
                )
        return result

    results = Parallel(n_jobs=n_jobs, backend="threading")(
        delayed(compute_distances_for_a)(i) for i in range(len(group_a))
    )

    # Flatten the results
    flat_results = [item for sublist in results for item in sublist]
    # return pd.DataFrame(flat_results)

    df_long = pd.DataFrame(flat_results)
    # print(df_long.head())
    df_wide = df_long.pivot(index=id_col_b_return, columns=id_col_a_return, values="centroid_distance")

    return df_wide


# get the valid attributes to be processed based on the valid attributes of the first receiver
def get_valid_attrs(recs0, recs1, dfAttr0, attrs, config):
    dt1 = dfAttr0[~dfAttr0["is_donor"]]
    dt1 = dt1[dt1.divide_id.isin(recs0) & ~dt1.divide_id.isin(recs1)].iloc[0]
    dt1 = dt1[~dt1.index.isin(config["non_attr_cols"])]
    vars = config["non_attr_cols"] + dt1.index[~dt1.isna()].tolist()
    dfAttr = dfAttr0[vars]
    vars = [value for value in vars if value in attrs]  # attrs included for current round
    vars0 = [value for value in attrs if value not in vars]  # attrs excluded for current round

    if len(vars) > 0:
        if len(vars0) > 0:
            print("Excluding " + str(len(vars0)) + " attributes: " + ",".join(vars0))
        else:
            print("Using all attributes")

    # ignore donors & receivers with NA attribute values
    dfAttr = dfAttr.dropna(subset=[x for x in attrs if x not in vars0], inplace=False)

    if dfAttr.shape[0] == 0:
        print("WARNING: no valid attributes found for the following receivers: ")
        print(dfAttr["id"].tolist())

    return dfAttr


# apply Principal Componenet Analysis to the attributes
def apply_pca(data0, min_var=0.8):
    # standardize the data
    scaled_data = StandardScaler().fit_transform(data0)

    # perform PCA given the required minimum total explained variance
    pca = PCA(min_var, svd_solver="auto", random_state=7777)
    pca.fit(scaled_data)
    n1 = pca.n_components_

    print("Number of PCs selected: " + str(n1))
    print("PCA total portion of variance explained ... " + str(sum(pca.explained_variance_ratio_)))
    x_pca = pca.transform(scaled_data)

    # standardize the reduced data (comment out because it is not necessary)
    # x_pca = StandardScaler().fit_transform(x_pca)

    # convert to dataframe
    strs1 = ["pc"] * n1
    strs2 = list(map(str, list(range(1, n1 + 1))))
    cols = [i + j for i, j in zip(strs1, strs2)]
    x_pca = pd.DataFrame(x_pca, columns=cols)

    # weights for chosen PCs are proporitonal to the variances they explained
    w1 = pca.explained_variance_ratio_ / sum(pca.explained_variance_ratio_)

    # return scores and weights
    return x_pca, w1


# apply a few additional constraints to donors identified (e.g., via Gower's distance or other techniques)
def apply_donor_constraints(rec, donors, dists, pars, dfAttr):
    # 1. narrow down to donors with the same snowiness category
    # snowy = dfAttr.query("id == @rec & tag=='receiver'")['snowy']
    # snowy1 = dfAttr.query("id in @donors & tag=='donor'")['snowy']
    snowy = dfAttr[dfAttr["divide_id"] == rec]["snowy"].values[0]
    snowy1 = dfAttr[dfAttr["divide_id"].isin(donors)]["snowy"].values
    # ix1 = snowy1.isin(snowy)
    ix1 = np.isin(snowy1, snowy)
    if sum(ix1) > 0:
        dists = np.array(dists)[ix1]
        donors = np.array(donors)[ix1]

    # 2. further narrow down to those donors within maximum spatial distance defined
    ix1 = dists <= pars["max_spa_dist"]
    if sum(ix1) > 0:
        dists = np.array(dists)[ix1]
        donors = np.array(donors)[ix1]

    # 3. further narrow down based on screening attributes
    # for att1 in pars['max_attr_diff'].keys():
    #     ix1 = abs(np.array(dfAttr[~dfAttr['is_donor']][att1]) - \
    #         np.array(dfAttr[dfAttr['is_donor']][att1])) \
    #             <= pars['max_attr_diff'][att1]
    #     if sum(ix1) > 0:
    #         dists = np.array(dists)[ix1]
    #         donors = np.array(donors)[ix1]

    # 4. further narrow down to donors in the same HSG
    # hsg = dfAttr.query("id==@rec & tag=='receiver'")['hsg']
    # hsg1 = dfAttr.query("id in @donors & tag=='donor'")['hsg']
    # ix1 = hsg1.isin(hsg)
    # if sum(ix1) > 0:
    #     dists = np.array(dists)[ix1]
    #     donors = np.array(donors)[ix1]

    return donors, dists


# assign donors based on clusters and spatial distance and apply additional constrains
def assign_donors(scenario, donors, receivers, pars, dist_attr, dist_spatial, dfAttr):
    df_donor = pd.DataFrame()
    for rec1 in receivers:
        # get spatial distances
        dists1 = dist_spatial.loc[rec1, donors].to_numpy()

        # apply additional donor constraints
        if dfAttr is None:
            donors1 = donors.copy()
        else:
            donors1, dists1 = apply_donor_constraints(rec1, donors, dists1, pars, dfAttr)

        # if applicable, choose donor with the smallest attribute distances
        if dist_attr is not None:
            ix0 = [donors.index(i) for i in donors1]
            dist_attr = [dist_attr.iloc[i] for i in ix0]
            ix1 = np.argsort(dist_attr)[range(min(len(dist_attr), pars["n_donor_max"]))]
            dist_attr1 = np.array(dist_attr)[ix1]
            dists1 = dists1[ix1]
            donors1 = np.array(donors1)[ix1]

        # order donors by spatial distance
        ix1 = np.argsort(dists1)
        # dists1 = dists1.iloc[ix1]
        dists1 = dists1[ix1]
        donors1 = np.array(donors1)[ix1]

        # if the number of donors is greater than nDonorMax, ignore the additional donors
        nd_max = min(len(dists1), pars["n_donor_max"])
        dists1 = dists1[range(nd_max)]
        donors1 = donors1[range(nd_max)]

        # add the donor/receiver pair to the pairing table
        if len(donors1) > 0:
            pair1 = {
                "divide_id": rec1,
                "tag": scenario,
                "donor": donors1[0],
                "distSpatial": dists1[0],
                "donors": ",".join(donors1),
                "distSpatials": ",".join(map(str, pd.Series(dists1))),
            }

            # add attribute distance if applicable (e.g., for Gower & URF)
            if dist_attr is not None:
                dist_attr1 = np.array(dist_attr1)[ix1]  # sort according to spatial distance
                dist_attr1 = dist_attr1[
                    range(nd_max)
                ]  # ignore unneeded donor (likely not necessary given the treatment above)
                pair1["distAttr"] = dist_attr1[0]
                pair1["distAttrs"] = ",".join(map(str, pd.Series(dist_attr1)))

            df_donor = pd.concat((df_donor, pd.DataFrame(pair1, index=[0])), axis=0)

    return df_donor


# plot the clusters (using the first 6 components)
def plot_clusters(data1, labels, ndonor):
    fig = plt.figure(figsize=(20, 14))
    cols_all = [[0, 1], [0, 2], [3, 4], [3, 5]]
    for i1, cols in enumerate(cols_all):
        if max(cols) > data1.shape[1]:
            break
        ax = fig.add_subplot(2, 2, i1 + 1)

        # receiver - noise
        d1 = labels[ndonor:] == -1
        plt.scatter(data1.iloc[:, cols[0]][ndonor:][d1], data1.iloc[:, cols[1]][ndonor:][d1], c="grey", marker=".")

        # receiver non-noise
        d1 = labels[ndonor:] != -1
        plt.scatter(
            data1.iloc[:, cols[0]][ndonor:][d1],
            data1.iloc[:, cols[1]][ndonor:][d1],
            c=labels[ndonor:][d1],
            cmap="rainbow",
            marker=".",
        )
        plt.colorbar()

        # donor - noise
        d1 = labels[:ndonor] == -1
        plt.scatter(
            data1.iloc[:, cols[0]][:ndonor][d1], data1.iloc[:, cols[1]][:ndonor][d1], c="black", marker="x", s=100
        )

        # donor non-noise
        d1 = labels[:ndonor] != -1
        plt.scatter(
            data1.iloc[:, cols[0]][:ndonor][d1], data1.iloc[:, cols[1]][:ndonor][d1], c="green", marker="x", s=100
        )

        plt.title(data1.columns[cols[1]] + " vs " + data1.columns[cols[0]], fontsize=20, fontweight="bold")

    plt.subplots_adjust(left=0.07, bottom=0.07, right=0.95, top=0.93, hspace=0.15, wspace=0.03)
    plt.show()


# calculate spatial distance between all donors and receivers
def calculate_spatial_distance(shp_file, donors, receivers):
    print("compute donor-receiver spatial distance ...")

    # read in shapefile as GeoDataFrame
    shps = gpd.read_file(shp_file, layer="divides")

    # reproject from geodetic coordinates to meters (for distance calculation)
    shps = shps.to_crs(crs=3857)

    # narrow down donors and receiver GeoDataFrames to those needed
    id1 = "id"
    if "divide_id" in shps.columns:
        id1 = "divide_id"
    shps_rec = shps[shps[id1].isin(receivers)]
    shps_don = shps[shps[id1].isin(donors)]

    # reindex the GeoDataFrames by order of ids
    shps_rec = shps_rec.set_index(id1)
    shps_rec = shps_rec.reindex(receivers)
    shps_don = shps_don.set_index(id1)
    shps_don = shps_don.reindex(donors)

    # calculate centroids of donor and receiver catchments
    cent_don = shps_don["geometry"].centroid
    cent_rec = shps_rec["geometry"].centroid

    # convert centroids from GeoSeries to GeoDataFrame
    cent_don = gpd.GeoDataFrame(geometry=cent_don)
    cent_rec = gpd.GeoDataFrame(geometry=cent_rec)

    # calcualte distance between all receiver and donor centroids
    def calculate_distances(row):
        return cent_don.distance(row.geometry)

    distances = cent_rec.apply(calculate_distances, axis=1)

    # convert to km
    distances = distances.div(1000)
    distances = distances.astype(int)

    # reset the columns and index of the distance matrix
    distances.columns = donors
    distances.index = receivers

    return distances
