# future: FROM bgruening/galaxy-stable:latest
FROM quay.io/qiime2/galaxy-qiime2

ENV \
GALAXY_CONFIG_TOOL_CONFIG_FILE=/qiime2_tools/qiime2_tool_conf.xml \
GALAXY_CONFIG_CONDA_AUTO_INSTALL=true \
GALAXY_CONFIG_CONDA_ENSURE_CHANNELS=https://packages.qiime2.org/qiime2/latest/tested/,iuc,conda-forge,bioconda,defaults

COPY tools/ /qiime2_tools/
COPY qiime2_tool_conf.xml /qiime2_tools/
