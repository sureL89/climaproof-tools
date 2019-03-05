# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
#ARG BASE_CONTAINER=jupyter/scipy-notebook
ARG BASE_CONTAINER=jupyter/minimal-notebook
FROM $BASE_CONTAINER

LABEL maintainer="Climaproof <maria.wind@boku.ac.at>"

USER root

# pre-requisites
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    apt-utils \
    build-essential \
    libssl1.0.0 \
    libssl-dev && \
    rm -rf /var/lib/apt/lists/*

USER $NB_UID

COPY model_selection_tool.ipynb /home/$NB_USER

# packages installed globally
RUN conda install --quiet --yes \
    -c conda-forge 'iris=2.2' && \
    -c conda-forge 'ipywidgets' && \
    fix-permissions $CONDA_DIR && \
    fix-permissions /home/$NB_USER

# Import matplotlib the first time to build the font cache.
ENV XDG_CACHE_HOME /home/$NB_USER/.cache/
RUN MPLBACKEND=Agg python -c "import matplotlib.pyplot" && \
fix-permissions /home/$NB_USER