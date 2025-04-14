# FROM bgruening/galaxy-stable:24.2
# FROM quay.io/qiime2/galaxy-qiime2
# FROM locally-built-galaxy:24.2
FROM quay.io/bgruening/galaxy:24.2

ENV \
GALAXY_CONFIG_TOOL_CONFIG_FILE=/qiime2_tools/qiime2_tool_conf.xml \
GALAXY_CONFIG_CONDA_AUTO_INSTALL=true \
GALAXY_CONFIG_CONDA_ENSURE_CHANNELS=https://packages.qiime2.org/qiime2/2024.10/amplicon/released,iuc,conda-forge,bioconda,defaults

# Install Visualisation
RUN install-biojs msa

COPY tools/ /qiime2_tools/
COPY qiime2_tool_conf.xml /qiime2_tools/

# Mark folders as imported from the host.
VOLUME ["/export/", "/data/", "/var/lib/docker"]

EXPOSE :80
EXPOSE :21

# Autostart script that is invoked during container start
CMD ["/usr/bin/startup"]
