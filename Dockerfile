ARG BASE_CONTAINER=continuumio/miniconda3
FROM $BASE_CONTAINER

LABEL maintainer="Climaproof <g.seyerl@posteo.at>"

USER root

# pre-requisites
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libssl-dev \
    qtbase5-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


#RUN /opt/conda/bin/conda install -y --quiet \
#    -c conda-forge 'iris=2.2' && \
#    /opt/conda/bin/conda clean -ay
#
#COPY ./mst /mst

COPY ./environment_p36.yml .
RUN /opt/conda/bin/conda env create -n p36 -f environment_p36.yml
RUN /opt/conda/bin/conda clean -ay
RUN echo "source activate p36" > ~/.bashrc
ENV PATH /opt/conda/envs/p36/bin:$PATH

COPY ./mst /app/mst
COPY ./dst /app/dst
WORKDIR /app
ENV ORIGIN="127.0.0.1:5100" PORT="5100" PREFIX="" LOG_LEVEL="info"

# Add entrypoint (this allows variable expansion)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
