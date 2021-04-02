set -ex

cd $(dirname $(realpath -s $0))

TAG=$(echo $1 | cut -d- -f2 )
ENV_P=../__tmp_q2galaxy_env_$TAG

conda env create --force -p $ENV_P --file $1

echo TODO: remove this line when they are included already
conda install -p $ENV_P -c https://packages.qiime2.org/qiime2/latest/tested/ \
  -c conda-forge -c bioconda -c defaults -y q2galaxy q2-mystery-stew

mkdir -p tools/
rm -rf tools/*
conda run -p $ENV_P q2galaxy template all tools/

echo sudo docker build -t q2galaxy:$TAG .
