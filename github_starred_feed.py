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
        # Safely extract next page URL from Link header
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
            "changelog": body[:400] + ("..." if len(body) > 400 else "")
        })

    return issues, releases

def fmt_dt(dt_str):
    return parse_iso(dt_str).strftime("%Y-%m-%d %H:%M UTC") if dt_str else ""

def main():
    token = get_token()
    state = load_state()
    since_dt = parse_iso(state.get("last_run")) if state.get("last_run") else None

    print("\n🔍 Fetching starred repositories...")
    repos = fetch_starred_repos(token)
    print(f"✅ Found {len(repos)} repositories. Scanning for updates...\n")

    feed_lines = []
    new_count = 0

    for i, repo in enumerate(repos, 1):
        name = repo["full_name"]
        print(f"⏳ [{i}/{len(repos)}] {name}", end="\r")

        try:
            issues, releases = get_updates(name, since_dt, token)
        except requests.RequestException as e:
            print(f"\n⚠️  Failed to fetch {name}: {e}")
            continue

        if issues or releases:
            feed_lines.append(f"\n📦 {name} ({repo['html_url']})")
            for r in releases:
                feed_lines.append(f"  🚀 RELEASE: {r['name']} ({r['tag']}) {'[PRE-RELEASE]' if r['prerelease'] else ''}")
                feed_lines.append(f"     📅 {fmt_dt(r['published'])} | 🔗 {r['url']}")
                feed_lines.append(f"     📝 {r['changelog'].replace(chr(10), ' ')}")
            for iss in issues:
                state_emoji = "🟢" if iss["state"] == "open" else "🔵"
                feed_lines.append(f"  {state_emoji} ISSUE #{iss['number']}: {iss['title']}")
                feed_lines.append(f"     📅 {fmt_dt(iss['updated'])} | 🔗 {iss['url']}")
            new_count += len(issues) + len(releases)

    print(" " * 60, end="\r")  # Clear progress line

    if new_count == 0:
        print("\n✨ No new updates since the last run.")
    else:
        print("\n" + "="*70)
        print(f"📰 NEW UPDATES SINCE {'last run' if since_dt else 'the beginning'} ({new_count} items)")
        print("="*70)
        print("\n".join(feed_lines))
        print("="*70)

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