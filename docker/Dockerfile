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

# Install base utilities
RUN apt-get update \
    && apt-get install -y build-essential \
    && apt-get install -y wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install miniconda
ENV CONDA_DIR /opt/conda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda

# Put conda in path so we can use conda activate
ENV PATH=$CONDA_DIR/bin:$PATH

# RUN  apt-get update \
#   && apt-get install -y wget \
#   && rm -rf /var/lib/apt/lists/*
# RUN wget https://repo.continuum.io/miniconda/Miniconda3-4.5.4-Linux-x86_64.sh -O /tmp/miniconda.sh
# RUN /bin/bash /tmp/miniconda.sh -b -p /opt/conda && \
#     rm /tmp/miniconda.sh && \
#     echo "export PATH=/opt/conda/bin:$PATH" > /etc/profile.d/conda.sh
# ENV PATH /opt/conda/bin:$PATH
RUN conda env create -n qiime2-amplicon-2024.10 --file https://data.qiime2.org/distro/amplicon/qiime2-amplicon-2024.10-py310-linux-conda.yml

EXPOSE :80
EXPOSE :21

# Autostart script that is invoked during container start
CMD ["/usr/bin/startup"]
