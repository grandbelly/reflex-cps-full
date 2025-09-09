#!/bin/bash
# Build script for Raspberry Pi deployment

echo "🚀 Building ultra-lightweight Docker image for Raspberry Pi..."

# Stop any running containers
docker-compose -f docker-compose.rpi.yml down 2>/dev/null

# Clean up old images
docker system prune -f

# Build the Alpine-based image
echo "📦 Building Alpine Linux image..."
docker build -f Dockerfile.alpine -t reflex-ksys-rpi:latest .

# Check image size
echo "📊 Image size:"
docker images reflex-ksys-rpi:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Optional: Save image for transfer to Raspberry Pi
read -p "Do you want to save the image for transfer? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "💾 Saving image to reflex-ksys-rpi.tar.gz..."
    docker save reflex-ksys-rpi:latest | gzip > reflex-ksys-rpi.tar.gz
    echo "✅ Image saved! Transfer to Raspberry Pi using:"
    echo "   scp reflex-ksys-rpi.tar.gz pi@raspberrypi:/home/pi/"
    echo ""
    echo "Then load on Raspberry Pi with:"
    echo "   gunzip -c reflex-ksys-rpi.tar.gz | docker load"
fi

echo "✨ Build complete!"