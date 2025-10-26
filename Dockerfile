# Build: docker build -t fingr .
# Run: docker run -it --rm fingr:latest
# Distroless image for minimal attack surface and security

# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies needed for numpy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgfortran5 \
    libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Copy only pyproject.toml first to leverage Docker cache
COPY pyproject.toml .

# Create a minimal setup to install dependencies from pyproject.toml
# We create a dummy package structure so pip can resolve dependencies
RUN mkdir -p fingr_pkg && \
    echo "# Dummy" > fingr_pkg/__init__.py && \
    pip install --no-cache-dir --target=/app/packages . && \
    rm -rf fingr_pkg

# Runtime stage - distroless
FROM gcr.io/distroless/python3-debian12:nonroot

# Copy required shared libraries from builder for numpy C extensions
COPY --from=builder /usr/lib/x86_64-linux-gnu/libgfortran.so.5* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libquadmath.so.0* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libgomp.so.1* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /lib/x86_64-linux-gnu/libgcc_s.so.1* /lib/x86_64-linux-gnu/

COPY --from=builder /app/packages /app/packages
COPY fingr.py motd.txt* deny.txt* useragent.txt* /app/

WORKDIR /app
ENV PYTHONPATH=/app/packages

EXPOSE 7979
ENTRYPOINT ["/usr/bin/python3", "fingr.py", "--verbose", "--host", "0.0.0.0"]
