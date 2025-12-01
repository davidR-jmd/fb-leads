#!/bin/bash
set -e

VPS_HOST="root@72.62.52.211"
REMOTE_DIR="/app/fb-leads"

echo "==> Deploying to Hetzner VPS..."

# 1. Ensure Docker is installed on VPS
echo "==> Checking Docker on VPS..."
ssh $VPS_HOST "command -v docker || curl -fsSL https://get.docker.com | sh"

# 2. Create directory on VPS
ssh $VPS_HOST "mkdir -p $REMOTE_DIR"

# 3. Copy files to VPS
echo "==> Copying files..."
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '.git' \
  --exclude '*.pyc' \
  /home/david/perso/fb-leads/ $VPS_HOST:$REMOTE_DIR/

# 4. Build and start on VPS
echo "==> Starting containers..."
ssh $VPS_HOST "cd $REMOTE_DIR && docker compose down 2>/dev/null || true && docker compose up -d --build"

echo "==> Done! App running at:"
echo "    Frontend: http://72.62.52.211:3000"
echo "    Backend:  http://72.62.52.211:8000"
