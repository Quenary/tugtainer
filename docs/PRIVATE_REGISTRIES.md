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

`identitytoken` is the OAuth refresh token `docker login` writes for registries such as Azure Container Registry. When it is set, it is the only credential used for that registry. Image pull and Swarm service update send it in `X-Registry-Auth` as `identitytoken`. Registry checks exchange it at the Bearer realm with `grant_type=refresh_token` and `client_id=docker`, then use the access token. Username and password on the same entry are not sent. `identitytoken` works with Bearer-token registries; Basic-auth registries need username/password (`auth`).

Without `identitytoken`, image pull and Swarm service update send `username`, `password`, and `serveraddress`. Registry checks send that `auth` value as Basic, or use it to obtain a Bearer token.

`credsStore` and `credHelpers` are not supported: the image does not include credential-helper binaries. A config that sets them logs a warning, and only inline `auths` entries are used.
