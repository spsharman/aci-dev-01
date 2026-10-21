#!/usr/bin/env python3
"""Live dashboard for the 12 iperf3 demo streams. Run it on the jumphost.

For every stream it follows the iperf3 SERVER log on the receiving machine
over SSH and draws one row:

    ID  client -> server   state   rate   timeline

The timeline starts at the left when you start the dashboard and grows to the
right, one cell per second. Green means data arrived and red means 0 bytes
arrived. When the timeline reaches the right-hand edge it scrolls left. A time
axis underneath the streams shows the clock time of each column, so you can
point at the moment a stream turned red.

The server side is used because it shows a drop straight away. A client
console can keep showing about 1 Mbit/s for a while after a stream is blocked,
until its send buffer fills.

Usage:
    ./iperf-dashboard.py              run until Ctrl+C
    ./iperf-dashboard.py --once 10    wait 10 seconds, print one frame, exit

Environment variables:
    SSH_USER   login name on the machines (default: your current user)
    SSH_KEY    path to a private key to use (default: whatever ssh picks up)

Start the servers first with iperf-servers.sh, then the clients. The server
logs are /tmp/iperf3-server-<port>.log on each machine. Only data that arrives
after the dashboard starts is drawn.

Authentication uses SSH keys or your ssh-agent. No passwords are stored or
accepted by this script.
"""

import getpass
import os
import re
import shutil
import subprocess
import sys
import threading
import time

# ID, client host, server host, server port. Keep in step with iperf-clients.sh.
STREAMS = [
    ("A1", "10.237.99.172", "10.237.99.171", 5201),
    ("A2", "10.5.32.145", "10.5.33.133", 5202),
    ("A3", "10.237.99.184", "10.237.99.189", 5203),
    ("A4", "10.5.32.144", "10.5.33.132", 5204),
    ("B1", "10.237.99.171", "10.237.99.184", 5211),
    ("B2", "10.237.99.173", "10.237.99.190", 5212),
    ("B3", "10.5.33.133", "10.5.32.146", 5213),
    ("B4", "10.5.33.134", "10.5.32.145", 5214),
    ("C1", "10.237.99.189", "10.5.32.144", 5221),
    ("C2", "10.237.99.190", "10.5.33.134", 5222),
    ("C3", "10.5.32.146", "10.237.99.172", 5223),
    ("C4", "10.5.33.132", "10.237.99.173", 5224),
]

SSH_USER = os.environ.get("SSH_USER") or getpass.getuser()
SSH_KEY = os.environ.get("SSH_KEY")

DOWN_AFTER = 3  # this many zero seconds in a row counts as DOWN
STALE_AFTER = 5.0  # no new log line for this long counts as NO DATA
MAX_BAR = 150  # widest timeline, in seconds
TICK_EVERY = 10  # a tick mark every this many seconds
LABEL_EVERY = 30  # a time label every this many seconds
LABEL_WIDTH = 8  # HH:MM:SS

GREEN = "\x1b[32m"
RED = "\x1b[31m"
YELLOW = "\x1b[33m"
GREY = "\x1b[90m"
BOLD = "\x1b[1m"
RESET = "\x1b[0m"

# Example server line: [  6]  431.00-432.00 sec   128 KBytes  1.05 Mbits/sec
LINE = re.compile(
    r"\]\s+(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\s+sec\s+\S+\s+\S*Bytes\s+"
    r"([\d.]+)\s+([KMG]?)bits/sec"
)
UNIT = {"": 1e-6, "K": 1e-3, "M": 1.0, "G": 1e3}

# Cell 0 of the timeline is this second. Set when the dashboard starts.
START = int(time.time())


class Stream:
    def __init__(self, sid, client, server, port):
        self.sid = sid
        self.client = client
        self.server = server
        self.port = port
        self.cells = {}  # second since START -> Mbit/s
        self.last_idx = None
        self.last_end = -1.0
        self.anchor_idx = 0
        self.anchor_end = 0.0
        self.last_rx = 0.0
        self.error = ""
        self.lock = threading.Lock()
        self.proc = None
        self.stop = False

    def ssh_command(self):
        cmd = [
            "ssh",
            "-tt",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=5",
            "-o",
            "StrictHostKeyChecking=accept-new",
        ]
        if SSH_KEY:
            cmd += ["-i", SSH_KEY]
        cmd += [
            f"{SSH_USER}@{self.server}",
            f"tail -n 0 -F /tmp/iperf3-server-{self.port}.log",
        ]
        return cmd

    def feed(self, line):
        if "sender" in line or "receiver" in line:
            return
        m = LINE.search(line)
        if not m:
            return
        start, end = float(m.group(1)), float(m.group(2))
        if end - start > 1.5:
            return
        mbit = float(m.group(3)) * UNIT[m.group(4)]
        now = time.time()
        with self.lock:
            # The first line, or a new test (the interval counter went back to
            # the start), fixes which timeline column this interval belongs to.
            # After that the interval numbers keep the columns in step.
            if self.last_idx is None or end < self.last_end:
                self.anchor_idx = int(round(now - START))
                self.anchor_end = end
            idx = self.anchor_idx + int(round(end - self.anchor_end))
            self.cells[idx] = mbit
            self.last_idx = idx
            self.last_end = end
            self.last_rx = now
            self.error = ""

    def run(self):
        while not self.stop:
            try:
                self.proc = subprocess.Popen(
                    self.ssh_command(),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    errors="replace",
                )
                tail = ""
                for raw in self.proc.stdout:
                    line = raw.replace("\r", "").strip()
                    if line:
                        tail = line
                    self.feed(line)
                with self.lock:
                    self.error = tail[:60] if tail else "ssh ended"
            except OSError as exc:
                with self.lock:
                    self.error = str(exc)[:60]
            if not self.stop:
                time.sleep(3)

    def snapshot(self):
        with self.lock:
            return dict(self.cells), self.last_idx, self.last_rx, self.error

    def terminate(self):
        self.stop = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()


def fmt_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m{seconds % 60:02d}s"


def describe(cells, last_idx, last_rx, error, now):
    """Return (state text, colour, rate text)."""
    if last_idx is None:
        return "WAITING", GREY, "   -    "
    rate = f"{cells[last_idx]:6.2f} Mb"
    age = now - last_rx
    if age > STALE_AFTER:
        return f"NO DATA {fmt_duration(age)}", YELLOW, rate
    zeros = 0
    i = last_idx
    while cells.get(i) == 0:
        zeros += 1
        i -= 1
    if zeros >= DOWN_AFTER:
        return f"DOWN {fmt_duration(zeros)}", RED, rate
    return "UP", GREEN, rate


def axis(window_start, width):
    """Two lines: tick marks, then HH:MM:SS labels, one column per second."""
    ticks = []
    labels = [" "] * width
    for col in range(width):
        t = START + window_start + col
        if t % TICK_EVERY == 0:
            ticks.append("┬")
        else:
            ticks.append("─")
        if t % LABEL_EVERY == 0 and col + LABEL_WIDTH <= width:
            text = time.strftime("%H:%M:%S", time.localtime(t))
            labels[col : col + LABEL_WIDTH] = list(text)
    return "".join(ticks), "".join(labels)


def render(streams, color=True):
    cols = shutil.get_terminal_size((140, 40)).columns
    # ID (2) + gap + client -> server (31) + gap + state (12) + gap + rate (9) + gap
    prefix = 2 + 2 + 31 + 2 + 12 + 2 + 9 + 2
    width = max(20, min(MAX_BAR, cols - prefix))
    now = time.time()
    current = int(now) - START  # the newest second
    window_start = 0 if current < width else current - width + 1

    def paint(text, colour):
        return f"{colour}{text}{RESET}" if color and colour else text

    rows = []
    errors = []
    up = 0
    down_ids = []
    last_tier = None
    for s in streams:
        cells, last_idx, last_rx, error = s.snapshot()
        state, colour, rate = describe(cells, last_idx, last_rx, error, now)
        if state == "UP":
            up += 1
        elif state.startswith("DOWN"):
            down_ids.append(s.sid)
        if last_tier is not None and s.sid[0] != last_tier:
            rows.append("")
        last_tier = s.sid[0]

        bar = []
        for col in range(width):
            idx = window_start + col
            if idx > current:
                bar.append(" ")  # the future
            elif idx in cells:
                bar.append(paint("█", GREEN if cells[idx] > 0 else RED))
            else:
                bar.append(paint("·", GREY))  # no data for this second
        pair = f"{s.client} -> {s.server}"
        rows.append(
            f"{paint(s.sid, BOLD)}  {pair:<31}  "
            f"{paint(f'{state:<12.12}', colour)}  {rate:<9}  {''.join(bar)}"
        )
        if error:
            errors.append(f"{s.sid} ({s.server}): {error}")

    ticks, labels = axis(window_start, width)
    axis_lines = [
        paint("time", GREY) + " " * (prefix - 4) + paint(ticks, GREY),
        " " * prefix + paint(labels, GREY),
    ]

    head = [
        paint("iperf3 stream monitor", BOLD)
        + f"   {time.strftime('%H:%M:%S')}   "
        + "one cell = one second, oldest on the left   "
        + paint("green", GREEN)
        + " = data received   "
        + paint("red", RED)
        + " = 0 bytes",
        "",
    ]
    summary_colour = GREEN if not down_ids else RED
    summary = f"Streams up: {up}/{len(streams)}"
    if down_ids:
        summary += "    DOWN: " + " ".join(down_ids)
    foot = [
        "",
        paint(summary, summary_colour),
        paint(
            f"Monitoring since {time.strftime('%H:%M:%S', time.localtime(START))}. "
            "Ctrl+C to quit",
            GREY,
        ),
    ]
    if errors:
        foot += ["", paint("Cannot read these logs (run this on the jumphost, with SSH_USER set):", YELLOW)]
        foot += [paint("  " + e, YELLOW) for e in errors]
    return head + rows + [""] + axis_lines + foot


def main():
    once = None
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if args and args[0] == "--once":
        once = float(args[1]) if len(args) > 1 else 10.0

    streams = [Stream(*entry) for entry in STREAMS]
    for s in streams:
        threading.Thread(target=s.run, daemon=True).start()

    try:
        if once is not None:
            time.sleep(once)
            print("\n".join(render(streams, color=sys.stdout.isatty())))
            return 0

        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        while True:
            frame = "\x1b[H" + "\n".join(line + "\x1b[K" for line in render(streams))
            sys.stdout.write(frame + "\x1b[J")
            sys.stdout.flush()
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
    finally:
        if once is None:
            sys.stdout.write("\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()
        for s in streams:
            s.terminate()


if __name__ == "__main__":
    sys.exit(main())
