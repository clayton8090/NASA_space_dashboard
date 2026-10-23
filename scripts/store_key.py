"""Store your NASA API key in the system keychain (hidden prompt; nothing is written to disk)."""
import getpass

import keyring

key = getpass.getpass("Paste your NASA API key (input is hidden): ").strip()
if len(key) < 20 or key.startswith(("ghp_", "github_pat_")):
    raise SystemExit("That doesn't look like a NASA API key (too short, or a GitHub token). Nothing saved.")
keyring.set_password("nasa-space-dashboard", "NASA_API_KEY", key)
print("Saved to your keychain.")
