#!/usr/bin/env bash
# bootstrap-server.sh — one-time deploy server setup for blue/green Waybill pipeline
#
# Run this once on a fresh Ubuntu 22.04 / 24.04 server as root (or with sudo).
# Sets up the deploy user, restricted sudoers, nginx, Docker, and the slot file.
#
# Usage: sudo bash scripts/bootstrap-server.sh
#
# After running:
#   1. Copy the printed SSH public key to your GitHub secret SSH_PRIVATE_KEY
#      (private key) and to /home/deploy/.ssh/authorized_keys (public key)
#   2. Update your GitHub secret SERVER_IP with this server's IP
#   3. Run the pipeline — it will SSH as deploy@ and use the permissions set here

set -euo pipefail

# ── Require root ──────────────────────────────────────────────────────────────
if [ "$(id -u)" -ne 0 ]; then
  echo "❌ Run as root: sudo bash $0"
  exit 1
fi

echo "=== Waybill deploy server bootstrap ==="
echo ""

# ── 1. System packages ────────────────────────────────────────────────────────
echo "[1/8] Installing system packages..."
apt-get update -qq
apt-get install -y -qq nginx curl ca-certificates gnupg

# ── 2. Docker ─────────────────────────────────────────────────────────────────
echo "[2/8] Installing Docker..."
if ! command -v docker &>/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
else
  echo "   Docker already installed: $(docker --version)"
fi

# ── 3. Deploy user ────────────────────────────────────────────────────────────
echo "[3/8] Creating deploy user..."
if ! id -u deploy &>/dev/null; then
  useradd --system --shell /bin/bash --create-home deploy
  echo "   Created user: deploy"
else
  echo "   User deploy already exists"
fi

# Add deploy to docker group so it can run docker commands without sudo
usermod -aG docker deploy

# ── 4. SSH key for deploy user ────────────────────────────────────────────────
echo "[4/8] Setting up SSH key for deploy user..."
SSH_DIR=/home/deploy/.ssh
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

if [ ! -f "$SSH_DIR/deploy_ed25519" ]; then
  ssh-keygen -t ed25519 -C "waybill-deploy@$(hostname)" \
    -f "$SSH_DIR/deploy_ed25519" -N ""
  echo "   Generated new ed25519 key pair"
else
  echo "   SSH key already exists"
fi

# Install the public key as an authorized key for the deploy user
cat "$SSH_DIR/deploy_ed25519.pub" >> "$SSH_DIR/authorized_keys"
chmod 600 "$SSH_DIR/authorized_keys"
chown -R deploy:deploy "$SSH_DIR"

# ── 5. Slot file ──────────────────────────────────────────────────────────────
echo "[5/8] Creating slot file..."
mkdir -p /etc/deploy
echo "blue" > /etc/deploy/active-slot
chown root:deploy /etc/deploy/active-slot
chmod 664 /etc/deploy/active-slot   # deploy user can write directly

# ── 6. Nginx config ───────────────────────────────────────────────────────────
echo "[6/8] Configuring nginx..."
mkdir -p /etc/nginx/conf.d

# Upstream — defaults to blue slot on first deploy
cat > /etc/nginx/conf.d/waybill-upstream.conf << 'NGINX'
upstream waybill {
    server 127.0.0.1:7070;   # blue slot default
}
NGINX

# Main site config
cat > /etc/nginx/conf.d/waybill.conf << 'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass         http://waybill;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 5s;
        proxy_read_timeout    30s;
    }

    location /health {
        proxy_pass         http://waybill/health;
        proxy_set_header   Host $host;
        access_log         off;
    }
}
NGINX

nginx -t && systemctl reload nginx
echo "   nginx configured and reloaded"

# ── 7. Sudoers — least privilege ──────────────────────────────────────────────
echo "[7/8] Configuring sudoers..."
cat > /etc/sudoers.d/waybill-deploy << 'SUDOERS'
# deploy user permissions for blue/green pipeline
# Scope: write slot file, write nginx upstream config, reload nginx
# Nothing else. Not a general sudo grant.

deploy ALL=(ALL) NOPASSWD: /usr/bin/tee /etc/deploy/active-slot
deploy ALL=(ALL) NOPASSWD: /usr/bin/tee /etc/nginx/conf.d/waybill-upstream.conf
deploy ALL=(ALL) NOPASSWD: /usr/sbin/nginx -s reload
SUDOERS

chmod 440 /etc/sudoers.d/waybill-deploy
# Validate sudoers syntax before applying
visudo -c -f /etc/sudoers.d/waybill-deploy
echo "   Sudoers configured: slot file write + nginx reload only"

# ── 8. Enable nginx on boot ───────────────────────────────────────────────────
echo "[8/8] Enabling services..."
systemctl enable nginx
systemctl start nginx || systemctl reload nginx

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "=== Bootstrap complete ==="
echo ""
echo "Next steps:"
echo ""
echo "1. Add this PRIVATE KEY to your GitHub secret SSH_PRIVATE_KEY:"
echo "   (copy everything including the BEGIN/END lines)"
echo ""
cat /home/deploy/.ssh/deploy_ed25519
echo ""
echo "2. The public key is already in /home/deploy/.ssh/authorized_keys"
echo "   If you're adding an existing key, append it there manually:"
echo "   echo 'your-public-key' >> /home/deploy/.ssh/authorized_keys"
echo ""
echo "3. Add this server's IP to your GitHub secret SERVER_IP:"
hostname -I | awk '{print $1}'
echo ""
echo "4. Verify the deploy user can write the slot file without a password:"
echo "   sudo -u deploy sudo tee /etc/deploy/active-slot <<< 'blue'"
echo ""
echo "5. Verify nginx reloads without a password:"
echo "   sudo -u deploy sudo nginx -s reload"
echo ""
echo "6. Run docker compose up manually once to pull postgres and verify connectivity:"
echo "   cd /opt/app && sudo -u deploy docker compose up -d postgres"
echo ""
echo "Port layout (matches docker-compose.yml):"
echo "  waybill-blue:  7070 → 8000"
echo "  waybill-green: 9091 → 8000"
echo "  postgres:      5433 → 5432 (localhost only)"
echo ""
