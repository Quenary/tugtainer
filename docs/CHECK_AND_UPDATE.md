# Check and update process

## Check process

1. Verify that a container is suitable for checking (not a local image);
2. Pull image (if enabled in the settings, disabled by default), this may be handy if you are using a registry proxy;
3. Request current digest of an image from a registry;
4. Compare digests;
5. If different, the container is **marked as available**.

**Scheduled** process includes all enabled hosts and all containers **selected for auto-check**.

**Manual** process includes all containers despite the auto-check toggle (or a single container if you've clicked one).

## Update process

- ### Dependency graph
  - Containers of a host are processed as a single set;
  - A dependency graph is built for that host from:
    - Compose dependencies (`com.docker.compose.depends_on` for containers with the same `com.docker.compose.project` and `com.docker.compose.project.config_files`)
    - Custom dependencies ([dev.quenary.tugtainer.depends_on](../README.md#custom-labels))
  - Dependencies are directional: if container A depends on B, B is started before A and stopped after A;
  - Containers without dependencies are treated as independent nodes

- ### Process
  1. The dependency graph is built:
     - [protected](../README.md#custom-labels) containers are skipped;
     - not `running` containers are skipped by default (can be changed in the settings);
  2. A set of **updatable** containers is calculated:
     - an updatable container has an **available** update and is either **selected for auto-update** or included by a **manual** run;
  3. A set of **affected** containers is calculated:
     - includes all containers that depend (directly or transitively) on any updatable container;
     - excludes the updatable containers themselves;
  4. A topological execution order is built from the dependency graph;
  5. Images are pulled for **updatable** containers;
  6. All involved containers (**updatable** and **affected**) that were running are stopped once, from most dependent to least dependent;
  7. Then, in reverse order (least dependent → most dependent):
     - **Updatable** containers are recreated and started;
     - **Affected** containers are started;
  8. After start, healthchecks are waited on; if an updatable container becomes unhealthy, it is rolled back to the previous image.

**Scheduled** process runs on all enabled hosts for containers **selected for auto-update**.

**Manual** process updates all containers with an available update despite the auto-update toggle (or a single container if you've clicked one), including their affected dependents.

Optional [hooks](../README.md#hooks) can run around stop, update, and rollback when enabled.

## Update delay

Optional delay between detecting a new image and applying a **scheduled** update (security buffer while a bad release can be yanked or fixed).

- Global setting `DELAY_UPDATE_FOR` (seconds, default `0` = no delay);
- Per-container `delay_update_for` overrides the global value when set; otherwise the global setting is used;
- When remote digests change, `remote_digests_changed_at` is updated and kept as the last change time;
- Scheduled update runs only if `now - remote_digests_changed_at >=` effective delay (or delay is `0` / timestamp is missing);
- **Manual** updates ignore the delay;
- Notifications on check are **not** delayed.
