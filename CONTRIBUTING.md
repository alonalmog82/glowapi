# Contributing to GlowAPI

Contributions are welcome — bug fixes, new git providers, documentation improvements, or anything else.

## Local setup

**1. Fork and clone**

```bash
git clone https://github.com/<your-username>/glowapi.git
cd glowapi
```

**2. Create a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

**4. Copy the example config**

```bash
cp config.env.example config.env
# Fill in credentials if you want to test against a real repo.
# Tests run without credentials — all external calls are mocked.
```

**5. Run the tests**

```bash
pytest tests/ -v
```

**6. Run the linter**

```bash
flake8 .
```

## Making changes

- Keep a virtual environment active while developing — never install into the system Python
- All external calls (GitHub API, Bitbucket API) must be mocked in tests; no real network calls in the test suite
- New providers should implement the `GitProvider` ABC in `utils/providers/base.py` and be registered in `utils/providers/factory.py`
- Line length limit is 120 characters (`.flake8`)

## Submitting a pull request

1. Create a branch: `git checkout -b feat/your-feature`
2. Make your changes and add tests
3. Ensure `pytest tests/ -v` and `flake8 .` both pass
4. Open a PR against `main` — describe what it does and why
