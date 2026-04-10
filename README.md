# 📡 GitHub Starred Feed

A lightweight CLI tool that acts as a personalized RSS-style news reader for your GitHub starred repositories. It aggregates recent **Issues** and **Releases**, displays them in a clean terminal feed, and tracks what you've already seen.

## ✨ Features

- 🔍 Scans all your starred repositories for new Issues and Releases
- 📅 Filters updates by timestamp (only shows what's new since your last run)
- 💾 Local state tracking (`~/.gh_starred_feed_state.json`) to mark items as read
- 🚫 Automatically excludes Pull Requests (focuses on community/bug tracking)
- 🐧 Optimized for Linux environments
- ⚡ Rate-limit aware with polite API delays & pagination support

## 📦 Prerequisites

- Python 3.7+
- `requests` library
- GitHub Personal Access Token (PAT)

## 🛠️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/racuna/githubreader.git
   cd githubreader
   ```

2. **Install dependencies:**
   ```bash
   pip install requests
   ```

3. **Generate a GitHub PAT:**
   - Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
   - Generate a new token with `public_repo` scope (or `repo` if you star private repositories)

4. **Set the token as an environment variable:**
   ```bash
   export GITHUB_TOKEN="ghp_your_token_here"
   # Add to ~/.bashrc or ~/.zshrc for persistence
   echo 'export GITHUB_TOKEN="ghp_your_token_here"' >> ~/.bashrc
   source ~/.bashrc
   ```

## 🚀 Usage

Run the script:
```bash
chmod +x github_starred_feed.py
./github_starred_feed.py
```

It will output a clean feed of new updates. At the end, it prompts you to mark them as read. Answer `y` to save the timestamp, or `n` to review them again later.

### 📄 Example Output
```
📦 microsoft/vscode (https://github.com/microsoft/vscode)
  🚀 RELEASE: v1.85.0 (v1.85.0)
     📅 2024-01-15 10:30 UTC | 🔗 https://github.com/microsoft/vscode/releases/tag/v1.85.0
     📝 Release notes: Performance improvements, new extension APIs...
  🟢 ISSUE #2041: Memory leak in terminal on Linux
     📅 2024-01-16 08:12 UTC | 🔗 https://github.com/microsoft/vscode/issues/2041
```

## ⏱️ Automation (Optional)

Run it daily via `cron`:
```bash
# Runs every day at 09:00, appends to log
0 9 * * * /usr/bin/python3 /path/to/gh_starred_feed.py >> ~/.gh_starred_feed.log 2>&1
```

> 💡 **For unattended runs**, modify the prompt section in `main()` to auto-mark as read:
> ```python
> state["last_run"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
> save_state(state)
> ```

## 📂 State Management

The tool stores a `last_run` timestamp in `~/.gh_starred_feed_state.json`.
- 🗑️ Delete this file to reset the history and see all past updates again.
- 🌍 The timestamp is always saved in UTC for consistency across timezones.

## ⚠️ API Rate Limits

- Authenticated GitHub API allows **5,000 requests/hour**.
- The script sleeps `0.2s` between requests to stay well within limits.
- If you have 500+ starred repos, consider filtering by organization or language, or run the script less frequently.

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

GPL2 © racuna
