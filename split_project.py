#!/usr/bin/env python3
"""
프로젝트 분리 도구
Full 버전과 Part 버전으로 프로젝트 분할
"""

import os
import shutil
import json
from pathlib import Path

# 버전별 구성
PROJECT_STRUCTURE = {
    "full": {
        "name": "reflex-cps-full",
        "description": "Enterprise CPS Full Version",
        "features": ["dashboard", "ai", "ml", "dagster", "monitoring", "analytics"],
        "excluded_files": [],
        "requirements": [
            "reflex>=0.8.6",
            "psycopg[binary,pool]>=3.1",
            "openai>=1.0.0",
            "dagster>=1.0.0",
            "scikit-learn>=1.0.0",
            "pandas>=2.0.0",
            "plotly>=5.0.0",
            "prometheus-client>=0.16.0"
        ]
    },
    "part": {
        "name": "reflex-ksys-lite",
        "description": "Lightweight KSYS Version for Raspberry Pi",
        "features": ["dashboard", "monitoring", "basic_analytics"],
        "excluded_files": [
            "ksys_app/ai_engine/",
            "ksys_app/ml/",
            "dagster/",
            "ksys_app/components/ai_*.py"
        ],
        "requirements": [
            "reflex>=0.8.6",
            "psycopg[binary,pool]>=3.1",
            "cachetools>=5.0.0",
            "plotly>=5.0.0"
        ]
    }
}

def create_version_config(version_type):
    """버전별 설정 파일 생성"""
    config = PROJECT_STRUCTURE[version_type]
    
    return {
        "version": version_type,
        "name": config["name"],
        "description": config["description"],
        "features": config["features"],
        "resource_limits": {
            "memory": "2Gi" if version_type == "full" else "512Mi",
            "cpu": "2" if version_type == "full" else "0.5"
        },
        "database": {
            "pool_size": 20 if version_type == "full" else 5,
            "cache_ttl": 60 if version_type == "full" else 30
        }
    }

def create_feature_flags():
    """Feature flags 시스템 생성"""
    return """
import os
from typing import Set

class FeatureFlags:
    def __init__(self):
        self.version = os.getenv("APP_VERSION", "full")
        self.enabled_features = self._get_enabled_features()
    
    def _get_enabled_features(self) -> Set[str]:
        if self.version == "full":
            return {
                "dashboard", "ai", "ml", "dagster", 
                "monitoring", "analytics", "realtime"
            }
        elif self.version == "part":
            return {
                "dashboard", "monitoring", "basic_analytics"
            }
        else:
            return set()
    
    def is_enabled(self, feature: str) -> bool:
        return feature in self.enabled_features
    
    def get_menu_items(self):
        if self.version == "full":
            return [
                ("Dashboard", "/"),
                ("Trend", "/trend"),
                ("Tech", "/tech"),
                ("AI Insights", "/ai"),
                ("ML Analysis", "/ml"),
                ("Dagster", "/dagster"),
                ("Monitoring", "/monitoring")
            ]
        else:
            return [
                ("Dashboard", "/"),
                ("Trend", "/trend"),
                ("Monitoring", "/monitoring")
            ]

feature_flags = FeatureFlags()
"""

def split_requirements(base_path):
    """requirements.txt 분리"""
    full_reqs = PROJECT_STRUCTURE["full"]["requirements"]
    part_reqs = PROJECT_STRUCTURE["part"]["requirements"]
    
    # Full 버전 requirements
    with open(base_path / "requirements-full.txt", "w") as f:
        f.write("# Full Version Requirements\n")
        for req in full_reqs:
            f.write(f"{req}\n")
    
    # Part 버전 requirements
    with open(base_path / "requirements-part.txt", "w") as f:
        f.write("# Part Version Requirements (Lightweight)\n")
        for req in part_reqs:
            f.write(f"{req}\n")
    
    print("[OK] Requirements files created")

def create_docker_files(base_path):
    """Docker 파일 생성"""
    
    # Full 버전 Dockerfile
    dockerfile_full = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc g++ make libpq-dev curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-full.txt .
RUN pip install --no-cache-dir -r requirements-full.txt

# Copy application
COPY . .

# Set environment
ENV APP_VERSION=full
ENV TZ=Asia/Seoul

EXPOSE 13000 13001

CMD ["reflex", "run", "--env", "prod", "--backend-host", "0.0.0.0"]
"""
    
    # Part 버전 Dockerfile (ARM 지원)
    dockerfile_part = """FROM python:3.11-slim

WORKDIR /app

# Install minimal dependencies
RUN apt-get update && apt-get install -y \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-part.txt .
RUN pip install --no-cache-dir -r requirements-part.txt

# Copy application (excluding AI/ML components)
COPY --exclude=ksys_app/ai_engine \\
     --exclude=ksys_app/ml \\
     --exclude=dagster \\
     . .

# Set environment
ENV APP_VERSION=part
ENV TZ=Asia/Seoul

# Optimize for Raspberry Pi
ENV PYTHONUNBUFFERED=1
ENV REFLEX_TELEMETRY_ENABLED=false

EXPOSE 13000 13001

CMD ["reflex", "run", "--env", "prod", "--backend-host", "0.0.0.0"]
"""
    
    with open(base_path / "Dockerfile.full", "w") as f:
        f.write(dockerfile_full)
    
    with open(base_path / "Dockerfile.part", "w") as f:
        f.write(dockerfile_part)
    
    print("[OK] Docker files created")

def create_deployment_scripts(base_path):
    """배포 스크립트 생성"""
    
    # Full 버전 배포 (K3s)
    deploy_full = """#!/bin/bash
echo "[DEPLOY] Full Version to K3s"

# Build image
docker build -f Dockerfile.full -t reflex-cps-full:latest .

# Tag for registry
docker tag reflex-cps-full:latest registry.local/reflex-cps-full:latest

# Push to registry
docker push registry.local/reflex-cps-full:latest

# Apply K3s manifests
kubectl apply -f k8s/full/

echo "[OK] Full version deployed"
"""
    
    # Part 버전 배포 (Docker)
    deploy_part = """#!/bin/bash
echo "[DEPLOY] Part Version to Raspberry Pi"

# Build ARM64 image
docker buildx build --platform linux/arm64 \\
    -f Dockerfile.part \\
    -t reflex-ksys-lite:latest \\
    --push .

# Deploy to Pi
ssh pi@raspberrypi << EOF
docker pull reflex-ksys-lite:latest
docker stop ksys-lite || true
docker rm ksys-lite || true
docker run -d --name ksys-lite \\
    -p 13000:13000 \\
    -e APP_VERSION=part \\
    -e DB_HOST=localhost \\
    --restart unless-stopped \\
    reflex-ksys-lite:latest
EOF

echo "[OK] Part version deployed to Raspberry Pi"
"""
    
    os.makedirs(base_path / "deploy", exist_ok=True)
    
    with open(base_path / "deploy" / "deploy-full.sh", "w") as f:
        f.write(deploy_full)
    
    with open(base_path / "deploy" / "deploy-part.sh", "w") as f:
        f.write(deploy_part)
    
    print("[OK] Deployment scripts created")

def main():
    base_path = Path(".")
    
    print("[PROJECT SPLITTER]")
    print("This will create structure for Full/Part versions")
    print()
    
    # Create feature flags
    with open(base_path / "ksys_app" / "feature_flags.py", "w") as f:
        f.write(create_feature_flags())
    print("[OK] Feature flags system created")
    
    # Split requirements
    split_requirements(base_path)
    
    # Create Docker files
    create_docker_files(base_path)
    
    # Create deployment scripts
    create_deployment_scripts(base_path)
    
    # Create version configs
    for version in ["full", "part"]:
        config = create_version_config(version)
        with open(base_path / f"config-{version}.json", "w") as f:
            json.dump(config, f, indent=2)
    print("[OK] Version configs created")
    
    print("\n[NEXT STEPS]")
    print("1. Test with: APP_VERSION=part reflex run")
    print("2. Build Part version: docker build -f Dockerfile.part -t ksys-lite .")
    print("3. Build Full version: docker build -f Dockerfile.full -t cps-full .")
    print("4. Deploy using scripts in deploy/ directory")
    print("\n[NETWORK MONITORING]")
    print("Run: python network_monitor.py")

if __name__ == "__main__":
    main()