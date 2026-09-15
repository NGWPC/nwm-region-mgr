#!/bin/bash
set -euo pipefail

# -----------------------------------------------------------------------------
# setup_region.sh
#
## \brief
## Set up a regionalization environment for nwm-region-mgr.
##
## \details
## Downloads sample configuration files from nwm-region-mgr and regionalization
## scripts from nwm-rte. Static and sample data can be downloaded from S3 or an
## existing local data source can be specified using --alt_data_source.
##
## The downloaded configuration files contain placeholders for environment-
## specific values, including the number of processors, working directory, and
## static data directory. These placeholders are replaced with the appropriate
## values during setup.
##
## By default, static and sample data are downloaded from S3. Use
## --no-download-s3 to skip the download. Alternatively, --alt_data_source can
## be used to specify an existing local data source, in which case a symbolic
## link is created and the S3 download is skipped.
##
## \usage
## ./setup_region.sh [OPTIONS]
##
## Arguments:
## \option -o, --org ORG
##     GitHub organization containing the nwm-region-mgr and nwm-rte
##     repositories. Default: NGWPC.
##
## \option -b, --branch BRANCH
##     GitHub branch from which configuration files and scripts are downloaded.
##     Default: development.
##
## \option -n, --no-download-s3
##     Skip downloading static and sample data from S3. By default, the data
##     are downloaded.
##
## \option -r, --s3-static-region S3_STATIC_REGION
##     S3 path containing static and sample data for "region" and "eval"
##
## \option -f, --s3-static-forcing S3_STATIC_FORCING
##     S3 path containing static forcing data for "ngen".
##
## \option -a, --alt-data-source ALT_DATA_SOURCE
##     Use an existing local directory as the static data source instead of
##     downloading data from S3. A symbolic link is created at STATIC_DIR.
##
## \option -p, --nprocs NPROCS
##     Number of processors to use for regionalization. By default, the total
##     number of available processors minus two is used, with a minimum of one.
##
## \option -d, --domain DOMAIN
##     Domain for regionalization. Determines the source directory for the
##     sample configuration files: configs/ for conus, configs_ak/ for ak,
##     configs_hi/ for hi, and configs_prvi/ for prvi. Default: conus.
##
## \option -h, --help
##     Display usage information.
##
## \example
## ./setup_region.sh
##
## \example
## ./setup_region.sh --nprocs 8
##
## \example
## ./setup_region.sh --alt_data_source /data/shared/regionalization
##
# -----------------------------------------------------------------------------

# defaults
ORG="NGWPC"
BRANCH="development"
S3_STATIC_REGION="s3://ngwpc-dev/nwm-tools-data/regionalization/data/inputs"
S3_STATIC_FORCING="s3://ngwpc-dev/nwm-tools-data/esmf"
DOWNLOAD_S3=true
DEFAULT_NPROCS=$(( $(nproc) - 2 ))
DEFAULT_NPROCS=$(( DEFAULT_NPROCS < 1 ? 1 : DEFAULT_NPROCS ))
NPROCS="$DEFAULT_NPROCS"
DOMAIN="conus"

# parse command line arguments (if any)
ARGS=$(getopt -o o:b:nr:f:a:p:d:h \
    --long org:,branch:,no-download-s3,s3-static-region:,s3-static-forcing:,alt-data-source:,nprocs:,domain:,help \
    -n "$0" -- "$@") || exit 1
eval set -- "$ARGS"

while true; do
    case "$1" in
        -o|--org)
            ORG="$2"
            shift 2
            ;;
        -b|--branch)
            BRANCH="$2"
            shift 2
            ;;
        -n|--no-download-s3)
            DOWNLOAD_S3=false
            shift
            ;;
        -r|--s3-static-region)
            S3_STATIC_REGION="$2"
            shift 2
            ;;
        -f|--s3-static-forcing)
            S3_STATIC_FORCING="$2"
            shift 2
            ;;
        -a|--alt-data-source)
            ALT_DATA_SOURCE="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -p|--nprocs)
            if ! [[ "$2" =~ ^[0-9]+$ ]] || [ "$2" -lt 1 ]; then
                echo "Error: NPROCS must be a positive integer: $2" >&2
                exit 1
            fi
            NPROCS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -o, --org ORG                  GitHub organization (default: NGWPC)"
            echo "  -b, --branch BRANCH            GitHub branch (default: development)"
            echo "  -n, --no-download-s3           Do not download static and sample data from S3 (default: download)"
            echo "  -r, --s3-static-region S3_STATIC_REGION    S3 path for static data (default: $S3_STATIC_REGION)"
            echo "  -f, --s3-static-forcing S3_STATIC_FORCING  S3 path for static forcing data (default: $S3_STATIC_FORCING)"
            echo "  -a, --alt-data-source ALT_DATA_SOURCE      Alternative data source (default: none)"
            echo "  -d, --domain DOMAIN            Domain for regionalization (default: conus)"
            echo "                                 Valid domains: conus, ak, hi, prvi"
            echo "  -p, --nprocs NPROCS            Number of processors to use (default: $DEFAULT_NPROCS)"
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Invalid option: $1" >&2
            exit 1
            ;;
    esac
done

# Validate domain and determine the source configuration directory.
case "$DOMAIN" in
    conus)
        CONFIG_SOURCE_DIR="configs"
        ;;
    ak)
        CONFIG_SOURCE_DIR="configs_ak"
        ;;
    hi)
        CONFIG_SOURCE_DIR="configs_hi"
        ;;
    prvi)
        CONFIG_SOURCE_DIR="configs_prvi"
        ;;
    *)
        echo "Error: Unsupported domain '$DOMAIN'. Valid domains: conus, ak, hi, prvi" >&2
        exit 1
        ;;
esac

echo
echo "Starting setup for regionalization environment..."

WORK_DIR="$(realpath .)"
STATIC_DIR="${WORK_DIR}/static_data"

# If an alternative data source is specified, create a symbolic link to it.
# This also disables downloading static and sample data from S3.
if [ -n "${ALT_DATA_SOURCE:-}" ]; then
    if [ ! -d "$ALT_DATA_SOURCE" ]; then
        echo "Error: Alternative data source directory does not exist: $ALT_DATA_SOURCE" >&2
        exit 1
    fi

    ALT_DATA_SOURCE="$(realpath "$ALT_DATA_SOURCE")"

    if [ -d "$STATIC_DIR" ] || [ -L "$STATIC_DIR" ]; then
        if [ -e "${STATIC_DIR}.bak" ] || [ -L "${STATIC_DIR}.bak" ]; then
            echo "Error: Backup path already exists: ${STATIC_DIR}.bak" >&2
            exit 1
        fi

        mv "$STATIC_DIR" "${STATIC_DIR}.bak"
        echo "Existing static data directory backed up to: ${STATIC_DIR}.bak"
    fi

    ln -sfn "$ALT_DATA_SOURCE" "$STATIC_DIR"
    DOWNLOAD_S3=false

    echo "Using alternative data source: $ALT_DATA_SOURCE"
    echo "Symbolic link created: $STATIC_DIR -> $ALT_DATA_SOURCE"
    echo "Skipping download of static and sample data from S3 due to alternative data source."
fi

download_github_file() {
    local repo="$1"
    local remote_path="$2"
    local local_path="$3"

    echo "  Downloading ${local_path}..."

    mkdir -p "$(dirname "$local_path")"

    if ! wget -q -O "$local_path" \
        "https://raw.githubusercontent.com/${ORG}/${repo}/${BRANCH}/${remote_path}"; then
        echo "Error: Failed to download ${repo}/${remote_path}" >&2
        rm -f "$local_path"
        exit 1
    fi
}

echo
echo "Downloading sample configuration files from $ORG repo nwm-region-mgr"
download_github_file \
    "nwm-region-mgr" \
    "${CONFIG_SOURCE_DIR}/config_general.yaml" \
    "configs/config_general.yaml"

download_github_file \
    "nwm-region-mgr" \
    "${CONFIG_SOURCE_DIR}/config_formreg.yaml" \
    "configs/config_formreg.yaml"

download_github_file \
    "nwm-region-mgr" \
    "${CONFIG_SOURCE_DIR}/config_parreg.yaml" \
    "configs/config_parreg.yaml"

download_github_file \
    "nwm-region-mgr" \
    "${CONFIG_SOURCE_DIR}/config_ngen.yaml" \
    "configs/config_ngen.yaml"

download_github_file \
    "nwm-region-mgr" \
    "${CONFIG_SOURCE_DIR}/config_eval.yaml" \
    "configs/config_eval.yaml"

echo
echo "Downloading RTE scripts for regionalization from $ORG repo nwm-rte"
download_github_file \
    "nwm-rte" \
    "bin_mounted/ngen_rte/run_regionalization.py" \
    "rte_scripts/run_regionalization.py"

download_github_file \
    "nwm-rte" \
    "run_region.sh" \
    "rte_scripts/run_region.sh"

download_github_file \
    "nwm-rte" \
    "sbatch_run_region.sh" \
    "rte_scripts/sbatch_run_region.sh"

chmod +x rte_scripts/run_region.sh
chmod +x rte_scripts/sbatch_run_region.sh

echo
if [ "$DOWNLOAD_S3" = true ]; then
    echo "Downloading static and sample data from S3 ..."

    aws s3 sync \
        "${S3_STATIC_REGION}/" \
        "${STATIC_DIR}/" \
        --only-show-errors

    aws s3 sync \
        "${S3_STATIC_FORCING}/" \
        "${STATIC_DIR}/ngen/" \
        --only-show-errors \
        --exclude "esmf_mesh/NWM/domain/geo_em_CONUS.nc"
else
    echo "Skipping download of static and sample data from S3."
fi

echo
echo "Replace placeholders in configs/config_general.yaml and configs/config_eval.yaml ..."

# Update <N_PROCS> in the general configuration file
sed -i "s|<NPROCS>|${NPROCS}|g" configs/config_general.yaml
echo "  <NPROCS> ->  ${NPROCS}"

# Update <WORK_DIR> in the general and evaluation configuration files
sed -i "s|<WORK_DIR>|${WORK_DIR}|g" configs/config_general.yaml
sed -i "s|<WORK_DIR>|${WORK_DIR}|g" configs/config_eval.yaml
echo "  <WORK_DIR> ->  ${WORK_DIR}"

# Update <STATIC_DATA_DIR> in the general and evaluation configuration files
sed -i "s|<STATIC_DATA_DIR>|${STATIC_DIR}|g" configs/config_general.yaml
sed -i "s|<STATIC_DATA_DIR>|${STATIC_DIR}|g" configs/config_eval.yaml
echo "  <STATIC_DATA_DIR> ->  ${STATIC_DIR}"

echo
echo "***************************************************************************"
echo "Setup completed."
echo "Check n_procs, base_dir, and static_data_dir in configs/config_general.yaml"
echo "  to ensure they are correctly set."
echo "Run the regionalization application using 'rte_scripts/run_region.sh', e.g., "
echo "  ./rte_scripts/run_region.sh -p"
echo "For help and more options, run:"
echo "  ./rte_scripts/run_region.sh -h"
echo "***************************************************************************"