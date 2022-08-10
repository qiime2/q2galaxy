# future: FROM bgruening/galaxy-stable:latest
FROM quay.io/qiime2/galaxy-qiime2

ENV \
GALAXY_CONFIG_TOOL_CONFIG_FILE=/qiime2_tools/qiime2_tool_conf.xml \
GALAXY_CONFIG_CONDA_AUTO_INSTALL=true \
GALAXY_CONFIG_CONDA_ENSURE_CHANNELS=https://packages.qiime2.org/qiime2/2022.2/passed/core,iuc,conda-forge,bioconda,defaults

COPY tools/ /qiime2_tools/
COPY qiime2_tool_conf.xml /qiime2_tools/

#RUN nohup /usr/bin/startup
#RUN /tool_deps/_conda/bin/galaxy-wait -g http://127.0.0.1 -v --timeout 120
#RUN /tool_deps/_conda/bin/install_tool_deps -t /qiime2_tools/qiime2_tool_conf.xml -
copy installer.sh /usr/bin/install-non-ts
RUN chmod +x /usr/bin/install-non-ts
RUN install-non-ts
