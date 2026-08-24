# Notifications

Tugtainer uses [Apprise](https://github.com/caronc/apprise?tab=readme-ov-file#productivity-based-notifications) to send notifications and [Jinja2](https://jinja.palletsprojects.com/en/stable/) to render their content. See each project's documentation for details.

> Notification URLs that resolve to private or reserved networks are blocked by default (best-effort SSRF protection). See [.env.example](../.env.example) and the [security policy](./SECURITY.md).

Jinja2 custom filters:

- `any_worthy` — returns true if at least one item has a result of `available`, `updated`, `rolled_back`, or `failed`

Jinja2 context schema:

```json
{
  "hostname": "Tugtainer container hostname",
  "results": [
    {
      "host_id": 0,
      "host_name": "string",
      "items": [
        {
          "container": {
            "id": "string",
            "image": "string",
            "...other docker container inspect keys, in snake_case": {},
          },
          "local_image": {
            "id": "string",
            "repo_digests": [
              "digest1",
              "digest2",
            ],
            "...other docker image inspect keys, in snake_case": {},
          },
          "remote_image": {
            "...same schema as local_image": {},
          },
          "local_digests": [
            "platform-specific image digests",
          ],
          "remote_digests": [
            "platform-specific image digests",
          ],
          "previous_image_digests": [
            "digests of the image the container was running before the update",
          ],
          "previous_image_tags": [
            "tags of the image the container was running before the update",
          ],
          "previous_image_version": "version from the previous image labels, or None",
          "result": "not_available|available|available(notified)|updated|rolled_back|failed|None"
        }
      ],
      "prune_result": "string",
    }
  ]
}
```

`result` values:

- `not_available`: No new image was found.
- `available`: A new image is available for the container.
- `available(notified)`: A new image is available, but the same image was already included in a previous notification. Tugtainer keeps the digests of newly detected images, so the result stays `available` if a different new image appears.
- `updated`: The container was successfully recreated with the new image.
- `rolled_back`: Tugtainer failed to recreate the container, but restored it using the previous image.
- `failed`: Tugtainer failed to recreate the container.

A notification is sent only when the body is not empty. For example, if every container has an `available(notified)` result, the default template produces an empty body and no notification is sent.

The default template is defined in [backend/const.py](../backend/const.py).
