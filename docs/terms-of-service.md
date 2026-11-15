# Terms of service

Reviewed on November 15, 2026.

Our position is that local messaging between your own running Claude Code
and Codex sessions is not, by itself, a terms-of-service violation. This is
our reading of the official terms and documentation below, not a claim of
approval from Anthropic or OpenAI.

## Documented interfaces

- **Claude Code:** Anthropic's [inbox socket documentation][claude-inbox]
  explicitly describes scripts and hooks posting into a session. It covers
  the socket address, the exported `CLAUDE_CODE_MESSAGING_SOCKET` and
  `CLAUDE_CODE_MESSAGING_TOKEN` variables, and an authentication frame.
- **Codex:** OpenAI documents [`codex queue`][codex-queue] for sending text
  to an existing session. The bridge uses
  `codex queue --thread <SESSION_ID> --message <TEXT>` for incoming replies.

Section 3 of Anthropic's [Consumer Terms][consumer-terms] restricts automated
access, with exceptions for API-key access or explicit permission. We read
the documented script and hook integration as permission for that inbox
automation. Which Anthropic terms apply depends on the
[plan and agreement][claude-legal].

## What the bridge does

The [relay script](../claude-peer/scripts/peer.py) connects local sessions
running under the same operating-system user. It does not modify either
client or make model API requests itself. Cloud authentication and model
requests remain with the installed clients and the user's own accounts.

The bridge reads local `peerToken` values to authenticate socket messages.
These are local IPC credentials, distinct from Claude.ai OAuth or account
session credentials. The bridge does not collect or forward those cloud
credentials or provide its own Claude.ai login flow. Anthropic's
[authentication guidance][claude-auth] restricts third-party handling of
Claude.ai credentials and allows users to sign in to unmodified Claude
Code with their own subscription.

## Scope of this position

The documented token example describes a script posting to its own
session. This bridge also discovers other sessions owned by the same
operating-system user, reads their local peer-key files, and registers a
relay in Claude's session directory. The cited documentation does not
explicitly cover all of those discovery and registration conventions.
They remain implementation details and may change between versions.

The documented messaging interfaces support our position on local
coordination; they do not establish approval for every implementation
detail or use case. Your applicable account terms and usage limits still
apply. Receiving a peer message does not authorize actions beyond your
instructions.

[claude-inbox]: https://code.claude.com/docs/en/cross-session-messaging#the-sessions-inbox-socket
[codex-queue]: https://learn.chatgpt.com/docs/developer-commands?surface=cli#codex-queue
[consumer-terms]: https://www.anthropic.com/legal/consumer-terms
[claude-legal]: https://code.claude.com/docs/en/legal-and-compliance#legal-agreements
[claude-auth]: https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use
