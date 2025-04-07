# GitHub PR Dashboard

A simple FastAPI-based dashboard that displays open pull requests across all GitHub repositories accessible via one or more personal access tokens (PATs). Supports merging PRs and checking for active GitHub Actions workflows before merging.

## Features

- View open PRs from all accessible repos (classic tokens only)
- Merge PRs directly from the dashboard
- Token-aware merge routing (uses the correct token per PR)
- CI status indicator per repo (green = no actions running, orange = active actions)
- FastAPI + async httpx based

## Setup

### 1. Clone this repo

```bash
git clone https://github.com/marksowell/gh-dash.git
cd gh-dash
```

### 2. Create `.env`

```bash
touch .env
```

Add this to your `.env`:

```env
GITHUB_CLASSIC_TOKENS=ghp_abc123...,ghp_def456...
```

- ✅ Use **classic tokens** with `repo` scope
- 🔒 No quotes or trailing spaces
- ✅ Comma-separated if using multiple tokens

### 3. Create virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the dashboard

```bash
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## Notes

- The dashboard pulls fresh data on each page load.
- CI dots:
  - 🟢 Green: No GitHub Actions currently running
  - 🟠 Orange: At least one GitHub Action is running on the repo

## License

This project is licensed under the [MIT License](LICENSE).
