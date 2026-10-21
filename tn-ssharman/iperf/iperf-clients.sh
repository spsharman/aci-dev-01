#!/usr/bin/env bash
#
# Start the iperf3 clients from the jumphost and show their output in YOUR ssh
# session. Each client runs on its own machine over SSH, so the traffic still
# goes machine to machine. Only the output comes back to you.
#
# Usage:
#   ./iperf-clients.sh list          show the 12 streams
#   ./iperf-clients.sh start         start all 12 in the background and return
#                                    (watch them with iperf-dashboard.py)
#   ./iperf-clients.sh A4            run one stream in the foreground (Ctrl+C stops it)
#   ./iperf-clients.sh all           run all 12, output interleaved with a [ID] label
#   ./iperf-clients.sh tmux          run all 12 in a tiled tmux window (needs tmux)
#   ./iperf-clients.sh stop          stop every client on every machine
#
# Ctrl+C in "all" mode stops all the clients.
#
# Optional environment variables:
#   SSH_USER   login name on the machines (default: your current user)
#   SSH_KEY    path to a private key to use (default: whatever ssh picks up)
#   DURATION   seconds to run (default: 0 = until you press Ctrl+C)
#   BITRATE    iperf3 target bitrate (default: 1M)
#
# Start the servers first with iperf-servers.sh.
# Authentication uses SSH keys or your ssh-agent. No passwords are stored or
# accepted by this script.

set -u

SSH_USER="${SSH_USER:-$(id -un)}"
DURATION="${DURATION:-0}"
BITRATE="${BITRATE:-1M}"

# ID:client host:server host:server port
STREAMS=(
  A1:10.237.99.172:10.237.99.171:5201
  A2:10.5.32.145:10.5.33.133:5202
  A3:10.237.99.184:10.237.99.189:5203
  A4:10.5.32.144:10.5.33.132:5204
  B1:10.237.99.171:10.237.99.184:5211
  B2:10.237.99.173:10.237.99.190:5212
  B3:10.5.33.133:10.5.32.146:5213
  B4:10.5.33.134:10.5.32.145:5214
  C1:10.237.99.189:10.5.32.144:5221
  C2:10.237.99.190:10.5.33.134:5222
  C3:10.5.32.146:10.237.99.172:5223
  C4:10.5.33.132:10.237.99.173:5224
)

SSH_OPTS=(
  -o BatchMode=yes
  -o ConnectTimeout=5
  -o StrictHostKeyChecking=accept-new
)
if [[ -n "${SSH_KEY:-}" ]]; then
  SSH_OPTS+=(-i "$SSH_KEY")
fi

usage() {
  sed -n '2,/^set -u/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
}

# The iperf3 command line that runs on the client machine.
client_cmd() {
  local server="$1" port="$2"
  printf 'iperf3 -c %s -p %s -t %s -b %s -l 1K -i 1' "$server" "$port" "$DURATION" "$BITRATE"
}

find_stream() {
  local want="$1" entry
  for entry in "${STREAMS[@]}"; do
    if [[ "${entry%%:*}" == "$want" ]]; then
      printf '%s\n' "$entry"
      return 0
    fi
  done
  return 1
}

list_streams() {
  printf '%-4s %-16s %-16s %s\n' ID CLIENT SERVER PORT
  local entry id client server port
  for entry in "${STREAMS[@]}"; do
    IFS=: read -r id client server port <<<"$entry"
    printf '%-4s %-16s %-16s %s\n' "$id" "$client" "$server" "$port"
  done
}

# One stream in the foreground. -tt gives the remote command a terminal, so it
# is stopped when you press Ctrl+C or the ssh session ends.
run_one() {
  local entry id client server port
  if ! entry="$(find_stream "$1")"; then
    echo "Unknown stream '$1'. Run '$0 list'." >&2
    exit 2
  fi
  IFS=: read -r id client server port <<<"$entry"
  echo "[$id] $client -> $server:$port"
  exec ssh -tt "${SSH_OPTS[@]}" "${SSH_USER}@${client}" "$(client_cmd "$server" "$port")"
}

# All streams at once in this terminal. Every line is prefixed with the stream
# ID, so you can see which one stops.
run_all() {
  local entry id client server port
  local pids=()
  trap 'echo; echo "Stopping all clients..."; kill "${pids[@]}" 2>/dev/null; wait 2>/dev/null; exit 0' INT TERM
  for entry in "${STREAMS[@]}"; do
    IFS=: read -r id client server port <<<"$entry"
    (
      ssh -tt "${SSH_OPTS[@]}" "${SSH_USER}@${client}" "$(client_cmd "$server" "$port")" </dev/null 2>&1 |
        tr -d '\r' |
        sed -u "s/^/[${id}] /"
    ) &
    pids+=("$!")
  done
  wait
}

# All streams in one tiled tmux window.
run_tmux() {
  if ! command -v tmux >/dev/null 2>&1; then
    echo "tmux is not installed here. Use '$0 all' instead, or install it with: sudo apt install tmux" >&2
    exit 1
  fi
  local session=iperf-clients entry id client server port first=1 cmd pane
  tmux kill-session -t "$session" 2>/dev/null
  for entry in "${STREAMS[@]}"; do
    IFS=: read -r id client server port <<<"$entry"
    cmd="ssh -tt ${SSH_OPTS[*]} ${SSH_USER}@${client} '$(client_cmd "$server" "$port")'; echo; echo '[$id] ended - press Enter to close'; read -r _"
    if ((first)); then
      pane="$(tmux new-session -d -P -F '#{pane_id}' -s "$session" -x 240 -y 60 "$cmd")"
      # Show a label on the top border of every tile, and stop programs in the
      # tiles from changing it.
      tmux set-option -t "$session" -w pane-border-status top
      tmux set-option -t "$session" -w pane-border-format ' #[bold]#{pane_title}#[default] '
      tmux set-option -t "$session" -w allow-rename off
      tmux set-option -g allow-set-title off 2>/dev/null || true
      first=0
    else
      pane="$(tmux split-window -t "$session" -P -F '#{pane_id}' "$cmd")"
      tmux select-layout -t "$session" tiled >/dev/null
    fi
    tmux select-pane -t "$pane" -T "[$id] $client -> $server:$port"
  done
  tmux select-layout -t "$session" tiled >/dev/null
  tmux attach -t "$session"
}

# Runs on the client machine. Finds iperf3 client processes by looking at each
# process's arguments, so it never matches its own shell (which "pkill -f" can).
REMOTE_FIND_CLIENTS="ps -C iperf3 -o pid=,args= | awk '/iperf3 -c /{print \$1}'"

# Start all 12 clients in the background and return. Nothing is printed by the
# clients. Watch them with iperf-dashboard.py. Each client writes to
# /tmp/iperf3-client-<ID>.log on its own machine.
start_all() {
  local entry id client server port i=0
  local workdir
  workdir="$(mktemp -d)"
  for entry in "${STREAMS[@]}"; do
    IFS=: read -r id client server port <<<"$entry"
    (
      out="$(ssh -n "${SSH_OPTS[@]}" "${SSH_USER}@${client}" "
        if [ -n \"\$(${REMOTE_FIND_CLIENTS})\" ]; then echo 'already running'; exit 0; fi
        setsid nohup $(client_cmd "$server" "$port") > /tmp/iperf3-client-${id}.log 2>&1 < /dev/null &
        sleep 2
        if [ -n \"\$(${REMOTE_FIND_CLIENTS})\" ]; then echo started; exit 0; fi
        echo \"did not start: \$(tail -n 1 /tmp/iperf3-client-${id}.log)\"; exit 1
      " 2>&1)"
      rc=$?
      printf '%s\n' "$rc" >"${workdir}/${i}.rc"
      printf '%s\n' "${out##*$'\n'}" >"${workdir}/${i}.msg"
    ) &
    i=$((i + 1))
  done
  wait

  local failed=0
  i=0
  for entry in "${STREAMS[@]}"; do
    IFS=: read -r id client server port <<<"$entry"
    local rc msg
    rc="$(<"${workdir}/${i}.rc")"
    msg="$(<"${workdir}/${i}.msg")"
    if [[ "$rc" == "0" ]]; then
      printf '%-4s %-16s -> %-16s port %-5s OK      %s\n' "$id" "$client" "$server" "$port" "$msg"
    else
      printf '%-4s %-16s -> %-16s port %-5s FAILED  %s\n' "$id" "$client" "$server" "$port" "$msg"
      failed=$((failed + 1))
    fi
    i=$((i + 1))
  done
  rm -rf "$workdir"
  echo
  if ((failed > 0)); then
    echo "${failed} of ${#STREAMS[@]} clients reported a problem."
    exit 1
  fi
  echo "All ${#STREAMS[@]} clients running. Start the dashboard: ./iperf-dashboard.py"
}

stop_all() {
  local entry id client server port
  for entry in "${STREAMS[@]}"; do
    IFS=: read -r id client server port <<<"$entry"
    (
      ssh -n "${SSH_OPTS[@]}" "${SSH_USER}@${client}" "for pid in \$(${REMOTE_FIND_CLIENTS}); do kill \"\$pid\"; done; true" >/dev/null 2>&1
      printf '%-4s %-16s clients stopped\n' "$id" "$client"
    ) &
  done
  wait
  tmux kill-session -t iperf-clients 2>/dev/null
  true
}

case "${1:-}" in
  list) list_streams ;;
  start) start_all ;;
  all) run_all ;;
  tmux) run_tmux ;;
  stop) stop_all ;;
  "" | -h | --help | help) usage ;;
  *) run_one "$1" ;;
esac
