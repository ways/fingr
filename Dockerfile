# Build: docker buildx build -t fingr .
# Run: docker run -it --rm fingr:latest
# Distroless image for minimal attack surface and security

# Build stage
FROM python:3.13-slim AS builder

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir --target=/app/packages /app

# Runtime stage - distroless
FROM gcr.io/distroless/python3-debian12:nonroot

COPY --from=builder /app/packages /app/packages
COPY fingr.py motd.txt* deny.txt* useragent.txt* /app/

WORKDIR /app
ENV PYTHONPATH=/app/packages

EXPOSE 7979
ENTRYPOINT ["/usr/bin/python3", "fingr.py", "--verbose", "--host", "0.0.0.0"]
