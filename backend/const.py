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
{% if r.prune_res %}
{{r.prune_res}}
{% endif %}

{% endfor %}
"""
