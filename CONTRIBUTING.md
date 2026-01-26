# Contributing

## Setup

```bash
git clone <repo-url>
cd lobechat-aws
uv sync
git config core.hooksPath .githooks
```

## Commit Messages

This project uses [Conventional Commits](https://www.conventionalcommits.org/) enforced by [commitizen](https://commitizen-tools.github.io/commitizen/).

### Format

```
type(scope)?: description
```

### Types

| Type | Version Bump |
|------|--------------|
| `feat` | MINOR |
| `fix` | PATCH |
| `feat!` / `fix!` | MAJOR |
| `docs`, `style`, `refactor`, `test`, `build`, `ci`, `chore` | none |

### Making Commits

**Option 1**: Standard git commit (validated by hook)
```bash
git commit -m "feat: add health check endpoint"
```

**Option 2**: Interactive commitizen
```bash
cz commit
```

### Validation

```bash
cz check          # validate last commit
cz check -m "feat: test message"  # validate a message
```

## Versioning

Version bumps are automatic based on commit types:

```bash
cz bump           # bump version based on commits since last tag
cz bump --dry-run # preview the bump
cz changelog      # generate CHANGELOG.md
```

### Examples

```
feat: add feature    → 0.1.0 → 0.2.0 (MINOR)
fix: resolve bug     → 0.1.0 → 0.1.1 (PATCH)
feat!: breaking      → 0.1.0 → 1.0.0 (MAJOR)
```
