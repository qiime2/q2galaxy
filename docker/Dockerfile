FROM quay.io/bgruening/galaxy:24.2

ENV \
GALAXY_CONFIG_TOOL_CONFIG_FILE=/qiime2_tools/qiime2_tool_conf.xml \
GALAXY_CONFIG_CONDA_AUTO_INSTALL=true \
GALAXY_CONFIG_CONDA_ENSURE_CHANNELS=https://packages.qiime2.org/qiime2/2025.4/amplicon/passed,iuc,conda-forge,bioconda,defaults

# Install Visualisation
RUN install-biojs msa

COPY tools/ /qiime2_tools/
COPY qiime2_tool_conf.xml /qiime2_tools/

# Mark folders as imported from the host.
VOLUME ["/export/", "/data/", "/var/lib/docker"]

RUN /export/tool_deps/_conda/bin/conda create -y --quiet --solver libmamba --override-channels \
    --channel https://packages.qiime2.org/qiime2/2025.4/amplicon/passed --channel iuc --channel \
    conda-forge --channel bioconda --channel defaults --name __qiime2-amplicon@2025.4 qiime2-amplicon=2025.4

EXPOSE 80
EXPOSE 21

# Autostart script that is invoked during container start
CMD ["/usr/bin/startup"]
