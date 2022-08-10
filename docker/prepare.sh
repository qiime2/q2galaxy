set -ex

cd $(dirname $(realpath -s $0))

TAG=$(echo $1 | cut -d- -f2 )
ENV_P=../__tmp_q2galaxy_env_$TAG

conda env create --force -p $ENV_P --file $1

mkdir -p tools/
rm -rf tools/*
conda run -p $ENV_P q2galaxy template all tools/
conda run -p $ENV_P q2galaxy template tool-conf '/qiime2_tools/' qiime2_tool_conf.xml

echo '# for publishing, add quay.io/qiime2/ prefix to the tag'
echo sudo docker build -t q2galaxy:$TAG .
