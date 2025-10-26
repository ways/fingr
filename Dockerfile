# Build: docker buildx build -t fingr -f Dockerfile .
# Run: docker run -it --rm fingr:latest
# Ubuntu-based image

FROM ubuntu:24.04

RUN apt-get update && apt-get install -y python3.13 python3-pip python3-venv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /var/fingr/
WORKDIR /var/fingr/

RUN python3.13 -m venv /var/fingr/venv && \
    /var/fingr/venv/bin/pip install --no-cache-dir wheel && \
    /var/fingr/venv/bin/pip install --no-cache-dir /var/fingr

COPY fingr.py motd.txt* deny.txt* useragent.txt* /var/fingr/

RUN useradd fingr && mkdir -p /var/fingr/data && chown -R fingr /var/fingr/data
USER fingr

EXPOSE 7979
ENTRYPOINT ["/var/fingr/venv/bin/python3", "fingr.py", "--verbose", "--host", "0.0.0.0"]
