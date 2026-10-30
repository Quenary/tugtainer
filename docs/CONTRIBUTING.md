# Contributing guidelines for the Tugtainer project

Contributions are welcome. Please follow these guidelines to keep the project consistent and maintainable.

## Development

Angular for frontend, Python for backend and agent.

See [backend/README.md](/backend/README.md) and [frontend/README.md](/frontend/README.md) for setup. From the repo root:

```bash
uv run python -m backend.dev
uv run python -m agent.dev
npm --prefix frontend run start
```

## Commits

- Use the [Conventional Commits](https://www.conventionalcommits.org/) format for all commit messages e.g. `feat(backend): add user authentication`. Common types: feat, fix, docs, refactor, test, chore
- Keep commits focused, avoid mixing unrelated changes

AI tools may assist, but the human author is responsible for every change. Commit messages, PR titles, and descriptions contain no `Co-authored-by` trailers, agent mentions (such as `@cursor`), or "Generated with …" lines, and AI tools are not listed as authors.

## Code Changes

- Follow the existing code style and structure
- Prefer clear, readable solutions
- Avoid introducing unnecessary dependencies

## Tests

- All new features must include unit tests
- If you modify existing functionality, update or add/extend the related tests
- Ensure all tests pass before submitting changes
- Ensure lint and typechecks pass before submitting changes
- Application tests (system / integration / e2e) live in [/tests](/tests); see [/tests/README.md](/tests/README.md)

```bash
# Python lint, format, types
uv run ruff check --fix
uv run ruff format
uv run mypy agent backend shared

# Python unit tests (PYTHONPATH=. is mandatory)
PYTHONPATH=. uv run pytest
# Single test file:
PYTHONPATH=. uv run pytest backend/core/jobs/cleanup/test_cleanup_containers.py

# Frontend
npm --prefix frontend run lint
npm --prefix frontend run prettier-check
npm --prefix frontend run test:ci

# Integration / E2E (with cleanup)
npm --prefix tests run test:all
# Integration / E2E (if test app is already started)
npm --prefix tests run test:docker
```

## Pull Requests

- Provide a clear description of what was changed and why
- Reference related issues if applicable
- Keep pull requests focused, avoid mixing unrelated changes
- Titles and descriptions follow the AI attribution rule from Commits

## General

- If a breaking change is required, consider opening an issue and discussing it first

## Documentation

Update the matching documentation in the same change when behavior, configuration, architecture, or contracts change. General docs live in `docs/`. Package docs live beside the code (`backend/README.md`, `agent/README.md`, `frontend/README.md`). The root `README.md` is the product overview.

- **Compact and readable.** Short sections, lists and tables instead of long prose. Extend an existing doc rather than adding a new one, and remove text that the change made stale.
- **Behavior, rules, and flow.** Describe what the feature does, the rules and permissions, and how the parts interact. API request and response schemas, error codes, timeouts, magic numbers, and algorithm internals stay in the code, the Pydantic schemas in `shared/schemas/`, and the OpenAPI docs (`/api/docs`). A template an operator edits, such as a notification body, includes the context it receives: that context is the configuration contract.
- **Technical voice.** Third person, present tense: "The app supports…", "The server stores…". No direct address and no marketing wording.
- **Diagrams.** Flows, state decisions, and component relations use Mermaid (`flowchart`, `sequenceDiagram`). Each diagram stays small and parses.
- **Language and format.** English. File, class, and setting names are in backticks. Relative links and anchors stay valid.
