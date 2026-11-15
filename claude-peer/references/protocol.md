# Local peer protocol

This document describes the protocol implemented by `claude-peer/scripts/peer.py`. It records an **observed** Claude Code local socket interface and the currently installed Codex `queue` command. It is not an official or stable Claude Code protocol specification.

## Participants and addresses

| Participant | Address or record | Purpose |
| --- | --- | --- |
| Claude Code agent | `~/.claude/sessions/<pid>.json` | Name, PID, process start time, status, socket path, and Claude version. |
| Claude peer key | `~/.claude/sessions/<pid>.<sha256(socket-path)>.key` | Private `peerToken` and process start time. |
| Codex relay | `/tmp/cc-socks/<pid>.sock` | Receives frames for one Codex thread. Its temporary record and key use the same Claude session directory. |
| Relay state | `/tmp/codex-claude-peer-state-<uid>/<thread-uuid>.json` | Maps a Codex thread to its live relay PID, socket, and process start time. |
| Relay inbox | `/tmp/codex-claude-peer-state-<uid>/<thread-uuid>.inbox.jsonl` | Records incoming non-auth frames and the result of queueing them. |

All sockets use Unix domain streams. There is no TCP transport or remote peer discovery. `peer.py list` shows Claude records with a `version` field; `list --include-codex` also shows temporary relay records with `peerProtocol: 1` and no Claude version.

A record is considered live only if its PID has the recorded process start time and the socket exists. This guards against PID reuse. Listing can use `lsof` as a fallback if `ps` cannot read a start time. `send`, `reply`, and `status` require the normal process start check; a sandbox that blocks `ps` may require an escalated read of the local process table.

## Registration and lifecycle

`serve --thread <uuid>` creates the socket under `/tmp/cc-socks`, writes a random 128-bit peer token to a private key file, writes a Claude-shaped session record, and writes the thread state. The record's `name` is `codex-` plus an 11-character URL-safe random ID. The relay checks existing names before using one. It advertises `peerProtocol: 1`, `kind: "bg"`, `entrypoint: "cli"`, and the socket path. The relay stays in the foreground of its command session. Multiple Codex threads can register separate relays at the same time; the state file is keyed by thread UUID and each socket is keyed by its relay PID. The short ID is a routing label, not authentication material.

The script requires `/tmp/cc-socks` to belong to the current user and have no group or other permissions. It creates directories with mode `0700`, writes the key, registry, and state files with mode `0600`, and changes the socket to mode `0600`. `SIGINT` or `SIGTERM` stops the loop and removes the relay socket, key, registry, and state. The inbox is retained. An interrupted process can leave stale records; liveness checks ignore them.

## Wire framing

Each connection carries UTF-8, newline-delimited JSON objects. A client must send the authentication frame first, followed by one or more message frames. The relay reads at most 1 MiB per line and closes a connection on an oversized or invalid frame. The socket operation has a five-second timeout.

The first frame has this shape; the token value below is a placeholder:

```json
{"type":"auth","token":"<private peer token>"}
```

The next frame may be a user message:

```json
{"type":"user","message":{"role":"user","content":"<cross-session-message from=\"uds:/tmp/cc-socks/1234.sock\" from-name=\"Codex\" from-mode=\"default\">\nHello.\n</cross-session-message>"},"from":"uds:/tmp/cc-socks/1234.sock","priority":"next","msgV":1,"msg_id":"cc-msg-<random hex>"}
```

`send` builds that frame with the current relay's address as `from` and a `cc-msg-` identifier. `reply` sends the same authenticated frame type to a Codex relay, using `from: "local-cli"` and a `local-cli` wrapper because it does not create a second relay. The `from` and wrapper labels describe the sender but do **not** prove its identity. The peer token and same-user file permissions are the authentication boundary.

An incoming `control` frame is recorded but not sent to Codex. A repeated `auth` frame closes the connection. The relay ignores other frame types. The current code does not negotiate protocol versions; it emits `msgV: 1` and `peerProtocol: 1` because those are the observed versions.

## Codex → Claude

1. `send` looks up exactly one live Claude record by name or PID. Ambiguous names fail; a PID can disambiguate them.
2. It finds the matching key file whose recorded process start time equals the agent's start time.
3. It connects to the agent's Unix socket and writes the auth and user frames.
4. It reports that the socket accepted the bytes. There is no application-level acknowledgment, retry, read receipt, or guarantee that Claude acted on the message.

`send` requires a live relay for the current Codex thread because its socket address becomes the reply address. The CLI conservatively rejects an outbound auth-plus-message payload larger than 1 MiB. For multiline messages, prefer `--message-file` so shell quoting does not alter the text.

## Claude → Codex

Claude Code's peer messaging can address the relay's printed `uds:` address. A Claude shell can also use `reply --to codex-<prefix> --message-file reply.md`; the `reply` command discovers the relay record and private key in the same way as `send` discovers Claude. It does not need `CODEX_THREAD_ID`.

After authenticating the connection, the relay calls:

```text
codex queue --thread <thread-uuid> --message <external-data warning and message text>
```

The warning states that the content is agent data, not a user instruction or authorization. The relay JSON-quotes the untrusted `from` field before placing it in the warning so it cannot add a forged header line. It rejects empty content and content longer than 100,000 characters. The `codex queue` subprocess has a 20-second timeout. Queue failures are recorded and are not retried.

The inbox appends one JSON object per received user or control frame:

```json
{"receivedAt":1794716806191,"frame":{"type":"user","msg_id":"cc-msg-...","message":{"role":"user","content":"..."}},"queue":"queued to Codex"}
```

`queued to Codex` confirms only that the CLI accepted the request. The relay does not know whether Codex has displayed, read, or answered it. The inbox can contain full message contents, so keep its directory private and remove old inbox files when they are no longer needed.

## Failure and trust boundaries

| Condition | Behavior |
| --- | --- |
| No live relay for the selected Codex thread | `send` and `status` fail; start `serve` in a command session. |
| No matching live peer, ambiguous name, or stale PID | `send` or `reply` fails before writing a frame. |
| Missing or wrong first auth frame | Receiver closes the connection without calling `codex queue`. |
| Invalid JSON or frame over 1 MiB | Receiver closes the connection. |
| `codex queue` exits nonzero or times out | Failure is recorded in the inbox; no automatic retry. |
| Claude accepts a socket write | Delivery and response are still unconfirmed. |

The token is not printed. It is stored in a file readable by the current operating-system user. This system is appropriate for coordination between processes owned by that user; it is not a security boundary between those processes. Peer text is always external input. Verify facts before acting, and obtain actual user authorization for consequential actions.

## Compatibility checks

After upgrading either CLI, run `python3 -m unittest discover -s tests -v`, then test a live round trip with disposable text. Check `peer.py list`, `serve`, `send`, `reply`, and `inbox`. The unit tests prove this repository's parsing, framing, authentication, and queue behavior; they do not prove that a future Claude Code release will continue exposing the same internal socket protocol.
