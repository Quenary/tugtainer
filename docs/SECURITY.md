# Security policy

Tugtainer is a **self-hosted, single-operator** tool. It is distributed as-is
and is not intended for multi-tenant or untrusted-network use. Please read
this page before opening a security advisory.

## Threat model

- The instance runs on a **trusted network**, operated by one admin.
- There is **one privilege level**: an authenticated admin (`is_authorized`).
  There is no separate low-privilege role.
- That admin can already manage Docker through the product (start, stop,
  recreate, pull, inspect, logs), including via the documented socket-proxy
  setup. Reaching the Docker Engine is not a privilege jump.
- Settings such as notification URLs, remote agent URLs, and hooks are
  **admin-only**. An attacker who can change them already has the session.

Reports are judged against this model, not against a public multi-tenant SaaS.

## In scope

- Unauthenticated access to privileged API or data
- Authentication / authorization bypass
- Agent request-forgery when `ALLOW_UNAUTHENTICATED_AGENT` is false
- Secret leakage to unauthenticated callers
- Issues that affect an operator who did **not** opt into a risky setting

## Out of scope

These are not treated as vulnerabilities (and will not be accepted as High):

- Anything that requires an authenticated admin to paste an
  attacker-controlled URL, hostname, or shell command
- SSRF or DNS rebinding from **admin-configured** notification URLs
- Reaching Docker, socket-proxy, or link-local / metadata addresses from
  those URLs — the same admin already has equivalent access in the UI
- Lab setups that replace the container's DNS resolver (for example
  `docker run --dns=…`) to demonstrate a rebind
- Hooks executing the commands the admin configured (`ALLOW_HOOKS` /
  `ALLOW_EXEC` are opt-in by design)
- Default cookie flags (`HTTPS`, `DOMAIN`) that the operator can tighten
- Issues that exist only with explicit opt-outs (`DISABLE_AUTH`,
  `ALLOW_UNAUTHENTICATED_AGENT`, `ENABLE_PUBLIC_API`)

## Known limitations

### Notification URLs

The app uses [Apprise](https://github.com/caronc/apprise). Private and
reserved destinations are blocked with a **best-effort** check. See
[Notifications](./NOTIFICATIONS.md).

That check does **not** cover DNS rebinding (TOCTOU between the validator's
lookup and Apprise's own connect-time lookup). It is meant to stop obvious
mistakes such as `json://socket-proxy:2375`, not to be a hard guarantee.

Resolved IPs are **not** pinned through Apprise:

- Many Apprise URLs are not HTTP(S) URIs and have no host that can be
  pinned (`tgram://…`, `discord://…`, SMTP, and similar). The URL “host”
  is often a token; the client talks to a fixed public API.
- If a URL cannot be parsed or resolved, the SSRF check is skipped rather
  than breaking those services.
- Even for `json(s)://` / `xml://` / `form://`, rewriting the host to an IP
  breaks TLS (certificate + SNI) and virtual hosts. Apprise does not expose
  “connect to this IP, keep this Host/SNI”.

A stricter setup can set `NOTIFICATION_ALLOW_SCHEMES` (for example
`tgram,discord,ntfy`) and avoid arbitrary `json` / `http` webhooks.

### Agent host URLs

The same best-effort private/reserved check applies to remote agent URLs.
Allow a LAN or Docker network with `AGENT_ALLOW_NETWORKS` and/or
`AGENT_ALLOW_ENDPOINTS`. See [.env.example](../.env.example).

## Severity

CVSS will be scored against this threat model.

- **PR:H** when only the authenticated admin can trigger the issue
- Confidentiality / Integrity are **not High** when the impact is something
  the instance owner can already do through the intended UI
- A generic “SSRF to Docker / metadata = High” template does not apply here

## Reporting

Please report privately (GitHub Security Advisory), not as a public issue.

Include a realistic exploit path under this threat model: who is
authenticated, which setting they control, and what they gain **beyond**
what the admin UI already allows.

Thanks for taking the time to read this first.
