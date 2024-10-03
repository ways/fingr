# syntax=docker/dockerfile:1

# Build: docker buildx build -t fingr -f Dockerfile .
# Run: docker run -it --rm fingr:latest

FROM python:3.12-alpine3.20

COPY requirements.txt /var/fingr/
RUN python3 -m venv /var/fingr/venv && /var/fingr/venv/bin/pip install wheel \
    && /var/fingr/venv/bin/pip install -r /var/fingr/requirements.txt
COPY fingr.py motd.txt* deny.txt* useragent.txt* /var/fingr/

WORKDIR /var/fingr/

RUN adduser --disabled-password fingr && mkdir /var/fingr/data && chown -R fingr /var/fingr/data
USER fingr

EXPOSE 7979
ENTRYPOINT [ "/var/fingr/venv/bin/python3", "fingr.py", "--verbose", "--host", "0.0.0.0" ]
