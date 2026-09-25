#!/usr/bin/env bash
# One-time hardening for a fresh Ubuntu 24.04 LTS VPS that will run SerpTank.
# Run as root:  ADMIN_USER=alice ADMIN_KEY="ssh-ed25519 AAAA..." ./harden.sh
# Review before running; it changes SSH access and the firewall.
set -euo pipefail

: "${ADMIN_USER:?set ADMIN_USER}"
: "${ADMIN_KEY:?set ADMIN_KEY (public SSH key)}"
: "${SSH_ALLOW_FROM:=0.0.0.0/0}"   # restrict to your office/VPN range if you can

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y upgrade
apt-get -y install unattended-upgrades nftables fail2ban age rclone curl ca-certificates

# Admin user with key-only SSH, no root login, no passwords.
id "$ADMIN_USER" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "$ADMIN_USER"
usermod -aG sudo "$ADMIN_USER"
install -d -m 700 -o "$ADMIN_USER" -g "$ADMIN_USER" "/home/$ADMIN_USER/.ssh"
printf '%s\n' "$ADMIN_KEY" > "/home/$ADMIN_USER/.ssh/authorized_keys"
chown "$ADMIN_USER:$ADMIN_USER" "/home/$ADMIN_USER/.ssh/authorized_keys"
chmod 600 "/home/$ADMIN_USER/.ssh/authorized_keys"
cat > /etc/ssh/sshd_config.d/10-serptank.conf <<'SSH'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
X11Forwarding no
AllowAgentForwarding no
MaxAuthTries 3
LoginGraceTime 20
SSH
sshd -t
systemctl reload ssh

# Deploy user (no sudo) that owns /opt/serptank and runs docker compose.
id serptank >/dev/null 2>&1 || adduser --system --group --home /opt/serptank serptank
install -d -m 750 -o serptank -g serptank /opt/serptank /opt/serptank/secrets /opt/serptank/config
chmod 700 /opt/serptank/secrets

# Firewall: default deny in; SSH (optionally restricted) and HTTP(S) only.
cat > /etc/nftables.conf <<NFT
#!/usr/sbin/nft -f
flush ruleset
table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;
    iif lo accept
    ct state established,related accept
    ct state invalid drop
    ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded } limit rate 10/second accept
    ip6 nexthdr icmpv6 accept
    tcp dport 22 ip saddr ${SSH_ALLOW_FROM} ct state new limit rate 10/minute accept
    tcp dport { 80, 443 } accept
    udp dport 443 accept
  }
  chain forward { type filter hook forward priority 0; policy accept; }
  chain output { type filter hook output priority 0; policy accept; }
}
NFT
systemctl enable --now nftables
nft -f /etc/nftables.conf

# Docker publishes ports through its own iptables chains; only Caddy publishes any.
# Automatic security updates.
dpkg-reconfigure -f noninteractive unattended-upgrades
systemctl enable --now fail2ban

# Kernel hardening.
cat > /etc/sysctl.d/99-serptank.conf <<'SYS'
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.tcp_syncookies = 1
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
fs.protected_symlinks = 1
fs.protected_hardlinks = 1
SYS
sysctl --system >/dev/null

echo "Hardening done. Next: install Docker Engine from Docker's apt repo, add 'serptank'"
echo "to the docker group, then follow docs/runbooks/deploy.md."
