# Build: docker build -t fingr -f Dockerfile.ubuntu .
# Run: docker run -it --rm fingr:latest

FROM ubuntu:24.04
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libgfortran5 \
    libgomp1 \
    cl-cffi \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN useradd --home-dir=/app fingr && chown -R fingr /app
USER fingr

COPY pyproject.toml uv.lock ./

# Install dependencies with uv
# UV_COMPILE_BYTECODE: Precompile Python files to .pyc for faster startup
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

RUN uv python install 3.14
RUN uv sync --locked --no-cache

COPY fingr.py ./
COPY fingr/ ./fingr/

EXPOSE 7979
ENTRYPOINT ["uv", "run", "--no-cache", "./fingr.py", "--verbose", "--host", "0.0.0.0"]
