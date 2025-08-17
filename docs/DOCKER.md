# Docker Setup for Mod-Net

This document provides comprehensive instructions for running the Mod-Net ecosystem using Docker.

## Overview

The Mod-Net Docker setup includes:
- **Blockchain Node**: Substrate-based blockchain with module registry
- **Python Client**: API server for module management and IPFS integration
- **IPFS Node**: Distributed storage for module artifacts
- **Blockchain Explorer**: Web UI for blockchain interaction
- **Development Environment**: Full development stack with hot-reload

## Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ available RAM
- 10GB+ available disk space

### Production Deployment

1. **Clone and configure environment**:
```bash
git clone <repository-url>
cd mod-net/modules
cp .env.example .env
# Edit .env with your configuration
```

2. **Start the full stack**:
```bash
docker-compose up -d
```

3. **Verify services**:
```bash
docker-compose ps
docker-compose logs -f mod-net-node
```

### Development Setup

1. **Start development environment**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

2. **Access development container**:
```bash
docker-compose exec dev-environment bash
```

3. **Run with file watching**:
```bash
docker-compose --profile development up -d
```

## Service Architecture

### Blockchain Node (`mod-net-node`)
- **Image**: Multi-stage build from `paritytech/ci-unified`
- **Ports**: 30333 (P2P), 9933 (RPC), 9944 (WebSocket), 9615 (Metrics)
- **Data**: Persistent volume at `/data`
- **Configuration**: Environment variables and command-line flags

### Python Client (`mod-net-client`)
- **Image**: Multi-stage build from `python:3.11-slim`
- **Port**: 8000 (API server)
- **Dependencies**: FastAPI, substrate-interface, commune-ipfs
- **Environment**: Configurable via environment variables

### IPFS Node (`ipfs`)
- **Image**: `ipfs/kubo:latest`
- **Ports**: 5001 (API), 8080 (Gateway), 4001 (Swarm)
- **Configuration**: CORS enabled for web access
- **Storage**: Persistent volumes for data and staging

### Blockchain Explorer (`blockchain-explorer`)
- **Image**: `nginx:alpine`
- **Port**: 8081
- **Content**: Static web UI with API proxying
- **Configuration**: Custom nginx.conf with upstream proxying

## Build Targets

The Dockerfile provides multiple build targets:

### `blockchain-node` (Production)
Optimized runtime image containing only the compiled blockchain node.

### `python-client` (Production)
Minimal Python runtime with the mod-net client library and dependencies.

### `development` (Development)
Full development environment with Rust and Python toolchains, source code mounting, and development tools.

## Environment Configuration

Key environment variables in `.env`:

```bash
# External networking
EXTERNAL_IP=your.external.ip
EXTERNAL_CHAIN_RPC_PORT=9933
EXTERNAL_IPFS_API_PORT=5001

# Service configuration
BLOCKCHAIN_RPC_PORT=9944
IPFS_API_PORT=5001
IPFS_WORKER_API_KEY=your-secure-key

# Development mode
NODE_ENV=development
DEBUG=false
```

## Development Workflows

### Rust Development
```bash
# Build and test Rust code
docker-compose exec dev-environment cargo build
docker-compose exec dev-environment cargo test

# Watch for changes
docker-compose --profile development up rust-watcher
```

### Python Development
```bash
# Run Python tests
docker-compose --profile testing up python-tests

# Interactive Python shell
docker-compose exec mod-net-client python
```

### Integration Testing
```bash
# Run full test suite
docker-compose -f docker-compose.yml -f docker-compose.dev.yml run --rm python-tests
```

## Data Persistence

Persistent volumes:
- `blockchain_data`: Blockchain state and configuration
- `ipfs_data`: IPFS repository data
- `ipfs_staging`: IPFS staging area for imports
- `dev_cargo_cache`: Rust dependency cache (development)
- `dev_target_cache`: Rust build cache (development)

## Networking

Services communicate via the `mod-net` bridge network (172.20.0.0/16):
- Internal DNS resolution between services
- Isolated from host network by default
- Port mapping for external access

## Monitoring and Logs

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mod-net-node

# Follow new logs only
docker-compose logs -f --tail=0
```

### Health checks
```bash
# Service status
docker-compose ps

# Resource usage
docker stats
```

### Prometheus metrics
Blockchain node exposes metrics on port 9615:
```bash
curl http://localhost:9615/metrics
```

## Troubleshooting

### Common Issues

**Build failures**:
```bash
# Clean build cache
docker-compose build --no-cache

# Check build logs
docker-compose build mod-net-node 2>&1 | tee build.log
```

**Network connectivity**:
```bash
# Test internal connectivity
docker-compose exec mod-net-client curl http://mod-net-node:9933

# Check network configuration
docker network inspect modules_mod-net
```

**Storage issues**:
```bash
# Check volume usage
docker volume ls
docker system df

# Clean unused volumes
docker volume prune
```

### Performance Tuning

**Resource limits** (add to docker-compose.yml):
```yaml
services:
  mod-net-node:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

**Build optimization**:
- Use BuildKit: `DOCKER_BUILDKIT=1 docker-compose build`
- Multi-stage caching: Builds reuse intermediate layers
- Dependency caching: Separate dependency and source layers

## Security Considerations

- Non-root users in all runtime containers
- Minimal attack surface in production images
- Network isolation via Docker networks
- Secret management via environment variables
- Regular base image updates recommended

## Production Deployment

### Resource Requirements
- **Minimum**: 2 CPU cores, 4GB RAM, 20GB storage
- **Recommended**: 4 CPU cores, 8GB RAM, 100GB SSD storage

### Scaling
```bash
# Scale Python client instances
docker-compose up -d --scale mod-net-client=3

# Load balancer configuration required for multiple instances
```

### Backup Strategy
```bash
# Backup blockchain data
docker run --rm -v modules_blockchain_data:/data -v $(pwd):/backup alpine tar czf /backup/blockchain-backup.tar.gz /data

# Backup IPFS data
docker run --rm -v modules_ipfs_data:/data -v $(pwd):/backup alpine tar czf /backup/ipfs-backup.tar.gz /data
```

## Contributing

When modifying Docker configuration:
1. Test changes in development environment first
2. Update documentation for any new environment variables
3. Verify multi-stage builds work correctly
4. Test both development and production configurations
5. Update resource requirements if needed

For more information, see the main project [README.md](../README.md) and [CONTRIBUTING.md](../CONTRIBUTING.md).
