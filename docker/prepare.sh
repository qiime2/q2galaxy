set -ex

cd $(dirname $(realpath -s $0))

ENV_P=../__tmp_q2galaxy_env_qiime2-$2@$3

conda env create -p $ENV_P --file $1

mkdir -p tools/
rm -rf tools/*
conda run -p $ENV_P q2galaxy template all tools/ --metapackage __qiime2-$2@$3

echo sudo docker build -t q2galaxy:$3 .
