# Meshtastic Protobuf Parser for Python

## Local installation

```bash
# Clone Repo
git clone <link to repo>
cd mqtt-protobuf-to-json

# Setup environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configuration
cp config-example.json config.json
nano config.json

# Run service
python main.py
```

## Hosting with Docker

You can also host this service in your homelab with the steps below.

```bash
# Clone Repo
git clone <link to repo>
cd mqtt-protobuf-to-json

# Configuration
cp config-example.json config.json
nano config.json

# Deploy service
docker-compose up -d
```