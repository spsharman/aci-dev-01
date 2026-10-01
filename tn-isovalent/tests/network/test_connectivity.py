import os
import shlex
import socket
import subprocess

import pytest

JUMPHOST = os.environ.get("NETWORK_JUMPHOST", "localuser@10.237.101.6")
SOURCE_IP = os.environ.get("NETWORK_SOURCE_IP", "10.100.0.26")
DNS_SERVER_IPS = tuple(
    address.strip()
    for address in os.environ.get(
        "NETWORK_DNS_SERVER_IPS", "10.237.97.134,10.237.97.135"
    ).split(",")
    if address.strip()
)
JUMPHOST_INTERFACE_IPS = tuple(
    address.strip()
    for address in os.environ.get(
        "NETWORK_JUMPHOST_INTERFACE_IPS", "10.237.101.6,10.100.0.26"
    ).split(",")
    if address.strip()
)
SSH_BATCHMODE = os.environ.get("NETWORK_SSH_BATCHMODE", "no")

API_ENDPOINTS = (
    pytest.param(
        "k8s all-in-one API",
        "https://10.237.101.158:6443/livez",
        None,
        id="k8s-all-in-one",
    ),
    pytest.param(
        "ILB API",
        "https://api.ilb-01.uktme.cisco.com:6443/livez",
        401,
        id="ilb-api",
    ),
    pytest.param(
        "OpenShift API via ILB",
        "https://api.ocp-03.uktme.cisco.com:6443/livez",
        None,
        id="openshift-api",
    ),
)

API_PATHS = (
    pytest.param("local", None, id="outside"),
    pytest.param("jumphost", None, id="inside-default-source"),
    *(
        pytest.param("jumphost", address, id=f"inside-via-{address}")
        for address in JUMPHOST_INTERFACE_IPS
    ),
)
def run_command(origin, arguments, timeout=20):
    if origin == "local":
        command = list(arguments)
    else:
        control_path = os.path.expanduser("~/.ssh/tn-isovalent-%C")
        command = [
            "ssh",
            "-o",
            "ControlMaster=auto",
            "-o",
            "ControlPersist=300",
            "-o",
            f"ControlPath={control_path}",
            "-o",
            "ConnectTimeout=8",
            "-o",
            f"BatchMode={SSH_BATCHMODE}",
            JUMPHOST,
            shlex.join(arguments),
        ]

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        pytest.fail(f"Command timed out after {timeout}s: {error.cmd!r}")


def curl_status(origin, url, source_ip=None):
    arguments = [
        "curl",
        "--silent",
        "--show-error",
        "--noproxy",
        "*",
        "--output",
        "/dev/null",
        "--write-out",
        "%{http_code}",
        "--connect-timeout",
        "5",
        "--max-time",
        "12",
    ]
    if url.startswith("https://") and ":6443/" in url:
        arguments.append("--insecure")
    if source_ip:
        arguments.extend(("--interface", source_ip))
    arguments.append(url)

    result = run_command(origin, arguments)
    assert result.returncode == 0, (
        f"curl failed for {url} from {origin}: {result.stderr.strip()}"
    )
    status = result.stdout.strip()
    assert status.isdigit() and len(status) == 3, (
        f"No HTTP status returned for {url} from {origin}: {status!r}"
    )
    return int(status)


@pytest.mark.parametrize(("label", "url", "expected_status"), API_ENDPOINTS)
@pytest.mark.parametrize(("api_origin", "source_ip"), API_PATHS)
def test_api_livez_reachable(api_origin, source_ip, label, url, expected_status):
    status = curl_status(api_origin, url, source_ip)
    if expected_status is not None:
        assert status == expected_status, (
            f"{label} returned HTTP {status}; expected {expected_status} from "
            f"{api_origin}{f' using {source_ip}' if source_ip else ''}"
        )
    else:
        assert 200 <= status < 500, (
            f"{label} returned HTTP {status} from {api_origin}"
            f"{f' using {source_ip}' if source_ip else ''}; "
            "expected an HTTP response"
        )


@pytest.mark.parametrize(
    "source_ip", JUMPHOST_INTERFACE_IPS, ids=lambda ip: f"via-{ip}"
)
@pytest.mark.parametrize("dns_server", DNS_SERVER_IPS, ids=lambda ip: f"dns-{ip}")
def test_jumphost_can_reach_dns_servers(source_ip, dns_server):
    result = run_command(
        "jumphost",
        ("ping", "-c", "3", "-W", "2", "-I", source_ip, dns_server),
        timeout=15,
    )
    assert result.returncode == 0, (
        f"Cannot reach DNS server {dns_server} from jumphost using {source_ip}: "
        f"{result.stderr.strip()} {result.stdout.strip()}"
    )


def jumphost_host():
    host = JUMPHOST.rsplit("@", 1)[-1]
    if host.startswith("[") and "]" in host:
        return host[1 : host.index("]")]
    return host.split(":", 1)[0]


def test_jumphost_ssh_banner_reachable_from_outside():
    with socket.create_connection((jumphost_host(), 22), timeout=8) as connection:
        connection.settimeout(8)
        banner = connection.recv(255)
    assert banner.startswith(b"SSH-"), f"Unexpected SSH banner: {banner!r}"


@pytest.mark.parametrize(
    "source_ip",
    (None, SOURCE_IP),
    ids=("jumphost-default-source", "jumphost-internal-source"),
)
def test_jumphost_can_ping_internet(source_ip):
    arguments = ["ping", "-c", "3", "-W", "2"]
    if source_ip:
        arguments.extend(("-I", source_ip))
    arguments.append("8.8.8.8")
    result = run_command("jumphost", arguments, timeout=15)
    assert result.returncode == 0, (
        f"ping to 8.8.8.8 failed from jumphost"
        f"{f' using {source_ip}' if source_ip else ''}: {result.stderr.strip()}"
    )


@pytest.mark.parametrize(
    "source_ip",
    (None, SOURCE_IP),
    ids=("jumphost-default-source", "jumphost-internal-source"),
)
def test_jumphost_can_curl_internet(source_ip):
    status = curl_status("jumphost", "https://google.com/", source_ip)
    assert 200 <= status < 400, (
        f"google.com returned HTTP {status} from jumphost"
        f"{f' using {source_ip}' if source_ip else ''}"
    )
