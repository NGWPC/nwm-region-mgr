#!/bin/bash

set -euo pipefail

OPTIND=1

docker=false
parreg=false
formreg=false
ngen=false
eval=false
ARGS=$(getopt -o dpfneh --long docker,parreg,formreg,ngen,eval,help -- "$@")

if [ $? != 0 ] ; then echo "Failed parsing options." >&2 ; exit 1 ; fi
eval set -- "$ARGS"

# Accept -d (docker) and -p (parreg) flags
while true; do
    case "$1" in
        -d|--docker) docker=true 
            shift;;
        -f|--formreg) formreg=true 
            shift;;
        -p|--parreg) parreg=true 
            shift;;
        -n|--ngen) ngen=true 
            shift;;
        -e|--eval) eval=true 
            shift;;
        -h|--help) echo "Usage: $0 [-d|--docker] [-p|--parreg] [-f|--formreg] [-n|--ngen] [-e|--eval]" >&2; exit 1 ;;
        --) shift; break ;;
        *) echo "Internal error!" ; exit 1 ;;
    esac
done

function docker_run {
    time sudo docker run --entrypoint python \
        -v $(pwd)/data/:/ngen-app/nwm-region-mgr/data \
        -v $(pwd)/data/:/data \
        -v $(pwd)/sample_files/:/ngen-app/nwm-region-mgr/sample_files \
        -v $(pwd)/sample_files/:/sample_files \
        --rm ngen_rte $*
}

function docker_run_ngen {
    time sudo docker run --entrypoint "/bin/bash" -it\
        -v $(pwd)/data/:/ngen-app/nwm-region-mgr/data \
        -v $(pwd)/data/:/data \
        -v $(pwd)/sample_files/:/ngen-app/nwm-region-mgr/sample_files \
        -v $(pwd)/sample_files/:/sample_files \
        --rm ngen_rte -c " ulimit -n 60000 && python $*"
        
}

######### Docker Build #########
if [ "$docker" = true ]; then
    git clone git@github.com:NGWPC/nwm-rte.git 
    (cd nwm-rte && \
    git fetch && \
    git checkout region && \
    git pull && \
    ./ngen_rte_build.sh)


    ##### For development #####
    # (cd nwm-rte && \
    # ./ngen_rte_build.sh)
    # # rm -rf nwm-rte
fi

######### Regionalization #########
if [ "$parreg" = true ]; then

    docker_run "/ngen-app/nwm-region-mgr/regionalization.py" \
        "/ngen-app/nwm-region-mgr/sample_files/configs"
fi

if [ "$formreg" = true ]; then

    docker_run "/ngen-app/nwm-region-mgr/run_formreg.py" \
        "/ngen-app/nwm-region-mgr/sample_files/configs/config_general.yaml" \
        "/ngen-app/nwm-region-mgr/sample_files/configs/config_formreg.yaml"
fi
######### RUN NGEN #########
if [ "$ngen" = true ]; then


docker_run_ngen "/ngen-app/nwm-region-mgr/run_ngen_vpu_docker.py" \
    --config_ngen "/ngen-app/nwm-region-mgr/sample_files/configs/config_ngen.yaml"
fi

######### Run EVAL #########

if [ "$eval" = true ]; then
    docker_run -m nwm.verf \
        "/ngen-app/nwm-region-mgr/sample_files/configs/config_eval.yaml" 
fi