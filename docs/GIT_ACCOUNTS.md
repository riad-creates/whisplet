# Work and personal GitHub accounts

`gitswitch` selects a saved GitHub CLI account and keeps each matching checkout's
commit identity and Git HTTPS credentials pinned to that account. It never stores
tokens in this repository or rewrites existing commits.

Install the helper once:

```bash
mkdir -p "$HOME/.local/bin" "$HOME/.config/gitswitch"
cp scripts/gitswitch "$HOME/.local/bin/gitswitch"
chmod +x "$HOME/.local/bin/gitswitch"
```

Ensure `~/.local/bin` is on your PATH. Create `~/.config/gitswitch/accounts` with
one profile and GitHub username per line, separated by a **tab**. Account names
are configuration, not tokens. Both accounts must already be signed in through
`gh auth login`.

```text
work<TAB>YOUR_WORK_USERNAME
personal<TAB>YOUR_PERSONAL_USERNAME
```

Then:

```bash
gitswitch personal
gitswitch work
gitswitch status
```

Run the chosen profile inside a matching GitHub HTTPS checkout once to pin it.
The helper uses that account's GitHub noreply address for future commits. It
changes only repository-local Git settings, not your global Git author.
Switching `gh` back to work later leaves the personal checkout's pinned Git
credentials intact. It also leaves the origin URL unchanged.

If the checkout belongs to another account, `gitswitch` switches the GitHub CLI
account but preserves that checkout's identity. SSH and organization-owned remotes
are not automatically reconfigured. Explicit `GH_TOKEN`/`GITHUB_TOKEN` shell
variables must be unset before switching because they override the CLI account.

## This project

Whisplet is a personal project owned by **riad-creates**. Its canonical remote is
`https://github.com/riad-creates/whisplet.git`. Check both `gitswitch status` and
`gh api user --jq .login` before creating repositories, releases or pull requests.
Do not infer the destination owner from whichever `gh` account happens to be
active. The original work-account copy is not the publishing target.

The landing page uses the Vercel account `tobicj23-5222` and scope
`tobicj23-5222s-projects`. This is separate from the GitHub CLI login; that Vercel
project connects directly to `riad-creates/whisplet`. No second Vercel account is
required. See `website/README.md` for hosting and automatic deployment settings.
