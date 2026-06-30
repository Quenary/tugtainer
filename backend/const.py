from ipaddress import ip_network

TUGTAINER_DEPENDS_ON_LABEL = "dev.quenary.tugtainer.depends_on"
TUGTAINER_PROTECTED_LABEL = "dev.quenary.tugtainer.protected"
DOCKER_COMPOSE_DEPENDS_ON_LABEL = "com.docker.compose.depends_on"
DEFAULT_NOTIFICATION_TEMPLATE = """\
{% set groups = {
  "updated": "Updated",
  "available": "Available",
  "rolled_back": "Rolled-back",
  "failed": "Failed"
} %}
\
{% for r in results if r.items | any_worthy %}
## Host: {{r.host_name}}
\
{% for status, title in groups.items() %}
  {% set items = r.items | selectattr('result', 'equalto', status) | list %}
  {% if items %}
### {{ title }}:
    {% for item in items %}
- {{item.container.name}} {{item.container.config.image}}
    {% endfor %}
  {% endif %}
{% endfor %}
\
{% if r.prune_result %}
{% set lines = [] %}
{% for line in r.prune_result.split('\n') %}
    {% set stripped = line.strip() %}
    {% if stripped %}
        {% set _ = lines.append(stripped) %}
    {% endif %}
{% endfor %}
{% set res = lines[-1] if lines else None %}
{% if res %}
{{res}}
{% endif %}
{% endif %}

{% endfor %}
"""
RESTRICTED_NETWORKS = {
    # IPv4 Loopback and Local Host
    ip_network("127.0.0.0/8"),  # IPv4 loopback addresses (localhost)
    ip_network(
        "0.0.0.0/8"
    ),  # Current network (only valid as source, but can map to localhost in Linux)
    # IPv4 Private Networks (RFC 1918)
    ip_network("10.0.0.0/8"),  # Private network A
    ip_network("172.16.0.0/12"),  # Private network B
    ip_network("192.168.0.0/16"),  # Private network C
    # IPv4 Link-Local & Carrier-Grade NAT
    ip_network("169.254.0.0/16"),  # IPv4 Link-Local
    ip_network("100.64.0.0/10"),  # Carrier-Grade NAT
    # Broadcast & Documentation
    ip_network("224.0.0.0/4"),  # IPv4 Multicast
    ip_network("240.0.0.0/4"),  # IPv4 Reserved / Reserved for future use
    ip_network("255.255.255.255/32"),  # IPv4 Limited Broadcast
    # IPv6 Loopback and Unspecified
    ip_network("::1/128"),  # IPv6 loopback address (localhost)
    ip_network("::/128"),  # IPv6 unspecified address
    # IPv6 Private & Link-Local
    ip_network("fc00::/7"),  # IPv6 Unique Local Addresses (ULA)
    ip_network("fe80::/10"),  # IPv6 Link-Local Unicast
    # IPv6 Transition & Mapped Addresses
    ip_network("::ffff:0:0/96"),  # IPv4-mapped IPv6 addresses (e.g., ::ffff:127.0.0.1)
    ip_network("2002::/16"),  # 6to4 transition mechanism
    # IPv6 Documentation & Discard
    ip_network("2001:db8::/32"),  # IPv6 Documentation addresses
    ip_network("100::/64"),  # IPv6 Discard-only prefix
}
