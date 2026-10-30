# Security policy

Tugtainer is a self-hosted, single-operator tool. It is distributed as-is and is not a multi-tenant service. A GitHub Security Advisory is accepted only when it beats the threat model below. A report that does not is closed.

## Threat model

The instance runs on a trusted network and has one operator.

There is one privilege level: an authenticated admin (`is_authorized`). There is no separate low-privilege role and no cross-user boundary.

That admin can already manage Docker through the product (start, stop, recreate, pull, inspect, logs), including through the socket-proxy. Reaching the Docker Engine is not a privilege jump.

Notification URLs, remote agent URLs, and hooks are admin-only settings. A caller who can change them already holds the session and can already do what those settings do.

Reports are judged against this model. They are not judged against a public multi-tenant service.

## In scope

- Unauthenticated access to a privileged API or to data
- Authentication or authorization bypass
- Agent request forgery when `ALLOW_UNAUTHENTICATED_AGENT` is false
- Secret leakage to an unauthenticated caller
- An issue that affects an operator who did not opt into the risky setting

## Out of scope

These are not vulnerabilities and are not accepted as High or Critical:

- A report that needs an authenticated admin to paste an attacker-controlled URL, hostname, or shell command
- SSRF or DNS rebinding through an admin-configured notification URL or remote agent URL
- Reaching Docker, the socket-proxy, or a link-local or metadata address from those URLs
- A lab DNS resolver (`docker run --dns=…`) used to demonstrate a rebind
- Hooks running the commands the admin configured (`ALLOW_HOOKS` and `ALLOW_EXEC` are opt-in)
- Default cookie flags (`HTTPS`, `DOMAIN`) and CORS (`ALLOW_ORIGINS`), which the operator can tighten
- Behavior that exists only with `DISABLE_AUTH`, `ALLOW_UNAUTHENTICATED_AGENT`, or `ENABLE_PUBLIC_API`
- A score that treats "SSRF to Docker or metadata" as High without a gain beyond the admin UI

## Known limitations

### Notification URLs

[Apprise](https://github.com/caronc/apprise) delivers notifications. Private and reserved destinations are blocked with a best-effort check. See [Notifications](./NOTIFICATIONS.md). Literal IPv4 hosts are canonicalized the same way the libc stack does, including decimal, octal, hex, and short forms, before that check.

The check does not cover DNS rebinding between validation and Apprise's own connect. It stops an obvious mistake such as `json://socket-proxy:2375`. It is not a hard boundary, and a report of that gap is out of scope.

Resolved addresses are not pinned through Apprise:

- Many URLs are not HTTP(S) and have no host to pin (`tgram://…`, `discord://…`, SMTP, and similar). The URL host is often a token, and the client talks to a fixed public API.
- A URL that cannot be parsed or resolved skips the check, so those services keep working.
- Rewriting an HTTP webhook host to an IP breaks TLS and virtual hosts. Apprise does not expose "connect to this address, keep this hostname".

`NOTIFICATION_ALLOW_SCHEMES` (for example `tgram,discord,ntfy`) limits schemes and avoids arbitrary `json` or `http` webhooks.

### Agent host URLs

Remote agent URLs use the same private and reserved check. A LAN or Docker network is allowed with `AGENT_ALLOW_NETWORKS` and/or `AGENT_ALLOW_ENDPOINTS`. See [.env.example](../.env.example).

Agent requests are plain HTTP(S). The client resolves the name, applies the check, and connects only to the addresses that passed. The original hostname stays on the `Host` header, TLS SNI, and certificate verification.

This is not a boundary against a malicious admin-supplied hostname. An admin who can set the URL already controls the session and Docker.

## Severity

CVSS is scored against this threat model.

- **PR:H** when only the authenticated admin can trigger the issue
- Confidentiality and integrity are not High when the impact is something the operator can already do in the UI
- Critical or High requires unauthenticated access, an authentication bypass, or a gain the admin UI does not already provide

## Reporting

Reports go through a GitHub Security Advisory, not a public issue.

A report states who is authenticated, which setting they control, and what they gain beyond the admin UI. A report that does not show that gain is out of scope.
