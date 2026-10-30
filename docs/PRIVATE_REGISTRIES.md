# Private registries

A private image is pulled with the Docker config of the app or the agent that owns that container.

The config is created on the host with `docker login <registry>`, or written by hand:

```json
{
  "auths": {
    "<registry>": {
      "auth": "base64 encoded 'username:password_or_token'"
    }
  }
}
```

It is mounted read-only, for example `-v $HOME/.docker/config.json:/root/.docker/config.json:ro`. The Docker CLI then authenticates on pull.
