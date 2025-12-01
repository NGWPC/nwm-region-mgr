#!/bin/bash
# 
# rte_build.sh
# 
# This script builds the region_rte image for setting up the regionalization runtime environment. 
# It includes nwm-region-mgr, as well as regionalization.py and config files for regionalization: 
#   configs/config_general.yaml, configs/config_formreg.yaml, configs/config_parreg.yaml.
# 
# See config.bashrc for configuration. Components can be installed from GitHub or from local source code.
# 
# Input data required (s3://ngwpc-dev/regionalization/data/inputs/) can be downloaded or mounted at runtime.

set -euo pipefail
set -x

source config.bashrc

TIMESTAMP=`date '+%Y%m%d%H%M%S'`

info "Building image: ${TARGET_IMAGE_NAME}"
sudo docker build -t ${TARGET_IMAGE_NAME} -f Dockerfile.rte ${NO_CACHE} \
    --build-arg REPO_TAG__REGION_MGR="${COMPONENT__REGION_MGR__REMOTE_REPO_TAG}" \
    ".." \
    |& tee "docker_logs/build/${TARGET_IMAGE_NAME}-${TIMESTAMP}.log"

info "Built image: ${TARGET_IMAGE_NAME}"
info "Command to start and enter container without executing anything: sudo docker run --entrypoint /bin/bash -it --rm ${TARGET_IMAGE_NAME}"


exit 0

