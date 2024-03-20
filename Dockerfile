# syntax=docker/dockerfile:1

# Build: docker buildx build -t fingr -f Dockerfile .
# Run: docker run -it --rm fingr:latest

FROM python:3.10.13-alpine3.19

COPY requirements.txt /var/fingr/
RUN python3 -m venv /var/fingr/venv && /var/fingr/venv/bin/pip install wheel \
    && /var/fingr/venv/bin/pip install -r /var/fingr/requirements.txt
COPY server.py motd.txt* deny.txt* /var/fingr/

WORKDIR /var/fingr/

#RUN useradd fingr
#USER fingr

EXPOSE 7979
ENTRYPOINT [ "/var/fingr/venv/bin/python3", "server.py" ]
