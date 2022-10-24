# MAINTAINER Elias Ruefenacht | University of Bern | elias.ruefenacht@unibe.ch
FROM python:3.9-slim-bullseye

# copy the requirements file
RUN mkdir -p /app
COPY requirements.txt /app/requirements.txt

# create the necessary directories
RUN mkdir -p /app/data/input && \
	mkdir -p /app/data/scratch && \
	mkdir -p /app/data/output && \
	mkdir -p /app/env && \
    mkdir -p /install

# establish the python virtual environment
ENV VIRTUAL_ENV=/app/env/
RUN python3 -m venv $VIRTUAL_ENV && \
	$VIRTUAL_ENV/bin/pip install --upgrade pip && \
	$VIRTUAL_ENV/bin/pip install --no-cache-dir -r /app/requirements.txt && \
	$VIRTUAL_ENV/bin/pip install --no-cache-dir opencv-python-headless

# install X11 support for vtk
RUN apt-get update -y && \
    apt-get install -y libx11-dev libgl1-mesa-glx libxrender1

# copy the application
COPY . /app

# set the necessary environment variables
ENV INPUT_DATA_DIR=/app/data/input
ENV SCRATCH_DATA_DIR=/app/data/scratch
ENV OUTPUT_DATA_DIR=/app/data/output
ENV MODEL_DIR_PATH=/app/data/model/

# set inference related environment variables
ARG BATCH_SIZE=4
ENV BATCH_SIZE=$BATCH_SIZE
ENV CUDA_VISIBLE_DEVICES=0

# add a non-privileged user, change the ownership and mode and hinder the root login
RUN groupadd -r work && \
    useradd -m -r -g work work && \
    chown -v -H -R work:work /app/data && \
    chown -v -H -R work:work /app/main.py  && \
    chown -v -H -R work:work /app/entrypoint.sh && \
    chmod -R 766 /app/data && \
    chmod 777 /app/data/output && \
    chmod +x /app/entrypoint.sh && \
    chsh -s /usr/sbin/nologin root

# expose port 5000 for communication
EXPOSE 5000

# set the user work as default
USER work

# set the work directory
WORKDIR /app

# set the entrypoint
CMD ["/bin/bash", "./entrypoint.sh"]
#CMD ["/bin/bash"]