# github_pr_dashboard/main.py

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_env_tokens(key: str):
    raw = os.getenv(key, "")
    print("RAW ENV VALUE:", repr(raw))
    raw = os.getenv(key, "")
    tokens = raw.split(",") if "," in raw else [raw]
    return [t.strip().strip('"').strip("'") for t in tokens if t.strip()]

GITHUB_TOKENS = get_env_tokens("GITHUB_CLASSIC_TOKENS")
GITHUB_API_URL = "https://api.github.com"

async def fetch_all_repos(headers):
    repos = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            url = f"{GITHUB_API_URL}/user/repos?per_page=100&page={page}"
            print("---- GitHub Request ----")
            print("URL:", url)
            print("Authorization Header:", repr(headers["Authorization"]))
            print("Headers:", headers)
            print("------------------------")
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                print(f"Failed to fetch repos: {resp.text}")
                break
            page_repos = resp.json()
            if not page_repos:
                break
            for r in page_repos:
                if not r.get("archived", False) and not r.get("fork", False):
                    repos.append(r["full_name"])
            page += 1
    return repos

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    pr_data = []
    all_repos = set()

    async with httpx.AsyncClient() as client:
        for token_idx, token in enumerate(GITHUB_TOKENS):
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json"
            }
            repos_to_check = await fetch_all_repos(headers)
            print(f"Repos from token: {repos_to_check}")
            all_repos.update(repos_to_check)

            for repo in repos_to_check:
                prs_url = f"{GITHUB_API_URL}/repos/{repo}/pulls"
                try:
                    resp = await client.get(prs_url, headers=headers)
                    if resp.status_code == 200:
                        repo_prs = resp.json()
                        for pr in repo_prs:
                            pr["_token_idx"] = token_idx
                        pr_data.extend(repo_prs)
                    else:
                        print(f"Failed to fetch PRs for {repo}: {resp.text}")
                except Exception as e:
                    print(f"Error fetching PRs for {repo}: {e}")

    html_output = """
    <html><head><title>GitHub PR Dashboard</title>
    <link rel='stylesheet' href='/static/style.css'></head><body>
    <h1>GitHub PR Dashboard</h1>
    <table><tr><th>Repo</th><th>Title</th><th>Author</th><th>Status</th><th>Actions</th><th>CI</th></tr>
    """

    if not pr_data:
        for repo in sorted(all_repos):
            html_output += f"""
            <tr>
                <td>{repo}</td>
                <td colspan='4'><i>No open pull requests</i></td>
            </tr>
            """
    else:
        for pr in pr_data:
            repo_name = pr['base']['repo']['full_name']
            title = pr['title']
            author = pr['user']['login']
            url = pr['html_url']
            pr_number = pr['number']

            # Check for running workflows
            workflows_url = f"{GITHUB_API_URL}/repos/{repo_name}/actions/runs"
            token_idx = pr["_token_idx"]
            headers = {
                "Authorization": f"token {GITHUB_TOKENS[token_idx]}",
                "Accept": "application/vnd.github+json"
            }
            ci_status = "<span style='color:green'>●</span>"
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(workflows_url, headers=headers)
                    if resp.status_code == 200:
                        runs = resp.json().get("workflow_runs", [])
                        if any(run.get("status") != "completed" for run in runs):
                            ci_status = "<span style='color:orange'>●</span>"
            except Exception as e:
                print(f"Workflow check failed for {repo_name}: {e}")

            html_output += f"""
            <tr>
                <td>{repo_name}</td>
                <td><a href='{url}' target='_blank'>{title}</a></td>
                <td>{author}</td>
                <td>{'Open' if pr['state'] == 'open' else 'Closed'}</td>
                <td>
                    <form action='/merge' method='post'>
                        <input type='hidden' name='repo' value='{repo_name}' />
                        <input type='hidden' name='pr_number' value='{pr_number}' />
                        <input type='hidden' name='token_idx' value='{pr["_token_idx"]}' />
                        <button type='submit'>Merge</button>
                    </form>
                </td>
                <td>{ci_status}</td>
            </tr>
            """

    html_output += "</table></body></html>"
    return HTMLResponse(content=html_output)

@app.post("/merge")
async def merge_pr(repo: str = Form(...), pr_number: int = Form(...), token_idx: int = Form(...)):
    print(f"Merging PR: repo={repo}, pr_number={pr_number}")
    merge_url = f"{GITHUB_API_URL}/repos/{repo}/pulls/{pr_number}/merge"  # Note: 'pulls' is correct per GitHub API
    print(f"Merge URL: {merge_url}")

    headers = {
        "Authorization": f"token {GITHUB_TOKENS[token_idx]}",
        "Accept": "application/vnd.github+json"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.put(merge_url, headers=headers)

    if resp.status_code in [200, 201]:
        print("Merge successful!")
        return HTMLResponse("<p>PR Merged! <a href='/'>Go back</a></p>")
    else:
        print(f"Merge failed: {resp.text}")
        return HTMLResponse(f"<p>Error: {resp.text} <a href='/'>Go back</a></p>", status_code=400)
