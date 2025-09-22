## Remote Command Execution (Predefined, Safe Command Server)

A minimal client–server application that exposes a set of predefined, non-shell commands over a TCP socket. A Python client connects and issues JSON requests; the server returns JSON responses.

This project is designed for learning and controlled remote inspection. It does not support arbitrary command execution. It features token-based authentication, structured logging, and a safer ping implementation.

### Features

- Predefined, safe command handlers: system info, directory listing, disk and memory info, processes, network, file info, uptime, hostname, echo, ping, find file
- Token-based authentication (per-request token)
- Structured JSON logging on the server
- Safer `ping` using `shell=False` and argument lists
- Cross-platform (Windows/Linux/macOS)

### Requirements

- Python 3.8+
- pip
- Python packages:
  - `psutil`

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install psutil
```

### Repository Layout

- `server.py` — TCP server exposing predefined commands
- `client.py` — Interactive CLI client
- `README.md` — This guide

### Quick Start

1) Start the server (with token):

```powershell
cd 'C:\Users\biswa\Desktop\Remote Command Execution'
$env:RCE_TOKEN='test123'
python server.py --host 127.0.0.1 --port 9999 --token $env:RCE_TOKEN
```

2) In another terminal, start the client and connect using the same token:

```powershell
cd 'C:\Users\biswa\Desktop\Remote Command Execution'
$env:RCE_TOKEN='test123'
python client.py 127.0.0.1 --port 9999 --token $env:RCE_TOKEN
```

3) Try commands in the client shell:

```
help
sysinfo
listdir C:\
diskspace C:\
processlist 10
meminfo
netinfo
fileinfo C:\Windows\explorer.exe
uptime
hostname
echo Hello from client
ping 8.8.8.8 2
findfile Desktop C:\Users
exit
```

### Authentication

The server can require a token for every request.

- Provide a token via CLI (`--token`) or environment (`RCE_TOKEN`).
- The client forwards the token on each request automatically if provided.
- If the server has a token enabled and the client omits or mismatches it, the server returns `{"status":"error","error":"Unauthorized"}`.

Examples:

```powershell
# Server
$env:RCE_TOKEN='secret'
python server.py --host 127.0.0.1 --port 9999 --token $env:RCE_TOKEN

# Client
$env:RCE_TOKEN='secret'
python client.py 127.0.0.1 --port 9999 --token $env:RCE_TOKEN
```

### Protocol

The client sends a single JSON object per request on the TCP socket. Fields:

- `command` (string): one of the server's predefined commands
- `args` (object, optional): command-specific arguments
- `token` (string, optional): required if server auth is enabled

Example request/response (echo):

```json
{"command":"echo","args":{"message":"Hello"},"token":"test123"}
```

```json
{"status":"success","result":"Hello"}
```

### Available Commands

- `sysinfo`: Basic OS and CPU info
- `listdir [path]`: List directory items; default `.`
- `diskspace [path]`: Disk usage for path; default `.`
- `processlist [limit]`: Top processes by memory; default 10
- `meminfo`: Physical and swap memory stats
- `netinfo`: Interfaces, status, and IO counters
- `fileinfo <path>`: File/directory metadata
- `uptime`: System boot time and uptime seconds
- `hostname`: Hostname and FQDN
- `echo <message>`: Echo back a message
- `ping <host> [count]`: ICMP ping; default count 4 (uses `shell=False`)
- `findfile <pattern> [path]`: Case-insensitive substring match; capped at 100 results

Notes:

- Some commands rely on `psutil`. Without it, functionality will be limited.
- Timestamps are seconds since epoch.

### Client Usage

```text
python client.py [host] [--port PORT] [--token TOKEN]
```

Defaults:

- `host`: `127.0.0.1`
- `--port`: `9999`
- `--token`: Taken from `RCE_TOKEN` if not specified

Interactive shell helpers:

- `help` lists all commands
- `exit` disconnects and closes the client

### Server Usage

```text
python server.py [--host HOST] [--port PORT] [--token TOKEN]
```

Defaults:

- `--host`: `127.0.0.1`
- `--port`: `9999`
- `--token`: Taken from `RCE_TOKEN` if not specified; if omitted entirely, auth is disabled

### Structured Logging

The server prints JSON log lines to stdout. Examples:

```json
{"event": "server_started", "host": "127.0.0.1", "port": 9999, "auth_enabled": true, "commands": ["sysinfo", "listdir", "diskspace", "processlist", "meminfo", "netinfo", "fileinfo", "uptime", "hostname", "echo", "ping", "findfile"]}
{"event": "client_connected", "ip": "127.0.0.1", "port": 54321}
{"event": "client_disconnected", "ip": "127.0.0.1", "port": 54321}
{"event": "server_stopped"}
```

You can pipe these into a JSON-aware log processor or store them for analysis.

### Security Considerations

- Only predefined commands are accepted; arbitrary execution is not supported.
- Authentication (token) is available but plaintext over TCP. For sensitive environments, deploy behind TLS-terminating proxies or add TLS support.
- Input is minimally validated. Use safe defaults and keep the server bound to `127.0.0.1` unless you trust the network.
- `ping` uses `shell=False` to mitigate injection risks.

### Troubleshooting

- Cannot connect:
  - Ensure the server is running and listening on the correct host/port.
  - Firewalls may block `9999`. Try `127.0.0.1` first.
- Unauthorized:
  - Make sure server and client use the same token. Check `RCE_TOKEN` values.
- `psutil` not found:
  - `python -m pip install psutil`
- Windows quoting issues:
  - Prefer the shown PowerShell commands; avoid complex inline one-liners.

### Development Notes

- Code style: Python standard library + readable, explicit code
- Areas to extend:
  - File upload/download with checksums
  - Pagination for long outputs
  - Async (`asyncio`) server for higher concurrency
  - Tests (unit/integration) and CI
  - Optional TLS

### License

For educational and internal use. Add your preferred license text here.
