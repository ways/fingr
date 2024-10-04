# Build: docker buildx build -t fingr -f Dockerfile .
# Run: docker run -it --rm fingr:latest

FROM ubuntu:24.04

RUN apt-get update && apt-get install -y python3 python3-venv
COPY requirements.txt /var/fingr/
RUN python3 -m venv /var/fingr/venv && /var/fingr/venv/bin/pip install wheel \
    && /var/fingr/venv/bin/pip install -r /var/fingr/requirements.txt
COPY fingr.py motd.txt* deny.txt* useragent.txt* /var/fingr/

WORKDIR /var/fingr/

RUN useradd fingr && mkdir /var/fingr/data && chown -R fingr /var/fingr/data
USER fingr

EXPOSE 7979
ENTRYPOINT [ "/var/fingr/venv/bin/python3", "fingr.py", "--verbose", "--host", "0.0.0.0" ]
