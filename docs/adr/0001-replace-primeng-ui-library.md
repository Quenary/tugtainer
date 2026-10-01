# ADR-0001: Replace PrimeNG with Optimus UI

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Tugtainer maintainers
- **Related:** Angular 22 upgrade; current temporary pin to `primeng@21` via npm `overrides`

## Context

PrimeTek archived the open-source PrimeNG line and moved major versions from **v22** to a commercial license. Tugtainer already runs **Angular 22** and still depends on **PrimeNG 21** (MIT) with peer-dependency `overrides` so it can resolve against Angular 22 packages.

That is a stopgap:

- PrimeNG 21 will not track Angular majors.
- Peer overrides hide real incompatibility risk.
- Paying for PrimeNG 22 is undesirable for this project.
- Staying on an abandoned major is a long-term maintenance and security liability.

Current frontend coupling is substantial: on the order of **40+ TypeScript modules** import PrimeNG / `@primeuix/themes`, including `Table`, `DynamicDialog`, `Password`, `Accordion`, `Toast`, `ConfirmPopup`, `Tree`, `AutoComplete`, theming via Aura, and `primeicons`.

We need an open-source replacement that keeps the app maintainable on Angular 22+.

## Decision drivers

1. **License:** MIT (or equivalent permissive), no paid runtime tier required.
2. **Angular 22 support** without peer hacks.
3. **Migration cost** relative to the existing PrimeNG-shaped UI.
4. Coverage of what we actually use: data tables, dialogs/overlays, forms (password, filters), tags/toasts, menus, accordion/tabs.
5. Theming that can stay close to the current look (cyan/Aura-like) without a full redesign.
6. Maintenance signal: releases, community, Angular alignment.
7. Bundle size and DX are secondary but relevant.

## Options considered

### A. [Optimus UI](https://github.com/openng-org/optimus-ui) (`@openng/optimus-ui`) — community fork of PrimeNG v21

- MIT; explicitly positioned as the open continuation of PrimeNG v21 ([site](https://optimus.openng.org/), [repo](https://github.com/openng-org/optimus-ui)).
- **v2 targets Angular 22**; v1 targets Angular 21.
- Official migration path: `ng generate @openng/optimus-ui:migrate-from-primeng` (rewrites packages/imports; reports leftovers).
- Same component model / theming family (`provideOptimus`, Aura/Lara/Material/Nora presets, optional `@openng/icons` as `pi pi-*` successor).
- Young as a distinct org/product; long-term governance still maturing (fork + community, no commercial SLA).

### B. [Taiga UI](https://taiga-ui.dev/) (`@taiga-ui/*`)

- MIT; modern, strongly typed Angular UI from T-Bank / community maintainers.
- Supports recent Angular (`>=19` peers as of `@taiga-ui/core@5`).
- Different design system, APIs, and package layout → essentially a **rewrite of UI layer**, not a drop-in.
- Strong DX/a11y reputation; smaller “drop-in admin widgets” overlap with our PrimeNG tables/dialogs patterns.

### C. Angular Material + CDK (`@angular/material`)

- MIT; owned by the Angular team; best long-term Angular alignment.
- Fewer high-level widgets (especially vs PrimeNG `Table` / DynamicDialog-heavy screens).
- Would require rebuilding several screens on CDK primitives or adding extra libraries.

### D. NG-ZORRO (`ng-zorro-antd`)

- MIT; Ant Design for Angular; Angular 22-aligned releases exist.
- Full redesign to Ant Design language; no mechanical migration from PrimeNG.
- Solid enterprise table/form coverage, but high visual and code churn.

### Other notes (not primary candidates)

- **Stay on PrimeNG 21 + overrides (status quo):** no immediate rewrite, but a dead-end for Angular upgrades; overrides are technical debt. Acceptable only until migration lands.
- **License PrimeNG 22 (commercial):** official upgrade path from PrimeTek, but conflicts with “stay open / no paid UI runtime” preference for this project. Out of scope unless requirements change.
- **ng-bootstrap / ngx-bootstrap:** MIT, but Bootstrap-sized surface (~interactive Bootstrap widgets), not a replacement for our table/dialog-heavy admin UI.
- **Nebular:** MIT, Eva design; less momentum and still a redesign.
- Building everything on **CDK only** is too expensive for the current feature set.

## Decision

**Migrate to Optimus UI v2** (`@openng/optimus-ui`).

It minimizes rewrite risk while restoring a supported Angular 22 + MIT stack. The project already speaks PrimeNG; Optimus provides a purpose-built schematic and keeps theming/component concepts familiar.

## Consequences

### Positive

- Escape commercial PrimeNG 22 without freezing on Angular 21-era UI.
- Remove npm `overrides` for `primeng` peers.
- Keep most templates/structure; migration is package/import/theme oriented rather than a product redesign.

### Negative / risks

- Optimus is newer as a brand; bus factor and roadmap need watching.
- Schematic will not cover 100% of edge cases; expect manual follow-ups (icons package rename, theme import paths, any PrimeNG-only APIs that diverged).
- Temporary dual-docs/muscle-memory (“PrimeNG” vs “Optimus”) during transition.

### Neutral

- Visual language can stay Aura-like; no mandatory redesign.

## Migration plan

1. Install `@openng/optimus-ui@2`, run `migrate-from-primeng`, fix leftovers.
2. Replace `@primeuix/themes` / `primeicons` with Optimus themes / `@openng/icons` as documented.
3. Restore cyan primary tokens equivalent to current `definePreset(Aura, …)`.
4. Drop `primeng` and peer `overrides`.
5. Verify build, unit tests, lint/prettier, smoke main flows (hosts/containers tables, jobs dialog, auth password, toasts).

## References

- [Optimus UI repository](https://github.com/openng-org/optimus-ui)
- [Optimus UI docs / installation](https://optimus.openng.org/installation)
- [Taiga UI](https://taiga-ui.dev/)
- Current stopgap: `frontend/package.json` (`primeng@^21.1.10` + `overrides`)
