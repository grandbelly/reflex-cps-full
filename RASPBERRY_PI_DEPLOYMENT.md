# Raspberry Pi Deployment Guide

## 🚀 Ultra-Lightweight Docker Deployment

### Overview
This guide provides instructions for deploying the KSYS Reflex application on Raspberry Pi with minimal resource usage.

### Image Size Comparison
- **Original Image**: ~15.6 GB (with all AI/ML libraries)
- **Optimized Alpine Image**: **1.46 GB** (with bash for Reflex init) - **90.6% reduction!**
- **Startup Time**: < 30 seconds on Raspberry Pi 4

### Prerequisites
- Raspberry Pi 4 (minimum 2GB RAM recommended)
- Docker installed on Raspberry Pi
- Network connection to TimescaleDB server

## 📦 Building the Image

### Option 1: Build on Development Machine
```bash
# Build the Alpine-based lightweight image
docker build -f Dockerfile.alpine -t reflex-ksys-rpi:latest .

# Save the image for transfer
docker save reflex-ksys-rpi:latest | gzip > reflex-ksys-rpi.tar.gz

# Transfer to Raspberry Pi
scp reflex-ksys-rpi.tar.gz pi@raspberrypi:/home/pi/
```

### Option 2: Build Directly on Raspberry Pi
```bash
# Clone repository
git clone https://github.com/grandbelly/reflex-ksys-refactor.git
cd reflex-ksys-refactor

# Build using Raspberry Pi compose file
docker-compose -f docker-compose.rpi.yml build
```

## 🏃 Running the Application

### Load and Run Docker Image
```bash
# If transferred from another machine
gunzip -c reflex-ksys-rpi.tar.gz | docker load

# Run with docker-compose
docker-compose -f docker-compose.rpi.yml up -d

# Or run directly
docker run -d \
  --name reflex-ksys \
  -p 13000:13000 \
  -p 13001:13001 \
  -e TS_DSN='postgresql://user:pass@db-server:5432/EcoAnP?sslmode=disable' \
  -e ENABLE_AI=false \
  --restart unless-stopped \
  reflex-ksys-rpi:latest
```

## ⚙️ Configuration

### Environment Variables
```bash
# Database (required)
TS_DSN=postgresql://user:pass@host:5432/EcoAnP?sslmode=disable

# Performance
APP_ENV=production
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1

# AI Features (set to true only if needed)
ENABLE_AI=false

# Reflex Optimization
REFLEX_TELEMETRY_ENABLED=false
REFLEX_PROD_MODE=true
```

### Resource Limits
The docker-compose.rpi.yml file includes resource limits:
- CPU: Maximum 2 cores, minimum 0.5 cores
- Memory: Maximum 1GB, minimum 256MB

## 🔧 Performance Optimization

### 1. Disable Unnecessary Features
- AI/ML features disabled by default (ENABLE_AI=false)
- Telemetry disabled
- Production mode enabled

### 2. Use Minimal Dependencies
- Uses `requirements-minimal.txt` instead of full requirements
- No heavy ML libraries (torch, transformers, etc.)
- Alpine Linux base for smaller footprint

### 3. Caching Strategy
- Pre-initialized Reflex in Docker image
- Read-only volume mounts for application code
- Optimized startup command

### 4. Database Optimization
- Connection pooling enabled
- Query result caching (TTL: 30-60s)
- Adaptive resolution for time-series data

## 📊 Monitoring

### Check Container Status
```bash
docker ps
docker logs reflex-ksys
```

### Monitor Resource Usage
```bash
docker stats reflex-ksys
```

### Health Check
```bash
curl http://localhost:13000
```

## 🐛 Troubleshooting

### High Memory Usage
1. Check if AI features are accidentally enabled
2. Reduce cache sizes in application
3. Restart container: `docker restart reflex-ksys`

### Slow Startup
1. Ensure Reflex is pre-initialized in image
2. Check network connectivity to database
3. Review container logs for errors

### Database Connection Issues
1. Verify TS_DSN environment variable
2. Check network connectivity
3. Ensure PostgreSQL allows connections from Raspberry Pi

## 🔄 Updates

### Quick Update (Code Only)
```bash
# Pull latest code
git pull

# Restart container (volumes will pick up changes)
docker-compose -f docker-compose.rpi.yml restart
```

### Full Update (Rebuild Image)
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose -f docker-compose.rpi.yml up -d --build
```

## 📈 Performance Metrics

### Expected Performance (Raspberry Pi 4)
- **Docker Image Size**: 1.46 GB (90.6% smaller than original)
- **Startup Time**: 20-30 seconds
- **Memory Usage**: 200-400 MB (without AI)
- **CPU Usage**: 10-30% (idle), 50-70% (active)
- **Response Time**: < 500ms for dashboard
- **Query Performance**: 
  - 24h data: < 300ms
  - 30d data: < 1s (with adaptive resolution)

## 🎯 Best Practices

1. **Regular Maintenance**
   - Clean Docker system weekly: `docker system prune -f`
   - Monitor disk space: `df -h`
   - Check logs regularly: `docker logs --tail 100 reflex-ksys`

2. **Backup Strategy**
   - No persistent data stored in container
   - All data in TimescaleDB (backup separately)

3. **Security**
   - Run container as non-root user
   - Use read-only mounts where possible
   - Keep base image updated

## 📝 Notes

- AI features can be enabled by setting `ENABLE_AI=true`, but this will significantly increase memory usage and startup time
- For production deployment, consider using a reverse proxy (nginx) for SSL termination
- Monitor Raspberry Pi temperature: `vcgencmd measure_temp`

## 🆘 Support

For issues specific to Raspberry Pi deployment:
1. Check container logs
2. Verify resource availability
3. Review this guide
4. Open issue on GitHub with "rpi-deployment" tag