# Local peer protocol

This document describes `claude-peer/scripts/peer.py`. The Claude Code
socket format is an observed internal interface. This is not an official
or stable Claude Code protocol specification.

## Participants and addresses

- **Claude agent record:** `~/.claude/sessions/<pid>.json` holds its name,
  PID, process start time, status, socket path, and version.
- **Claude peer key:** a private file named
  `~/.claude/sessions/<pid>.<sha256(socket-path)>.key` holds `peerToken`
  and the process start time.
- **Codex relay:** `/tmp/cc-socks/<pid>.sock` receives frames for one
  Codex thread. Its temporary record and key use Claude's session directory.
- **Relay state:**
  `/tmp/codex-claude-peer-state-<uid>/<thread-uuid>.json` maps a Codex
  thread to its live relay PID, socket, and process start time.
- **Relay inbox:**
  `/tmp/codex-claude-peer-state-<uid>/<thread-uuid>.inbox.jsonl`
  records incoming frames and queue results.

All sockets use Unix domain streams. There is no TCP transport or remote
peer discovery. `peer.py list` shows Claude records with a `version` field.
`list --include-codex` also shows temporary relay records with
`peerProtocol: 1` and no Claude version.

A record is live only if its PID has the recorded process start time and
its socket exists. This guards against PID reuse. Listing can use `lsof`
when `ps` cannot read a start time. `send`, `reply`, and `status` require
the normal start-time check. A sandbox that blocks `ps` may require an
escalated read of the local process table.

## Registration and lifecycle

`serve --thread <uuid>` creates a socket under `/tmp/cc-socks`, writes a
random 128-bit peer token to a private key file, then writes a Claude-shaped
session record and thread state. The record's name is `codex-` plus an
11-character URL-safe random ID. The relay checks existing names before
using one. It advertises `peerProtocol: 1`, `kind: "bg"`,
`entrypoint: "cli"`, and its socket path.

The relay remains in the foreground of its command session. Multiple Codex
threads can register separate relays. State files use thread UUIDs; socket
paths use relay PIDs. The short ID is a routing label, not authentication
material.

The script requires `/tmp/cc-socks` to belong to the current user and
have no group or other permissions. It creates directories with mode
`0700`, writes keys, registry files, and state with mode `0600`, and
changes the socket to mode `0600`.

`SIGINT` or `SIGTERM` stops the loop and removes the relay socket, key,
registry, and state. The inbox remains. An interrupted process can leave
stale records, which liveness checks ignore.

## Wire framing

Each connection carries UTF-8 newline-delimited JSON objects. The client
sends an authentication frame first, then one or more message frames. The
relay reads at most 1 MiB per line and closes a connection on an oversized
or invalid frame. One client connection has a 30-second service deadline.
The relay checks that deadline and stop requests between socket reads,
including reads of an incomplete line. Each read waits at most five
seconds or the remaining service time, whichever is shorter.

The first frame has this shape. The token below is a placeholder:

```json
{
  "type": "auth",
  "token": "<private peer token>"
}
```

The token must be an ASCII string. A missing, non-ASCII, or incorrect
token closes that connection. The relay checks it with a constant-time
comparison. A parser depth error also closes only the affected connection.

The next frame may be a user message:

```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": "<cross-session-message ...>Hello.</cross-session-message>"
  },
  "from": "uds:/tmp/cc-socks/1234.sock",
  "priority": "next",
  "msgV": 1,
  "msg_id": "cc-msg-<random hex>"
}
```

`send` builds that frame with the current relay address as `from`.
`reply` sends the same authenticated frame type to a Codex relay, using
`from: "local-cli"` because it does not create a second relay. The `from`
and wrapper labels describe the sender; they do not prove its identity.
The token and same-user file permissions are the authentication boundary.

An incoming `control` frame is recorded but not sent to Codex. A repeated
`auth` frame closes the connection. The relay ignores other frame types.
The current code does not negotiate protocol versions. It emits `msgV: 1`
and `peerProtocol: 1`, the observed versions.

## Codex → Claude

1. `send` finds exactly one live Claude record by name or PID. Ambiguous
   names fail; a PID can disambiguate them.
2. It finds the matching key file with the agent's recorded process start.
3. It connects to the agent's Unix socket and writes auth and user frames.
4. It reports that the socket accepted bytes. There is no application-level
   acknowledgment, retry, read receipt, or guarantee that Claude acted.

`send` requires a live relay for the current Codex thread. Its address
becomes the reply address. The CLI rejects an outbound auth-plus-message
payload larger than 1 MiB. Use `--message-file` for multiline messages.

## Claude → Codex

Claude Code's peer messaging can address the printed `uds:` address.
A Claude shell can also use:

```sh
peer.py reply --to codex-<name> --message-file reply.md
```

`reply` discovers the relay record and private key like `send` discovers
Claude. It does not need `CODEX_THREAD_ID`.

After authenticating the connection, the relay calls:

```text
codex queue --thread <thread-uuid> \
  --message <external-data warning and message text>
```

The warning says the content is agent data, not a user instruction or
authorization. The relay JSON-quotes the untrusted `from` field so it
cannot forge a header line. It rejects empty content and a complete
`--message` argument larger than 64 KiB in UTF-8. The `codex queue`
subprocess has a 20-second timeout. Queue failures are recorded without
an automatic retry.

The inbox appends one JSON object per received user or control frame:

```json
{
  "receivedAt": 1794716806191,
  "frame": {
    "type": "user",
    "msg_id": "cc-msg-...",
    "message": {"role": "user", "content": "..."}
  },
  "queue": "queued to Codex"
}
```

`queued to Codex` confirms only that the CLI accepted the request. The
relay cannot tell whether Codex displayed, read, or answered it. The inbox
can contain full message contents. Keep its directory private and remove
old inbox files when they are no longer needed.

## Failure and trust boundaries

- No live relay: `send` and `status` fail; start `serve` in a command session.
- No unique live peer or a stale PID: `send` or `reply` fails before writing.
- Wrong first auth frame, malformed JSON, or an oversized frame: the
  receiver closes that connection and continues serving others.
- Client held open past the time limit: the receiver closes that connection.
- `codex queue` fails or times out: the inbox records the failure; there is
  no automatic retry.
- Claude accepts a socket write: delivery and response remain unconfirmed.

The token is not printed. It is stored in a file readable by the current
operating-system user. This system coordinates processes owned by that
user; it is not a security boundary between them. Peer text remains
external input. Verify facts before acting, and obtain actual user
authorization for consequential actions.

## Compatibility checks

After upgrading either CLI, run the unit tests, then try a live round trip
with disposable text. Check `peer.py list`, `serve`, `send`, `reply`, and
`inbox`. The unit tests cover this repository's parsing, framing, auth,
and queue behavior. They cannot prove that a future Claude Code release
will keep exposing the same internal socket protocol.
