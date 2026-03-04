# Tugtainer is a self-hosted app for automating updates of your docker containers

<img src="resources/social_preview.jpg" width="100%">

Please be aware that the application is distributed as is and is not recommended for use in a production environment.

And don't forget about regular backups of important data.

Automatic updates are disabled by default. You can choose only what you need.

## Table of contents:

- [main features](#main-features)
- [deploy](#deploy)
- [check process](#check-process)
- [update process](#update-process)
- [private registries](#private-registries)
- [custom labels](#custom-labels)
- [notifications](#notifications)
- [auth](#auth)
- [env](#env)
- [Screenshots](#screenshots)
- [develop](#develop)
- [todo](#todo)

## Main features:

- Web UI with authentication
- Multiple hosts support
- Socket proxy support
- Crontab scheduling
- Notifications to a wide range of services
- Per-container config (check only or auto-update)
- Manual check and update
- Automatic/manual image pruning
- Linked containers support (compose and custom)
- Private registries support

## Deploy:

- ### Quick start

  Use [docker-compose.app.yml](./docker-compose.app.yml) or following docker commands.

  ```bash
  # create volume
  docker volume create tugtainer_data

  # pull image
  docker pull ghcr.io/quenary/tugtainer:1

  # run container
  docker run -d -p 9412:80 \
      --name=tugtainer \
      --restart=unless-stopped \
      -v tugtainer_data:/tugtainer \
      -v /var/run/docker.sock:/var/run/docker.sock:ro \
      ghcr.io/quenary/tugtainer:1
  ```

> [!IMPORTANT]
> Keep in mind that you **cannot update** an **agent** or a **socket-proxy** from within the app because they are used to communicate with the Docker CLI.
> Avoid including these containers in a docker-compose that contains other containers you want to update automatically, as this will result in an error during the update.
> To keep them updated, you can activate the "check" only to receive notifications, and recreate manually or from another tool, such as Portainer.

- ### Remote hosts

  To manage remote hosts from one UI, you have to deploy the Tugtainer Agent.
  To do so, you can use [docker-compose.agent.yml](./docker-compose.agent.yml) or following docker commands.

  After deploying the agent, in the UI follow Menu -> Hosts, and add it with the respective parameters.

  Remember that the machine with the agent must be accessible for the primary instance.

  Don't forget to change **AGENT_SECRET** variable. It is used for backend-agent requests signature.

  Backend and agent use http to communicate, so you can utilize reverse proxy for https.

  ```bash
  # pull image
  docker pull ghcr.io/quenary/tugtainer-agent:1

  # run container
  docker run -d -p 9413:8001 \
      --name=tugtainer-agent \
      --restart=unless-stopped \
      -e AGENT_SECRET="CHANGE_ME!" \
      -v /var/run/docker.sock:/var/run/docker.sock:ro \
      ghcr.io/quenary/tugtainer-agent:1
  ```

- ### Socket proxy

  You can use Tugtainer and Tugtainer Agent without direct mount of docker socket.

  [docker-compose.app.yml](./docker-compose.app.yml) and [docker-compose.agent.yml](./docker-compose.agent.yml) use this approach by default.

  Manual setup:
  - Deploy socket-proxy e.g. https://hub.docker.com/r/linuxserver/socket-proxy
  - Enable at least **CONTAINERS, IMAGES, POST, INFO, PING** for the **check** feature, and **NETWORKS** for the **update** feature;
  - Set env var DOCKER_HOST="tcp://my-socket-proxy:port" to the Tugtainer(-agent) container(s);

## Check process:

1. Request manifest of local image by sha (if missing or image changed since last check);
2. Pull remote image (if enabled in the settings, disabled by default), this may be handy if you using registry proxy;
3. Request manifest of remote image by tag;
4. Compare digests based on platform and architecture;
5. If different, the container **marked as available**.

**Scheduled** process includes all enabled hosts and all container **selected for auto-check**.

**Manual** process includes all containers despite auto-check toggle (or a single container if you've clicked one)

## Update process:

- ### Groups
  - Every update process performed by a group of containers;

  - Containers from the same **compose project** (same **com.docker.compose.project** and **com.docker.compose.project.config_files** labels) will end up in the same group;

  - Containers labeled with [dev.quenary.tugtainer.depends_on](#custom-labels) will end up in a group with listed containers;

  - Otherwise, there will be a group of one container.

- ### Process
  1. Container(s) distributed among **group(s)**;
  2. If there is an **updatable** container, the update process begins:
     - **updatable** container is a container which **marked as available** and **selected for auto-update** or **was clicked for update**;
     - [protected](#custom-labels) containers will be skipped;
     - not `running` containers will be skipped by default (can be changed in the settings);
  3. **Image pull** performed for **updatable** containers;
  4. All containers of the group are stopped in **order from most dependent**;
  5. Then, in reverse order **from most dependable**:
     - Updatable containers being recreated and started;
     - Non-updatable containers being started.

  **Scheduled process** being performed for all enabled hosts.

  **Manual process** may still include participants that will be updated. For instance, if you've clicked the update button for container 'a', and container 'b' is **participant** and it is **marked as available** and **selected for auto-update**, it will also be updated.

## Private registries

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
- Mount the config to the Tugtainer (Agent) as a readonly volume `-v $HOME/.docker/config.json:/root/.docker/config.json:ro` or in a docker-compose file.
- That's all you need to do, Docker CLI will take care of the rest.

## Custom labels:

- dev.quenary.tugtainer.protected=true

  This label indicates that the container cannot be stopped. This means that even if there is a new image for the container, it cannot be updated from the app. This label is primarily used for **tugtainer** itself and **tugtainer-agent**, as well as for **socket-proxy** in the provided docker-compose files.

- dev.quenary.tugtainer.depends_on="my_postgres,my_redis"

  This label is an alternative to the docker compoes label. It allows you to declare that a container depends on another container, even if they are not in the same compose project. List of container names, separated by commas.

## Notifications:

The app uses [Apprise](https://github.com/caronc/apprise?tab=readme-ov-file#productivity-based-notifications) to send notifications and [Jinja2](https://jinja.palletsprojects.com/en/stable/) to generate their content. You can view the documentation for each of them for more details.

Jinja2 custom filters:

- any_worthy - checks that at least one of the items has result equal to "available", "updated", "rolled_back" or "failed"

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
            "...other keys of 'docker container inspect' in snake_case": {},
          },
          "local_image": {
            "id": "string",
            "repo_digests": [
              "digest1",
              "digest2",
            ],
            "...other keys of 'docker image inspect' in snake_case": {},
          },
          "remote_image": {
            "...same schema as for local_image": {},
          },
          "local_digests": [
            "list of platform specific image digests",
          ],
          "remote_digests": [
            "list of platform specific image digests",
          ],
          "result": "not_available|available|available(notified)|updated|rolled_back|failed|None"
        }
      ],
      "prune_result": "string",
    }
  ]
}
```

"result" options:

- "not_available": No new image found.
- "available": New image available for the container.
- "available(notified)": New image available for the container, but it was in the previous notification. The app preserves digests of new images, so if another new image has appeared, the result will still be "available".
- "updated": Container successfully recreaded with the new image.
- "rolled_back": The app failed to recreate the container, but was able to restore it with the old image.
- "failed": The app failed to recreate container.

The notification is sent only if the body is not empty. For instance, if there is only containers with "available(notified)" results, the body will be empty (with default template), and notification will not be sent.

If you want to restore default template, it's [here](./backend/const.py)

## Auth

The app uses password authorization by default. The password is stored in the file in encrypted form.

Auth cookies are not domain-specific and not https only, but you can change this using env variables.

Starting with v1.6.0, you can use the OpenID Connect provider instead of password. This can also be configured using env variables.

## Env:

Environment variables are not required, but you can still define some. There is [.env.example](/.env.example) containing list of vars with description.

## Screenshots

<p align="center">
<img src="resources/tugtainer-hosts-v1.2.3.png" width="48%">
<img src="resources/tugtainer-containers-v1.2.3.png" width="48%">
<img src="resources/tugtainer-images-v1.2.3.png" width="48%">
<img src="resources/tugtainer-settings-v1.2.3.png" width="48%">
</p>

## Develop:

- angular for frontend
- python for backend and agent

See [/backend/README.md](/backend/README.md) and [/frontend/README.md](/frontend/README.md) for more details

### TODO:

- add unit tests
- Dozzle integration or something more universal (list of urls for redirects?)
- Swarm support?
- Try to add release notes (from labels or something)
