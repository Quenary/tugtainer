# Private registries

To use private registries, you have to mount docker config to Tugtainer or Tugtainer Agent, depending on where the container with the private image is located.

- Create the config using one of the methods on the host machine
  - Log into the registry `docker login <registry>`
  - Manually
  ```json
  {
    "auths": {
      "<registry>": {
        "auth": "base64 encoded 'username:password_or_token'"
      }
    }
  }
  ```
- Mount the config to the Tugtainer (Agent) as a read-only volume `-v $HOME/.docker/config.json:/root/.docker/config.json:ro` or in a docker-compose file.
- That's all you need to do, Docker CLI will take care of the rest.
