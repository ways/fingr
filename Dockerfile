# Build: docker buildx build -t fingr -f Dockerfile .
# Run: docker run -it --rm fingr:latest

# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/packages -r requirements.txt

# Runtime stage - distroless
FROM gcr.io/distroless/python3-debian12:nonroot

COPY --from=builder /app/packages /app/packages
COPY fingr.py motd.txt* deny.txt* useragent.txt* /app/

WORKDIR /app
ENV PYTHONPATH=/app/packages

EXPOSE 7979
ENTRYPOINT ["/usr/bin/python3", "fingr.py", "--verbose", "--host", "0.0.0.0"]
