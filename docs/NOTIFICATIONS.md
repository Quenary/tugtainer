# Notifications

Job results go out through [Apprise](https://github.com/caronc/apprise). The body is a [Jinja2](https://jinja.palletsprojects.com/en/stable/) template. A notification is sent only when the rendered body is not empty.

Notification URLs that resolve to private or reserved networks are blocked by default. The check is best-effort. See [Security](./SECURITY.md) and [.env.example](../.env.example).

The template receives this context. Inspect objects expose the Docker inspect fields in snake_case. `item.name` and `item.image` exist on both a container item and a service item.

```json
{
  "hostname": "hostname of the app container",
  "results": [
    {
      "host_id": 0,
      "host_name": "string",
      "items": [
        {
          "container": { "id": "string", "image": "string" },
          "local_image": { "id": "string", "repo_digests": ["digest"] },
          "remote_image": { "id": "string" },
          "local_digests": ["platform-specific digests of the running image"],
          "remote_digests": ["platform-specific digests from the registry"],
          "previous_image_digests": ["repo digests of the image before a successful update"],
          "previous_image_tags": ["tags of that image"],
          "previous_image_version": "version label of that image, or null",
          "current_version": "version label of the running image, or null",
          "available_version": "version label of the pending image, or null",
          "available_created": "build time of the pending image, or null",
          "result": "not_available | available | available(notified) | updated | rolled_back | failed | null"
        }
      ],
      "prune_result": "string or null"
    }
  ]
}
```

A Swarm service item has no `container` and no `previous_image_*`. It has `service_name`, `service_image`, `service_id`, `local_image`, `remote_image`, `local_digests`, `remote_digests`, `current_version`, `available_version`, `available_created`, and `result`. `local_image` and `remote_image` are null when that image was not inspected.

`previous_image_*` is filled only after a successful container update. See [Previous image](./CHECK_AND_UPDATE.md#previous-image). `result` is null when the registry lookup failed; the previous availability is kept and the item is not reported as up to date.

| `result` | Meaning |
| --- | --- |
| `not_available` | No new image. |
| `available` | A new image is available. |
| `available(notified)` | That same new image was already included in an earlier notification. A different new image stays `available`. |
| `updated` | The container was recreated with the new image. |
| `rolled_back` | Recreate failed and the previous image was restored. |
| `failed` | Recreate failed. |
| `null` | The registry lookup failed. |

The filter `any_worthy` is true when any item is `available`, `updated`, `rolled_back`, or `failed`. The built-in default template renders an empty body when no item is one of those, so nothing is sent. When `available_version` is set, the default template includes it, and `current_version -> available_version` when the running image has a version label. A template saved in settings is left as-is. The default lives in `backend/const.py`.

## Health monitor

A separate template runs when health monitoring reports containers. The context is one host name mapped to the containers in that report:

```json
{
  "groups": {
    "<host_name>": [
      {
        "container": { "id": "string", "name": "string" },
        "status": "unhealthy | healthy"
      }
    ]
  }
}
```

`unhealthy` is sent once the notify threshold is reached. `healthy` is the recovery report, and only when an unhealthy notification was already sent for that container. A `starting` status is stored in history and is not part of this context. See [Healthcheck monitoring](./HEALTHCHECK_MONITOR.md).
