ARG BASE_CONTAINER=continuumio/miniconda3
FROM $BASE_CONTAINER

LABEL maintainer="Climaproof <g.seyerl@posteo.at>"

USER root

# pre-requisites
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libssl-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


RUN /opt/conda/bin/conda install -y --quiet \
    -c conda-forge 'iris=2.2' && \
    /opt/conda/bin/conda clean -ay

COPY ./app /app

# Add entrypoint (this allows variable expansion)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app
ENV ORIGIN="127.0.0.1:5100" PORT="5100" PREFIX="" LOG_LEVEL="info"

ENTRYPOINT ["/entrypoint.sh"]
