set -ex

cd $(dirname $(realpath -s $0))

TAG=$(echo $1 | cut -d- -f1)
METAPACKAGE=$(echo $1 | cut -d- -f1,2,3 )
METAPACKAGE="${METAPACKAGE//-/@}"
METAPACKAGE="${METAPACKAGE/@/-}"
ENV_P=../__tmp_q2galaxy_env_$TAG

conda env create -p $ENV_P --file $1

mkdir -p tools/
rm -rf tools/*
conda run -p $ENV_P q2galaxy template all tools/ --metapackage $METAPACKAGE

echo sudo docker build -t q2galaxy:$TAG .
