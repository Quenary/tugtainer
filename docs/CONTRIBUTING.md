# Contributing guidelines for the Tugtainer project

Contributions are welcome. Please follow these guidelines to keep the project consistent and maintainable.

## Development

Angular for frontend, Python for backend and agent.

See [/backend/README.md](/backend/README.md) and [/frontend/README.md](/frontend/README.md) for more details.

## Commits

- Use the [Conventional Commits](https://www.conventionalcommits.org/) format for all commit messages e.g. `feat(backend): add user authentication`. Common types: feat, fix, docs, refactor, test, chore
- Keep commits focused, avoid mixing unrelated changes

## Code Changes

- Follow the existing code style and structure
- Prefer clear, readable solutions
- Avoid introducing unnecessary dependencies

## Tests

- All new features must include unit tests
- If you modify existing functionality, update or add/extend the related tests
- Ensure all tests pass before submitting changes
- Ensure lint and typechecks pass before submitting changes (see backend/frontend readme for details)

## Pull Requests

- Provide a clear description of what was changed and why
- Reference related issues if applicable
- Keep pull requests focused, avoid mixing unrelated changes

## General

- If a breaking change is required, consider opening an issue and discussing it first
- Update documentation (README.md) when behavior changes
