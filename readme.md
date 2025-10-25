# Tugtainer is a self-hosted app for automating updates of your docker containers

It's like well-known [watchtower](https://github.com/containrrr/watchtower), but with a web UI where you can change most of the settings or view the current state of the containers.

<p align="center">
<img src="resources/tugtainer-hosts-v1.2.3.png" width="90%">
<img src="resources/tugtainer-containers-v1.2.3.png" width="30%">
<img src="resources/tugtainer-images-v1.2.3.png" width="30%">
<img src="resources/tugtainer-settings-v1.2.3.png" width="30%">
</p>

Please be aware that the application is distributed as is and is not recommended for use in a production environment.

And don't forget about regular backups of important data.

Automatic updates are disabled by default. You can choose only what you need.

## Main features:

- Web UI with authentication
- Socket proxy support
- Multiple hosts support
- Crontab scheduling
- Notifications to a wide range of services
- Per-container config (check only or auto-update)
- Manual check and update
- Automatic/manual image pruning
- Compose support (sort of, read Check/update section)

## Deploy:

- ### Quick start

  ```bash
  # create volume
  docker volume create tugtainer_data

  # pull image
  docker pull quenary/tugtainer:latest

  # run container
  docker run -d -p 9412:80 \
      --name=tugtainer \
      --restart=unless-stopped \
      -v tugtainer_data:/tugtainer \
      -v /var/run/docker.sock:/var/run/docker.sock \
      quenary/tugtainer:latest
  ```

- ### Remote Hosts / Proxy socket

  - SSH:

  ```bash
  # Mount ssh key to the container
  # Don't forget to add known hosts (ssh to remote at least once).
  docker run -d -p 9412:80 \
      --name=tugtainer \
      --restart=unless-stopped \
      -v tugtainer_data:/tugtainer \
      -v ~/.ssh:/root/.ssh:ro \
      quenary/tugtainer:latest

  # And create a host in the UI with
  HOST: ssh://my-user@my-host
  ```

  - Socket proxy:

  ```bash
  # Create socket proxy container, e.g. https://hub.docker.com/r/linuxserver/socket-proxy
  # Of course, you should remember not to update proxy container from the app.
  # Enable at least CONTAINERS, IMAGES, POST, INFO, PING for the check feature, and NETWORKS for the update feature.

  # Run the app with only the data volume.
  docker run -d -p 9412:80 \
      --name=tugtainer \
      --restart=unless-stopped \
      -v tugtainer_data:/tugtainer \
      quenary/tugtainer:latest

  # And create a host in the UI with
  HOST: tcp://my-socket-proxy:my-port
  ```

  - Combine ssh tunnel and socket proxy:

  ```bash
  # Create persistent tunnel outside the container.
  autossh -M 0 -f -N -L 23750:127.0.0.1:2375 \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3 \
    my-user@my-host

  # Run the app with only the data volume.
  docker run -d -p 9412:80 \
    --name=tugtainer \
    --restart=unless-stopped \
    -v tugtainer_data:/tugtainer \
    quenary/tugtainer:latest

  # And create a host in the UI with
  HOST: tcp://127.0.0.1:23750
  ```

  - TLS:
    You can try to utilize a tls certificates if you wish. In this case you have to mount ca/cert/key to the container and specify appropriate paths in the UI

## Check/update process:

- ### Groups
  Every check/update process performed by a group of containers. It's not some fancy term, but just that some containers will be grouped together. For now, this only applies to the valid compose projects. Containers with the same 'com.docker.compose.project' label will be grouped and processed together. Otherwise, there will be a group of one container. In future, i plan to add custom dependency label or an UI setting to link containers together (even if they are not in the same project).

- ### Actual process
  - **Image pull** performed for containers marked for **check**;
  - If there are a **new image** for any group's container and it is **marked for auto-update**, the update process begins;
  - After that, all containers in the group are stopped in **order from most dependent**;
  - Then, **in reverse order** (from most dependable):
      - Updatable containers being recreated and started;
      - Non-updatable containers being started;

- ### Scheduled:
  - For each **host defined in the UI**, the check/update process starts at time specified in the settings;
  - All containers of the host are distributed among **groups**;
  - Each container in the group receives an **action based on your selection in the UI** (check/update/none);
  - *Actual process*

- ### Click of check/update button:
  - **The container** (and **possible participants** from compose) added to a group;
  - **The container** receives an action based on the button you've clicked (check or update);
  - **Other possible participants** receives an **action based on your selection in the UI**. For instance, if you've clicked the update button for container 'a', and container 'b' is **participant** and it is **marked for auto-update** and there is **new image** for it, **it will also be updated**.
  - *Actual process*

## Env:

Environment variables are not required, but you can still define some. There is [.env.example](/.env.example) containing list of vars with description.

## Develop:

- angular for frontend
- python for backend
- there are a readme files in corresponding directories

### TODO:

- add unit tests
- filter cont in notification (dont notify already notified)
- Dozzle integration or something more universal (list of urls for redirects?)
- Swarm support?
- Try to add release notes (from labels or something)
- Remove unused deps
