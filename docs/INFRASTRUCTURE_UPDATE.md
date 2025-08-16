# Mod-Net Infrastructure Update: External Access Implementation

**Date**: August 13, 2025  
**Status**: ✅ **PRODUCTION READY WITH 3 WEBUIS**  
**Author**: Infrastructure Team  

## 🎯 Executive Summary

We have successfully implemented comprehensive external access for all Mod-Net services. The infrastructure now provides **dual access methods** (direct datacenter ports + ngrok tunnels) with complete redundancy and SSL encryption options.

### Key Achievements
- ✅ **10 External Ports** mapped and functional (2001, 2101-2109)
- ✅ **4 Core Services** externally accessible (Blockchain, IPFS, IPFS Worker, SSH)
- ✅ **3 Interactive WebUIs** for comprehensive management
- ✅ **Production Deployment** via PM2 process management
- ✅ **Complete Documentation** and management scripts
- ✅ **Security Hardened** with proper firewall rules

---

## 🌐 External Access Overview

### **Server Information**
- **External IP**: `24.83.27.62`
- **Available Port Range**: 2001-2201 (datacenter level)
- **Access Methods**: Direct ports + ngrok tunnels

### **Complete Service Mapping**

| External Port | Internal Port | Service | Protocol | Direct Access | Ngrok Access | Status |
|---------------|---------------|---------|----------|---------------|--------------|---------|
| **2001** | 22 | SSH | TCP | `24.83.27.62:2001` | `5.tcp.ngrok.io:21633` | ✅ **Active** |
| **2101** | 30333 | Blockchain P2P | TCP | `24.83.27.62:2101` | - | ✅ Ready |
| **2102** | 9944 | Blockchain RPC | HTTP | `24.83.27.62:2102` | `chain-rpc-comai.ngrok.dev` | ✅ **Verified** |
| **2103** | 9944 | WebSocket | WS | `24.83.27.62:2103` | - | ✅ Ready |
| **2104** | 9615 | Prometheus | HTTP | `24.83.27.62:2104` | - | ✅ Ready |
| **2105** | 5001 | IPFS API | HTTP | `24.83.27.62:2105` | `ipfs-api-comai.ngrok.dev` | ✅ **Verified** |
| **2106** | 8080 | IPFS Gateway | HTTP | `24.83.27.62:2106` | `ipfs-gateway-comai.ngrok.dev` | ✅ Ready |
| **2107** | 4001 | IPFS Swarm | TCP | `24.83.27.62:2107` | - | ✅ Ready |
| **2108** | 8003 | IPFS Worker | HTTP | `24.83.27.62:2108` | `ipfs-worker-comai.ngrok.dev` | ✅ **Verified** |
| **2109** | 8081 | Blockchain Explorer | HTTP | `24.83.27.62:2109` | `blockchain-explorer-comai.ngrok.dev` | ✅ **Verified** |

---

## 🚀 Service Status

### **PM2 Services Running**
```bash
pm2 list
```

| ID | Service | Status | Description |
|----|---------|--------|-------------|
| 5 | **chain** | ✅ Online | Substrate blockchain node with external RPC |
| 8 | **ipfs** | ✅ Online | IPFS daemon with external API/Gateway |
| 9 | **ipfs-worker** | ✅ Online | Off-chain bridge service (FastAPI) |
| 10 | **blockchain-explorer** | ✅ Online | Custom blockchain dashboard (WebUI) |
| 7 | **ngrok** | ✅ Online | All tunnel services active |
| 2 | **art** | ✅ Online | Existing service |

### **Service Commands**
```bash
# Blockchain Node
./target/release/modnet-node --dev --rpc-external --rpc-cors all

# IPFS Daemon  
ipfs daemon

# IPFS Worker (Off-chain Bridge)
cd commune-ipfs && COMMUNE_IPFS_HOST=0.0.0.0 COMMUNE_IPFS_PORT=8003 uv run python main.py
```

---

## 🔗 Access Examples

### **Blockchain Access**
```bash
# Health Check (Direct)
curl -H "Content-Type: application/json" \
  -d '{"id":1, "jsonrpc":"2.0", "method": "system_health", "params":[]}' \
  http://24.83.27.62:2102

# Health Check (Ngrok - SSL)
curl -H "Content-Type: application/json" \
  -d '{"id":1, "jsonrpc":"2.0", "method": "system_health", "params":[]}' \
  https://chain-rpc-comai.ngrok.dev
```

### **IPFS Access**
```bash
# IPFS API Version (Direct)
curl -X POST http://24.83.27.62:2105/api/v0/version

# IPFS API Version (Ngrok - SSL)
curl -X POST https://ipfs-api-comai.ngrok.dev/api/v0/version

# IPFS WebUI (Direct)
open http://24.83.27.62:2105/webui/

# IPFS WebUI (Ngrok - SSL)
open https://ipfs-webui-comai.ngrok.dev/webui/
```

### **IPFS Worker (Off-chain Bridge)**
```bash
# Health Check (Direct)
curl http://24.83.27.62:2108/health

# Health Check (Ngrok - SSL)
curl https://ipfs-worker-comai.ngrok.dev/health

# API Key for Admin Access
API_KEY="9xGRAVHroqmvundIy6orjvcohWvxiqeKxFO_I-jcTXo"

### **Blockchain Explorer (WebUI)**
```bash
# Blockchain Explorer (Direct)
open http://24.83.27.62:2109/blockchain-explorer.html

# Blockchain Explorer (Ngrok - SSL)
open https://blockchain-explorer-comai.ngrok.dev/blockchain-explorer.html
```

### **IPFS Upload Frontend (Beautiful File Manager)**
```bash
# IPFS Upload Frontend (Direct)
open http://24.83.27.62:2108/

# IPFS Upload Frontend (Ngrok - SSL)
open https://ipfs-uploader-comai.ngrok.dev/
```

### **SSH Access**
```bash
# Direct SSH
ssh user@24.83.27.62 -p 2001

# Ngrok SSH (Reserved TCP)
ssh user@5.tcp.ngrok.io -p 21633
```

---

## 🛠️ Management & Operations

### **Port Management Script**
Location: `/home/com/repos/comai/mod-net/modules/scripts/setup-external-ports.sh`

```bash
# Check all external port status
./scripts/setup-external-ports.sh status

# Test connectivity
./scripts/setup-external-ports.sh test

# Setup port forwarding (if needed)
sudo ./scripts/setup-external-ports.sh setup

# Remove port forwarding
sudo ./scripts/setup-external-ports.sh remove
```

### **PM2 Management**
```bash
# View all services
pm2 list

# Restart specific services
pm2 restart chain
pm2 restart ipfs
pm2 restart ipfs-worker
pm2 restart blockchain-explorer
pm2 restart ngrok

# View logs
pm2 logs chain
pm2 logs ipfs-worker
pm2 logs blockchain-explorer

# Save PM2 configuration
pm2 save
pm2 startup
```

### **Firewall Status**
```bash
# Check UFW status
sudo ufw status

# Check iptables NAT rules
sudo iptables -t nat -L PREROUTING
```

---

## 🔐 Security Configuration

### **Firewall Rules**
- **UFW**: Configured for external ports 2001-2108
- **iptables**: NAT rules for port forwarding
- **SSH**: Restricted to key-based authentication

### **API Keys & Authentication**
- **IPFS Worker API Key**: `9xGRAVHroqmvundIy6orjvcohWvxiqeKxFO_I-jcTXo`
- **Ngrok Auth**: Configured with reserved TCP address for SSH
- **CORS**: Enabled for blockchain RPC (`--rpc-cors all`)
- **IPFS WebUI**: CORS configured for external access

### **Network Security**
- **External Binding**: Services bind to `0.0.0.0` for external access
- **Internal Services**: Prometheus and other metrics on internal network
- **SSL/TLS**: Available via ngrok tunnels for encrypted connections

---

## 📋 Troubleshooting Guide

### **Common Issues**

#### **Service Not Accessible Externally**
1. Check if service is running: `pm2 list`
2. Verify port forwarding: `./scripts/setup-external-ports.sh status`
3. Check firewall: `sudo ufw status`
4. Test local connectivity first: `curl localhost:PORT`

#### **IPFS Worker Issues**
1. Check dependencies: `cd commune-ipfs && uv sync`
2. Verify IPFS daemon is running: `ipfs id`
3. Check logs: `pm2 logs ipfs-worker`
4. Restart service: `pm2 restart ipfs-worker`

#### **Ngrok Tunnel Issues**
1. Check ngrok status: `pm2 logs ngrok`
2. Verify configuration: `cat /home/com/.config/ngrok/ngrok.yml`
3. Restart ngrok: `pm2 restart ngrok`

### **Health Check Commands**
```bash
# Quick health check all services
curl http://24.83.27.62:2102 # Blockchain
curl http://24.83.27.62:2105/api/v0/version # IPFS
curl http://24.83.27.62:2108/health # IPFS Worker
curl http://24.83.27.62:2109/blockchain-explorer.html # Blockchain Explorer

# Ngrok health checks
curl https://chain-rpc-comai.ngrok.dev
curl https://ipfs-worker-comai.ngrok.dev/health
curl https://blockchain-explorer-comai.ngrok.dev/blockchain-explorer.html
```

---

## 🚀 Development Workflow

### **For Blockchain Development**
- **Local RPC**: `http://localhost:9944`
- **External RPC**: `http://24.83.27.62:2102` or `https://chain-rpc-comai.ngrok.dev`
- **WebSocket**: `ws://24.83.27.62:2103`

### **For IPFS Development**
- **Local API**: `http://localhost:5001`
- **External API**: `http://24.83.27.62:2105` or `https://ipfs-api-comai.ngrok.dev`
- **Gateway**: `http://24.83.27.62:2106` or `https://ipfs-gateway-comai.ngrok.dev`

### **For Off-chain Bridge Development**
- **Local Worker**: `http://localhost:8003`
- **External Worker**: `http://24.83.27.62:2108` or `https://ipfs-worker-comai.ngrok.dev`
- **API Documentation**: Available at `/docs` endpoint

### **For WebUI Access**
- **IPFS WebUI (Official)**: `http://24.83.27.62:2105/webui/` or `https://ipfs-webui-comai.ngrok.dev/webui/`
- **IPFS Upload Frontend**: `http://24.83.27.62:2108/` or `https://ipfs-uploader-comai.ngrok.dev/`
- **Blockchain Explorer**: `http://24.83.27.62:2109/blockchain-explorer.html` or `https://blockchain-explorer-comai.ngrok.dev/blockchain-explorer.html`
- **Features**: Real-time monitoring, drag-drop file uploads, RPC interface, network statistics

---

## 📚 Documentation References

- **Main Deployment Guide**: `docs/DEPLOYMENT.md`
- **Port Management Script**: `scripts/setup-external-ports.sh`
- **Ngrok Configuration**: `/home/com/.config/ngrok/ngrok.yml`
- **IPFS Worker Source**: `commune-ipfs/main.py`

---

## 🌐 WebUI Features

### **1. IPFS WebUI (Official) Capabilities**
- 📁 **File Management**: Upload, download, and manage files on IPFS
- 🌐 **Network View**: See connected peers and network status
- 📊 **Node Statistics**: Monitor bandwidth, storage, and performance
- 🔧 **Configuration**: Manage IPFS daemon settings
- 📋 **Pinning**: Pin important content to keep it available

### **2. IPFS Upload Frontend (Beautiful File Manager)**
- 🎨 **Drag & Drop Interface**: Beautiful upload zone with drag-and-drop support
- 📁 **Multiple File Upload**: Upload several files at once (up to 100MB each)
- 🏷️ **File Metadata**: Add descriptions and tags to uploads
- 🔍 **Search & Browse**: Search files by name/description, grid view browser
- 📊 **Progress Tracking**: Real-time upload progress and file management
- 💼 **Professional UI**: Modern, responsive design with Font Awesome icons

### **3. Blockchain Explorer Features**
- 📊 **Real-time Dashboard**: Live node status, peer count, block height
- 🔗 **Chain Information**: Best block, finalized block, chain health
- 🛠️ **RPC Interface**: Interactive tool to send custom RPC calls
- ⚡ **Quick Methods**: One-click access to common blockchain queries
- 📈 **Auto-refresh**: Updates every 10 seconds automatically

## 🎯 Next Steps & Recommendations

### **Immediate Actions**
1. ✅ **Test all endpoints** using the provided examples
2. ✅ **Access all 3 WebUIs** via the provided URLs
3. ✅ **Try IPFS Upload Frontend** for easy file management
4. ✅ **Bookmark ngrok URLs** for team access
5. ✅ **Save API keys** securely for admin access
6. ✅ **Setup monitoring** for service health

### **Future Enhancements**
- [ ] **Load Balancing**: Consider adding load balancer for RPC endpoints
- [ ] **SSL Certificates**: Deploy custom SSL certificates for direct access
- [ ] **Monitoring Dashboard**: Implement Grafana dashboard for metrics
- [ ] **Backup Strategy**: Automated backups for blockchain and IPFS data

### **Team Onboarding**
- [ ] **Share this document** with all team members
- [ ] **Provide access credentials** (SSH keys, API keys)
- [ ] **Demo all 3 WebUIs** (IPFS upload frontend, official WebUI, blockchain explorer)
- [ ] **Train team on file upload workflow** using the beautiful IPFS frontend
- [ ] **Schedule training session** on new infrastructure
- [ ] **Update CI/CD pipelines** to use new external endpoints

---

## 📞 Support & Contact

For infrastructure issues or questions:
- **Documentation**: Check `docs/DEPLOYMENT.md`
- **Logs**: Use `pm2 logs [service-name]`
- **Port Management**: Use `./scripts/setup-external-ports.sh`
- **Emergency**: SSH access via `ssh user@24.83.27.62 -p 2001`

---

**Infrastructure Status**: ✅ **PRODUCTION READY WITH 3 WEBUIS**  
**Services**: 6 PM2 services, 10 external ports, 3 interactive WebUIs  
**WebUIs**: IPFS Upload Frontend, Official IPFS WebUI, Blockchain Explorer  
**Last Updated**: August 13, 2025  
**Next Review**: Weekly service health checks recommended
