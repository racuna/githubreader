#!/usr/bin/env python3
"""
GitHub Starred Feed
A lightweight CLI tool that acts as a personalized RSS-style news reader
for your GitHub starred repositories. Tracks new Issues and Releases
since your last run.
Requires: pip install requests
"""
import os
import sys
import time
import json
import textwrap
import requests
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path.home() / ".gh_starred_feed_state.json"
API_BASE = "https://api.github.com"

def get_token():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ Error: GITHUB_TOKEN environment variable is not set.")
        print("   Generate one at: https://github.com/settings/tokens")
        print("   Required scopes: 'public_repo' or 'repo' (for private stars)")
        sys.exit(1)
    return token

def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_run": None}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def parse_iso(dt_str):
    """Parse ISO 8601 datetime string, handling 'Z' suffix for Python < 3.11"""
    if not dt_str:
        return None
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

def api_get(url, token, params=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code == 403:
        reset = int(resp.headers.get("X-RateLimit-Reset", 0))
        wait_time = max(reset - time.time(), 0)
        print(f"⏳ API rate limit reached. Retry in {time.strftime('%H:%M:%S', time.gmtime(wait_time))}")
        sys.exit(1)
    resp.raise_for_status()
    return resp

def fetch_starred_repos(token):
    repos = []
    url = f"{API_BASE}/user/starred?per_page=100&sort=created&direction=desc"
    while url:
        resp = api_get(url, token)
        repos.extend(resp.json())
        url = resp.links.get("next", {}).get("url")
        time.sleep(0.2)  # Polite delay for the API
    return [{"full_name": r["full_name"], "html_url": r["html_url"]} for r in repos]

def get_updates(repo_name, since_dt, token):
    issues = []
    releases = []
    # Fetch issues (excluding PRs)
    issues_url = f"{API_BASE}/repos/{repo_name}/issues"
    resp = api_get(issues_url, token, {"state": "all", "sort": "updated", "direction": "desc", "per_page": 20})
    for issue in resp.json():
        if "pull_request" in issue:
            continue
        updated = parse_iso(issue["updated_at"])
        if since_dt and updated <= since_dt:
            break  # Sorted by updated_at, safe to stop early
        issues.append({
            "number": issue["number"],
            "title": issue["title"],
            "state": issue["state"],
            "url": issue["html_url"],
            "updated": issue["updated_at"]
        })
    # Fetch releases
    releases_url = f"{API_BASE}/repos/{repo_name}/releases"
    resp = api_get(releases_url, token, {"per_page": 10})
    for rel in resp.json():
        published = parse_iso(rel["published_at"])
        if since_dt and published <= since_dt:
            break
        body = rel.get("body") or "No changelog provided."
        releases.append({
            "tag": rel["tag_name"],
            "name": rel.get("name") or rel["tag_name"],
            "prerelease": rel.get("prerelease", False),
            "url": rel["html_url"],
            "published": rel["published_at"],
            "body": body
        })
    return issues, releases

def fmt_dt(dt_str):
    return parse_iso(dt_str).strftime("%Y-%m-%d %H:%M UTC") if dt_str else ""

def format_changelog(body, max_lines=4, width=68, indent="      "):
    """Format changelog preserving structure, wrapping long lines and truncating gracefully."""
    if not body or body.strip() in ("No changelog provided.", ""):
        return f"{indent}📝 Sin detalles de cambios."
    
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    if not lines:
        return f"{indent}📝 Sin detalles de cambios."
        
    selected = lines[:max_lines]
    formatted = []
    for i, line in enumerate(selected):
        wrapped = textwrap.wrap(line, width=width - len(indent) - 2)
        if not wrapped:
            wrapped = [""]
        for j, w_line in enumerate(wrapped):
            prefix = "📝 " if (i == 0 and j == 0) else "   "
            formatted.append(f"{indent}{prefix}{w_line}")
            
    if len(lines) > max_lines:
        formatted.append(f"{indent}   🔗 Ver changelog completo en el enlace de la release")
    return "\n".join(formatted)

def main():
    token = get_token()
    state = load_state()
    since_dt = parse_iso(state.get("last_run")) if state.get("last_run") else None
    
    print("🔍 Fetching starred repositories...")
    repos = fetch_starred_repos(token)
    print(f"✅ Found {len(repos)} repositories. Scanning for updates...\n")
    
    feed_lines = []
    new_count = 0
    
    # Leyenda explicativa
    feed_lines.append("🔍 LEYENDA:")
    feed_lines.append("🟢 Issue ABIERTO  |  🔵 Issue CERRADO")
    feed_lines.append("🚀 Nueva Release  |  📝 Changelog  |  🔗 Enlace")
    feed_lines.append("=" * 70 + "\n")
    
    for i, repo in enumerate(repos, 1):
        name = repo["full_name"]
        print(f"⏳ [{i}/{len(repos)}] {name}", end="\r")
        try:
            issues, releases = get_updates(name, since_dt, token)
        except requests.RequestException as e:
            print(f"\n⚠️  Failed to fetch {name}: {e}")
            continue
            
        if issues or releases:
            feed_lines.append(f"📦 {name}")
            feed_lines.append(f"   🔗 {repo['html_url']}\n")
            
            if releases:
                feed_lines.append("  🚀 RELEASES:")
                for r in releases:
                    feed_lines.append(f"    {r['name']} ({r['tag']}) {'[PRE-RELEASE]' if r['prerelease'] else ''}")
                    feed_lines.append(f"       📅 {fmt_dt(r['published'])}")
                    feed_lines.append(f"       🔗 {r['url']}")
                    feed_lines.append(format_changelog(r["body"]) + "\n")
                    
            if issues:
                feed_lines.append("  📝 ISSUES:")
                for iss in issues:
                    state_emoji = "🟢" if iss["state"] == "open" else "🔵"
                    state_text = "ABIERTO" if iss["state"] == "open" else "CERRADO"
                    feed_lines.append(f"    {state_emoji} #{iss['number']} {state_text}: {iss['title']}")
                    feed_lines.append(f"       📅 {fmt_dt(iss['updated'])}")
                    feed_lines.append(f"       🔗 {iss['url']}\n")
                    
            new_count += len(issues) + len(releases)
            feed_lines.append("-" * 60 + "\n")
            
    print(" " * 60, end="\r")  # Clear progress line
    
    if new_count == 0:
        print("\n✨ No new updates since the last run.")
    else:
        print("\n" + "\n".join(feed_lines))
        
    while True:
        ans = input("\n❓ Mark all these updates as read? (y/n): ").strip().lower()
        if ans in ("y", "yes"):
            state["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            save_state(state)
            print("✅ State updated. Next run will only show updates after this timestamp.")
            break
        elif ans in ("n", "no"):
            print("🔍 State unchanged. These updates will be shown again next time.")
            break
        else:
            print("Invalid option. Please answer 'y' or 'n'.")

if __name__ == "__main__":
    main()