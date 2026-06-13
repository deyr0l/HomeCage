#!/bin/sh
set -eu

SERVICE_NAME="${SERVICE_NAME:-homecage-server}"
INSTALL_DIR="${INSTALL_DIR:-/opt/homecage-server}"
SERVICE_USER="${SERVICE_USER:-homecage}"
SERVICE_GROUP="${SERVICE_GROUP:-$SERVICE_USER}"
HOST="${HOMECAGE_HOST:-0.0.0.0}"
START_PORT="${HOMECAGE_PORT:-8000}"
DATA_DIR="${HOMECAGE_DATA_DIR:-$INSTALL_DIR/data}"
SOURCE_DIR="$(CDPATH= cd "$(dirname "$0")" && pwd)"
CHOWN_TARGET="$SERVICE_USER:$SERVICE_GROUP"

need_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root. Example: su -; cd $SOURCE_DIR; ./install-service.sh" >&2
    exit 1
  fi
}

detect_os() {
  if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    echo "${ID:-linux}"
  else
    echo "linux"
  fi
}

print_package_hint() {
  os_id="$1"
  case "$os_id" in
    alpine) echo "Install prerequisites with: apk add python3 py3-pip py3-virtualenv openrc" ;;
    debian|ubuntu) echo "Install prerequisites with: apt-get update && apt-get install -y python3 python3-venv python3-pip" ;;
    fedora) echo "Install prerequisites with: dnf install -y python3 python3-pip" ;;
    arch) echo "Install prerequisites with: pacman -S --needed python python-pip" ;;
    *) echo "Install Python 3 with venv support for your distribution." ;;
  esac
}

require_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    print_package_hint "$(detect_os)" >&2
    exit 1
  fi
  if ! python3 -m venv --help >/dev/null 2>&1; then
    print_package_hint "$(detect_os)" >&2
    exit 1
  fi
}

detect_init() {
  if command -v systemctl >/dev/null 2>&1 && [ -d /run/systemd/system ]; then
    echo "systemd"
  elif command -v rc-service >/dev/null 2>&1 && command -v rc-update >/dev/null 2>&1; then
    echo "openrc"
  else
    echo "unknown"
  fi
}

find_free_port() {
  python3 - "$START_PORT" <<'PY'
import socket
import sys

port = int(sys.argv[1])
while port < 65535:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
        except OSError:
            port += 1
            continue
        print(port)
        raise SystemExit(0)
raise SystemExit("No free TCP port found")
PY
}

generate_token() {
  if [ -n "${HOMECAGE_ADMIN_TOKEN:-}" ]; then
    echo "$HOMECAGE_ADMIN_TOKEN"
  elif command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 24
  else
    python3 - <<'PY'
import secrets
print(secrets.token_hex(24))
PY
  fi
}

group_exists() {
  if command -v getent >/dev/null 2>&1; then
    getent group "$SERVICE_GROUP" >/dev/null 2>&1
    return $?
  fi
  [ -r /etc/group ] && grep -q "^$SERVICE_GROUP:" /etc/group
}

user_exists() {
  id -u "$SERVICE_USER" >/dev/null 2>&1
}

create_group() {
  if command -v addgroup >/dev/null 2>&1; then
    addgroup -S "$SERVICE_GROUP" 2>/dev/null && return 0
    addgroup --system "$SERVICE_GROUP" 2>/dev/null && return 0
    addgroup "$SERVICE_GROUP" 2>/dev/null && return 0
  fi

  if command -v groupadd >/dev/null 2>&1; then
    groupadd --system "$SERVICE_GROUP" 2>/dev/null && return 0
    groupadd "$SERVICE_GROUP" 2>/dev/null && return 0
  fi

  return 1
}

create_user() {
  nologin_shell="/sbin/nologin"
  [ -x /usr/sbin/nologin ] && nologin_shell="/usr/sbin/nologin"
  [ -x /bin/false ] && nologin_shell="/bin/false"

  if command -v adduser >/dev/null 2>&1; then
    adduser -S -D -H -s "$nologin_shell" -G "$SERVICE_GROUP" "$SERVICE_USER" 2>/dev/null && return 0
    adduser --system --no-create-home --shell "$nologin_shell" --ingroup "$SERVICE_GROUP" "$SERVICE_USER" 2>/dev/null && return 0
  fi

  if command -v useradd >/dev/null 2>&1; then
    useradd --system --no-create-home --shell "$nologin_shell" --gid "$SERVICE_GROUP" "$SERVICE_USER" 2>/dev/null && return 0
    useradd -r -M -s "$nologin_shell" -g "$SERVICE_GROUP" "$SERVICE_USER" 2>/dev/null && return 0
  fi

  return 1
}

ensure_user() {
  if ! group_exists; then
    if ! create_group; then
      echo "Could not create group '$SERVICE_GROUP'. Install adduser/addgroup or set SERVICE_USER=root SERVICE_GROUP=root." >&2
      exit 1
    fi
  fi

  if ! user_exists; then
    if ! create_user; then
      echo "Could not create user '$SERVICE_USER'. Install adduser/useradd or set SERVICE_USER=root SERVICE_GROUP=root." >&2
      exit 1
    fi
  fi

  chown_check_dir="${TMPDIR:-/tmp}/$SERVICE_NAME-chown-check-$$"
  mkdir -p "$chown_check_dir"
  if ! chown "$CHOWN_TARGET" "$chown_check_dir" 2>/dev/null; then
    rm -rf "$chown_check_dir"
    echo "User/group '$CHOWN_TARGET' is not valid for chown." >&2
    exit 1
  fi
  rm -rf "$chown_check_dir"
}

install_files() {
  mkdir -p "$INSTALL_DIR"
  if [ "$SOURCE_DIR" != "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR/app"
    cp -R "$SOURCE_DIR/app" "$INSTALL_DIR/app"
    cp "$SOURCE_DIR/pyproject.toml" "$INSTALL_DIR/pyproject.toml"
    cp "$SOURCE_DIR/README.md" "$INSTALL_DIR/README.md"
  fi
  chown -R "$CHOWN_TARGET" "$INSTALL_DIR"
}

install_python_env() {
  python3 -m venv "$INSTALL_DIR/.venv"
  "$INSTALL_DIR/.venv/bin/python" -m pip install --upgrade pip
  "$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR"
  chown -R "$CHOWN_TARGET" "$INSTALL_DIR/.venv"
}

env_quote() {
  printf '"'
  printf "%s" "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\$/\\$/g; s/`/\\`/g'
  printf '"'
}

write_env_file() {
  token="$1"
  port="$2"
  mkdir -p "$DATA_DIR"
  chown -R "$CHOWN_TARGET" "$DATA_DIR"
  cat > /etc/"$SERVICE_NAME".env <<EOF
HOMECAGE_ADMIN_TOKEN=$(env_quote "$token")
HOMECAGE_HOST=$(env_quote "$HOST")
HOMECAGE_PORT=$(env_quote "$port")
HOMECAGE_DATA_DIR=$(env_quote "$DATA_DIR")
EOF
  chmod 0600 /etc/"$SERVICE_NAME".env
}

install_systemd_service() {
  cat > /etc/systemd/system/"$SERVICE_NAME".service <<EOF
[Unit]
Description=HomeCage Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=/etc/$SERVICE_NAME.env
ExecStart=$INSTALL_DIR/.venv/bin/homecage-server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable --now "$SERVICE_NAME"
}

install_openrc_service() {
  cp /etc/"$SERVICE_NAME".env /etc/conf.d/"$SERVICE_NAME"
  cat > /etc/init.d/"$SERVICE_NAME" <<EOF
#!/sbin/openrc-run

name="HomeCage Server"
description="HomeCage local admin server"
supervisor="supervise-daemon"

if [ -r "/etc/conf.d/$SERVICE_NAME" ]; then
    set -a
    . "/etc/conf.d/$SERVICE_NAME"
    set +a
fi

export HOMECAGE_ADMIN_TOKEN HOMECAGE_HOST HOMECAGE_PORT HOMECAGE_DATA_DIR

command="$INSTALL_DIR/.venv/bin/homecage-server"
command_user="$SERVICE_USER:$SERVICE_GROUP"
directory="$INSTALL_DIR"
output_log="/var/log/$SERVICE_NAME.log"
error_log="/var/log/$SERVICE_NAME.err"
supervise_daemon_args="--respawn-delay 5 --respawn-max 0"

depend() {
    need net
    after firewall
}

start_pre() {
    checkpath -f -m 0644 -o "$SERVICE_USER:$SERVICE_GROUP" "/var/log/$SERVICE_NAME.log"
    checkpath -f -m 0644 -o "$SERVICE_USER:$SERVICE_GROUP" "/var/log/$SERVICE_NAME.err"
    checkpath -d -m 0750 -o "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR"
}
EOF
  chmod +x /etc/init.d/"$SERVICE_NAME"
  rc-update add "$SERVICE_NAME" default
  rc-service "$SERVICE_NAME" restart
}

main() {
  need_root
  require_python
  init_system="$(detect_init)"
  if [ "$init_system" = "unknown" ]; then
    echo "Unsupported init system. systemd or OpenRC is required." >&2
    exit 1
  fi

  port="$(find_free_port)"
  token="$(generate_token)"

  ensure_user
  install_files
  install_python_env
  write_env_file "$token" "$port"

  case "$init_system" in
    systemd) install_systemd_service ;;
    openrc) install_openrc_service ;;
  esac

  server_ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  [ -n "$server_ip" ] || server_ip="127.0.0.1"

  echo
  echo "HomeCage Server installed."
  echo "Init system: $init_system"
  echo "URL: http://$server_ip:$port/"
  echo "Port: $port"
  echo "Token: $token"
  echo "Environment file: /etc/$SERVICE_NAME.env"
}

main "$@"
