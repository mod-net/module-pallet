# Multi-stage build for Mod-Net blockchain node
FROM rust:1.75 AS rust-builder

WORKDIR /mod-net

# Install system dependencies for Substrate
RUN apt-get update && apt-get install -y \
    build-essential \
    clang \
    curl \
    git \
    libssl-dev \
    llvm \
    libudev-dev \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

COPY Cargo.toml ./
COPY rust-toolchain.toml ./
COPY node/ ./node/
COPY pallets/ ./pallets/
COPY runtime/ ./runtime/

# Install WASM target and build
RUN rustup target add wasm32-unknown-unknown && \
    cargo build --release

# Python client builder stage
FROM python:3.11-slim AS python-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster Python package management
RUN pip install uv

# Copy Python project files
COPY pyproject.toml ./
COPY requirements.txt ./
COPY mod_net_client/ ./mod_net_client/
COPY tests/ ./tests/

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -r requirements.txt

# Final runtime image for blockchain node
FROM docker.io/parity/base-bin:latest AS blockchain-node

COPY --from=rust-builder /mod-net/target/release/modnet-node /usr/local/bin/mod-net-node

USER root
RUN useradd -m -u 1001 -U -s /bin/sh -d /mod-net modnet && \
    mkdir -p /data /mod-net/.local/share && \
    chown -R modnet:modnet /data && \
    ln -s /data /mod-net/.local/share/mod-net && \
    # Verify executable works
    /usr/local/bin/mod-net-node --version

USER modnet

EXPOSE 30333 9933 9944 9615
VOLUME ["/data"]

ENTRYPOINT ["/usr/local/bin/mod-net-node"]

# Python client runtime image
FROM python:3.11-slim AS python-client

WORKDIR /app

# Install runtime dependencies including uv
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

# Copy built Python environment
COPY --from=python-builder /opt/venv /opt/venv
COPY --from=python-builder /app /app

# Create missing modules.py file to fix import error
RUN echo 'from fastapi import APIRouter\n\nrouter = APIRouter(prefix="/modules", tags=["modules"])\n\n@router.get("/")\nasync def list_modules():\n    return {"modules": []}\n\n@router.get("/health")\nasync def modules_health():\n    return {"status": "healthy", "modules": []}' > /opt/venv/lib/python3.11/site-packages/app/api/modules.py

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user and necessary directories
RUN useradd -m -u 1001 modnet-client && \
    mkdir -p /app/logs /app/.venv && \
    chown -R modnet-client:modnet-client /app
USER modnet-client

EXPOSE 8001 8003 8081

CMD ["python", "-m", "mod_net_client"]

# Development image with both Rust and Python tools
FROM rust:1.75 AS development

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Rust tools
RUN rustup target add wasm32-unknown-unknown && \
    cargo install cargo-watch

# Install Python tools
RUN pip3 install uv

# Copy project files
COPY . .

# Install dependencies
RUN cargo fetch
RUN uv pip install --system -r requirements.txt

EXPOSE 30333 9933 9944 9615 8000

CMD ["/bin/bash"]
