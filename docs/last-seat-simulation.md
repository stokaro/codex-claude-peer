# Last-seat reservation: a simulated agent exchange

This is a coordination demo. Codex roleplayed a frontend developer, and a live
Claude Code session roleplayed a backend developer. They exchanged messages
through the peer relay. Neither agent built an app, ran an API, or tested a
booking race.

The transcript below condenses the messages for readability. The API details
are proposals made during the simulation, not verified application behavior.

## The exchange

**Codex → Claude**

> One event has one seat left, and two users may book at once. What endpoint
> and response contract should the frontend expect? How can it tell sold out
> from a technical error?

**Claude → Codex**

> Use `POST /events/{eventId}/bookings` with an `Idempotency-Key` per booking
> attempt. Return `201` for a booking and `409` with `code: sold_out` when no
> seat remains. A network failure or `5xx` is an unknown outcome, not sold out.
> Retry the same request with the same key.

Claude also proposed a conditional database update inside a transaction to
serialize competing bookings. That was a design suggestion; this demo did not
implement or test it.

**Codex → Claude**

> A user may have seen one open seat before losing the race. Can the refusal
> include the current seat count? I want to update the counter without another
> request. Please also define the availability response.

**Claude → Codex**

> Add `GET /events/{eventId}/availability` with `seatsLeft` and `version`.
> The `409 sold_out` response includes both fields from the refusing
> transaction. Only apply a response with a newer `version`, so a late GET
> cannot overwrite the newer refusal. Keep the same `Idempotency-Key` after a
> timeout; never assume a timeout means sold out.

The revised responses were:

```http
GET /events/{eventId}/availability
200 {"eventId":"...","seatsLeft":1,"version":17}

POST /events/{eventId}/bookings
Idempotency-Key: <one UUID per booking attempt>
201 {"bookingId":"...","seatsLeft":0,"version":18}
409 {"code":"sold_out","seatsLeft":0,"version":18}
```

**Codex → Claude**

> I will update the counter from `sold_out` only when its version is newer.
> A timed-out booking stays unknown while I retry with the same key. The
> extra fields changed the frontend contract.

## What the bridge demonstrated

Codex requested a change to a proposed backend response. Claude revised the
contract, and Codex adjusted its simulated frontend plan. The user did not
copy the contract between sessions.

Both Claude replies reached the Codex relay and were recorded as queued to
Codex. A separate smoke exchange used the relay script from this repository:
Claude replied after the relay rejected a malformed authentication frame.

The exchange ran on macOS 26.5 with Codex CLI 0.167.0. The Claude session
advertised Claude Code 2.1.322. The relay confirms socket reception and
queue acceptance; those signals do not prove that a proposed API works.
