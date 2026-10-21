#!/usr/bin/env bash
#
# Start, stop or check the iperf3 servers on all 12 demo machines from the jumphost.
# Each machine listens on the port of the stream it receives (see iperf-settings.md).
# The clients are started by hand.
#
# Usage:
#   ./iperf-servers.sh start     start a server on every host (default)
#   ./iperf-servers.sh stop      stop the iperf3 servers on every host
#   ./iperf-servers.sh status    show whether a server is listening on every host
#
# start does not kill anything. If the right port is already listening on a
# host it is left alone, so it is safe to run twice. To clear everything first,
# run "./iperf-servers.sh stop" (or killall iperf3 on the machines).
#
# All hosts are handled in parallel, so the whole run takes a few seconds.
#
# Optional environment variables:
#   SSH_USER   login name on the machines (default: your current user)
#   SSH_KEY    path to a private key to use (default: whatever ssh picks up)
#
# Authentication uses SSH keys or your ssh-agent. No passwords are stored or
# accepted by this script.

set -u

ACTION="${1:-start}"
SSH_USER="${SSH_USER:-$(id -un)}"

# host:port:stream. The port is the one the stream that ends on this host uses.
SERVERS=(
  10.5.32.144:5221:C1
  10.5.32.145:5214:B4
  10.5.32.146:5213:B3
  10.5.33.132:5204:A4
  10.5.33.133:5202:A2
  10.5.33.134:5222:C2
  10.237.99.171:5201:A1
  10.237.99.172:5223:C3
  10.237.99.173:5224:C4
  10.237.99.184:5211:B1
  10.237.99.189:5203:A3
  10.237.99.190:5212:B2
)

SSH_OPTS=(
  -o BatchMode=yes
  -o ConnectTimeout=5
  -o StrictHostKeyChecking=accept-new
)
if [[ -n "${SSH_KEY:-}" ]]; then
  SSH_OPTS+=(-i "$SSH_KEY")
fi

case "$ACTION" in
  start | stop | status) ;;
  *)
    echo "Usage: $0 {start|stop|status}" >&2
    exit 2
    ;;
esac

# Runs on the remote machine. $1 is the port. Prints one short result word and
# exits 0 on success. Success for start and status means the port is really
# listening, not just that some iperf3 process exists.
remote_script() {
  local port="$1"
  case "$ACTION" in
    start)
      cat <<EOF
listening() { ss -ltn 2>/dev/null | grep -Eq ":${port}[[:space:]]"; }
if ! command -v iperf3 >/dev/null 2>&1; then echo "iperf3 is not installed"; exit 1; fi
if listening; then echo "already running"; exit 0; fi
iperf3 -s -p ${port} -i 1 -D --logfile /tmp/iperf3-server-${port}.log
sleep 1
if listening; then echo "started"; exit 0; fi
echo "did not start, see /tmp/iperf3-server-${port}.log"; exit 1
EOF
      ;;
    stop)
      cat <<EOF
pkill -x iperf3 2>/dev/null
echo "stopped"
exit 0
EOF
      ;;
    status)
      cat <<EOF
if ss -ltn 2>/dev/null | grep -Eq ":${port}[[:space:]]"; then echo "listening"; exit 0; fi
echo "NOT listening"; exit 1
EOF
      ;;
  esac
}

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

# Start every host in the background, one result file each.
i=0
for entry in "${SERVERS[@]}"; do
  IFS=: read -r host port stream <<<"$entry"
  (
    out="$(remote_script "$port" | ssh "${SSH_OPTS[@]}" "${SSH_USER}@${host}" "bash -s" 2>&1)"
    rc=$?
    printf '%s\n' "$rc" >"${workdir}/${i}.rc"
    printf '%s\n' "${out##*$'\n'}" >"${workdir}/${i}.msg"
  ) &
  i=$((i + 1))
done
wait

# Print the results in list order.
failed=0
i=0
for entry in "${SERVERS[@]}"; do
  IFS=: read -r host port stream <<<"$entry"
  rc="$(<"${workdir}/${i}.rc")"
  msg="$(<"${workdir}/${i}.msg")"
  if [[ "$rc" == "0" ]]; then
    printf '%-16s %-3s port %-5s OK      %s\n' "$host" "$stream" "$port" "$msg"
  else
    printf '%-16s %-3s port %-5s FAILED  %s\n' "$host" "$stream" "$port" "$msg"
    failed=$((failed + 1))
  fi
  i=$((i + 1))
done

echo
if ((failed > 0)); then
  echo "${failed} of ${#SERVERS[@]} hosts reported a problem."
  exit 1
fi
echo "All ${#SERVERS[@]} hosts OK."
