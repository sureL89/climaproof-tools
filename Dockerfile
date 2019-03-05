ARG BASE_CONTAINER=continuumio/miniconda3
FROM $BASE_CONTAINER

LABEL maintainer="Climaproof <g.seyerl@posteo.at>"

USER root

# pre-requisites
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    apt-utils \
    build-essential \
    libssl-dev && \
    rm -rf /var/lib/apt/lists/*

#ADD src /opt/src
#ADD data /opt/data


# packages installed globally
#RUN conda install --quiet --yes \
#    -c conda-forge 'iris=2.2' && \
#    -c conda-forge 'ipywidgets' && \
#    fix-permissions $CONDA_DIR && \
#    fix-permissions /home/$NB_USER

RUN /opt/conda/bin/conda install -y --quiet \
    -c conda-forge 'iris=2.2'

#RUN /opt/conda/bin/bokeh serve --show main.py
#ENTRYPOINT [ "/opt/conda/bin/bokeh", "serve", "--show main.py" ]
#EXPOSE 5100

COPY ./app /app

# Add entrypoint (this allows variable expansion)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app
ENV ORIGIN="127.0.0.1:5100" PORT="5100" PREFIX="" LOG_LEVEL="info"

ENTRYPOINT ["/entrypoint.sh"]
