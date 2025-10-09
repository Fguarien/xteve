FROM python:3.11-slim

# set a working dir
WORKDIR /app

# copy app
COPY app /app

# install deps
RUN pip install --no-cache-dir requests

# create mount points
VOLUME ["/data/playlist", "/data/xmltv"]

# runtime
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Brussels

CMD ["python", "/app/generate_and_serve.py"]
