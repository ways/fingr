# Build: docker build -t fingr .
# Run: docker run -it --rm fingr:latest
# Distroless image for minimal attack surface and security

# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install uv and build dependencies for numpy
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install system dependencies needed for numpy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgfortran5 \
    libgomp1

# Copy project files
COPY pyproject.toml .
COPY fingr/ fingr/
COPY fingr.py .

# Install dependencies with uv
# UV_COMPILE_BYTECODE: Precompile Python files to .pyc for faster startup
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN uv pip install --system --no-cache .

# Runtime stage - distroless
FROM gcr.io/distroless/python3-debian12:nonroot

# Copy required shared libraries from builder for numpy C extensions
COPY --from=builder /usr/lib/x86_64-linux-gnu/libgfortran.so.5* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libquadmath.so.0* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libgomp.so.1* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /lib/x86_64-linux-gnu/libgcc_s.so.1* /lib/x86_64-linux-gnu/

# Copy Python packages and application
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY motd.txt* deny.txt* useragent.txt* /app/
COPY fingr/ /app/fingr/
COPY fingr.py /app/

WORKDIR /app
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages

EXPOSE 7979
ENTRYPOINT ["/usr/bin/python3", "fingr.py", "--verbose", "--host", "0.0.0.0"]
