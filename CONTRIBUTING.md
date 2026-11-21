# Contributing

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff format . && .venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/pytest          # enforces 100% line and branch coverage
```

- Every method must be tested for both `Hello` and `AsyncHello` (see `tests/test_resources.py`).
- `_resources_async.py` mirrors `_resources_sync.py`; change both together.
- Request building lives in `_specs.py`, shared by both clients.
- Keep Python 3.9 compatibility and `httpx` as the only runtime dependency.
- Update `CHANGELOG.md` for user-visible changes.

By contributing you agree your work is licensed under the MIT License.
