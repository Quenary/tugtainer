# AGENTS.md — Frontend

Angular 22 SPA for Tugtainer. TypeScript `~6.0`. Standalone components are the default. The app is zoneless (`provideZonelessChangeDetection` in `src/app/app.config.ts`).

For repo-wide workflow and commits, see [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md). Scripts live in `package.json`.

## Layout

- `src/app/features/<feature>/` — screens, `*.store.ts`, `*-api.service.ts`, `*.interface.ts`.
- `src/app/core/` — HTTP interceptor, auth guard, locale, toast, socket, app initializer.
- `src/app/shared/` — reusable components, pipes, forms, functions, directives.
- `src/app/app.config.ts`, `app.routes.ts`, `app.store.ts` — bootstrap, lazy routes, app-wide store.
- `src/testing/mocks/` — TestBed doubles. Import them via `@testing/*`.
- `src/environments/` — `environment.ts` replaced by `environment.prod.ts` in production builds.

Routes lazy-load with `loadComponent`. `ContainersStore`, `ImagesStore`, and `ServicesStore` are provided on their routes. `AppStore`, `HostsStore`, and `SettingsStore` are `providedIn: 'root'`.

## Imports and types

`tsconfig.json` has `"strict": true`, but `strictNullChecks` and `noImplicitAny` are off. Do not tighten those flags as a drive-by. Still avoid new `any`; narrow `unknown` at boundaries.

Path aliases:

- `@shared/*` → `src/app/shared/*`
- `@testing/*` → `src/testing/*`
- `@env/*` → `src/environments/*`

`baseUrl` is `frontend/`, so existing files also import `src/app/...`. Match the import style of the file you are editing.

Selectors: elements `app-*` (kebab-case), attribute directives `app*` (camelCase).

## Angular

- New components, directives, and pipes are standalone. Do not set `standalone: true`.
- `changeDetection: ChangeDetectionStrategy.OnPush` on components.
- Prefer `inject()` over constructor injection.
- Inputs: `input()` / `input.required<T>()`. Outputs: `output<T>()`. Two-way state: `model()`.
- Templates use built-in control flow (`@if`, `@for`, `@switch`). Call signals as `myInput()`.
- Do not use `@HostBinding` or `@HostListener`. Use the `host` object on `@Component` / `@Directive`.
- Do not use `ngClass` or `ngStyle`. Use `[class.foo]` and `[style.prop]`.
- Prefer reactive forms (`FormControl`, `FormGroup`) for form screens. Table filters in this app bind with `FormsModule`.
- i18n: `TranslatePipe` from `@ngx-translate/core`. App setup is `provideTranslateService` / `provideTranslateLoader` (`SlickTranslationLoader`). Do not import `TranslateModule` into components.
- HTTP: `provideHttpClient(withInterceptors([...]))`. New interceptors are functions, same as `authInterceptor`.
- Keep logic in `.ts`, template in `.html`, styles in `.scss`.

### UI

Use `@openng/optimus-ui`. Import each primitive from its entry point (`@openng/optimus-ui/button`, `table`, `dialog`, …). Theme is the Aura preset from `@openng/optimus-ui-themes`, registered with `provideOptimus`. Icons in templates are PrimeIcons classes (`pi pi-server`). Do not add PrimeNG or another component library.

### Signals

Local UI state is `signal()` / `computed()`. Feature and app state is an `@ngrx/signals` `signalStore` (`withState`, `withEntities`, `withMethods`, `withComputed`, `withHooks`). Async store methods use `rxMethod` (`@ngrx/signals/rxjs-interop`) and `tapResponse` (`@ngrx/operators`).

Read every reactive dependency at the start of a `computed()`, `effect()`, or `linkedSignal()` — including `input()` and `viewChild()`. An early `return`, `&&`, `||`, or ternary before those reads means Angular never tracks them.

```ts
effect(() => {
  const map = this.map();
  const container = this.mapContainer()?.nativeElement;

  if (!map || !container) {
    return;
  }

  this.observe(container);
});
```

- Do not put side effects in `computed()` or in a `linkedSignal()` computation.
- In `effect()`, read dependencies first, then run side effects inside `untracked()`.
- Do not mutate signal values in place. Use `.set()` or `.update()`.
- Do not replace a `signalStore` with an ad-hoc shared signal service unless asked.

## Tests

Unit tests run on Vitest through `@angular/build:unit-test` (jsdom). Setup is `src/testing/setup-file.ts`.

Colocate `*.spec.ts` with the unit. Use `TestBed`, `provideTranslateService()` when the template translates, and override stores with `useValue` when the component only reads signals. Shared doubles belong in `src/testing/mocks/`.

Group related `it` blocks in a nested `describe` named after the subject (a computed, a method, a command). Each condition of that subject is its own `it`. Keep the `it` title short: the `describe` name is already the prefix. Leave a single unrelated test, such as creation, at the top level.

## Style

`lint-staged` runs Prettier and ESLint on commit. Follow the Prettier and ESLint config already in the project.

- Drop unused imports. Prefix intentionally unused names with `_` (`@typescript-eslint/no-unused-vars`).
- Do not leave `console.log` in the codebase.
- Every new file ends with a trailing newline.
- Keep diffs limited to the task. Do not migrate unrelated templates or stores.

## Resources

- [Angular components](https://angular.dev/essentials/components)
- [Angular signals](https://angular.dev/essentials/signals)
- [Angular templates](https://angular.dev/essentials/templates)
- [Angular dependency injection](https://angular.dev/essentials/dependency-injection)
