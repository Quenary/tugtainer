# Private registries

A private image is pulled with the Docker config of the app or the agent that owns that container.

`config.json` is mounted read-only, for example `-v $HOME/.docker/config.json:/root/.docker/config.json:ro`. The default directory is `~/.docker`. `DOCKER_CONFIG` overrides it.

Supported `auths` entry:

```json
{
  "auths": {
    "ghcr.io": {
      "auth": "base64 encoded username:password_or_token"
    }
  }
}
```

`username` and `password` fields are also accepted. A key may be a host, `host:port`, or a URL such as `https://index.docker.io/v1/`. Docker Hub aliases (`docker.io`, `index.docker.io`, `registry-1.docker.io`) match each other.

Image pull and Swarm service update send those credentials in the `X-Registry-Auth` header (`username`, `password`, `serveraddress`).

`credsStore` and `credHelpers` are not supported: the image does not include credential-helper binaries. A config that sets them logs a warning, and only inline `auths` entries are used.
