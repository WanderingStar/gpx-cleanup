FROM jupyter/scipy-notebook

COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt
RUN jupyter labextension install @jupyterlab/geojson-extension
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager jupyter-leaflet