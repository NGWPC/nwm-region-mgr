#!/bin/bash

set -euo pipefail

### NO_CACHE: Passed to `docker build` call. Choose from: ["--no-cache", ""]. 
#NO_CACHE="--no-cache"
NO_CACHE=""


### Freeform name tag for image
# TARGET_IMAGE_NAME="eval_rte:`date '+%Y%m%d%H%M%S'`-${NGEN_SOURCE_MODE}"
TARGET_IMAGE_NAME="eval_rte"


##### Source of components; choose from ["remote", "local"]
## nwm-region-mgr
COMPONENT__REGION_MGR__SOURCE_MODE="remote"
COMPONENT__REGION_MGR__REMOTE_REPO_TAG="yliu_test_old_image" # only used if SOURCE_MODE="remote"

## nwm-eval-mgr
COMPONENT__EVAL_MGR__SOURCE_MODE="remote"
COMPONENT__EVAL_MGR__REMOTE_REPO_TAG="development" # only used if SOURCE_MODE="remote"

## nwm-verf
COMPONENT__VERF_MGR__SOURCE_MODE="remote"
COMPONENT__VERF_MGR__REMOTE_REPO_TAG="development" # only used if SOURCE_MODE="remote"


### Logging functions
BASENAME="$(basename "$(readlink -f "$0")")"
function log_to_stderr() { echo "[$(date -u +'%Y-%m-%dT%H:%M:%S%z')] ${BASENAME}: ${LINENO}: $*" >&2; }
function info() { log_to_stderr INFO: $*; }
function error() { log_to_stderr ERROR: $*; }
function fatal() { log_to_stderr FATAL ERROR: $*; exit 1; }