# Whisplet landing page

Next.js static export. Install dependencies with `npm ci`; use `npm run dev` for
local development, `npm run lint` and `npm test` for validation. `npm run build`
exports to `out/`; no Node server is needed to serve the exported page.

The landing page has a copyable automatic setup command and links to the GitHub
source-build guide. It does not advertise a notarized binary or automatic updater.
Its illustrated note is fictional content.

## Production hosting

The public landing page is https://whisplet.vercel.app. Vercel project `whisplet`
belongs to the `tobicj23-5222s-projects` scope (login `tobicj23-5222`) and connects
to **riad-creates/whisplet**, production branch **main**. The project's Root
Directory is **website**, with Next.js, Node 22, `npm ci`, and `npm run build`.
Keep this root directory when importing or reconnecting the Git repository.

Pushing to `main` triggers a production deployment. Other branches can create
previews. Commit changes and inspect the resulting deployment status before
calling an update published. The landing page must stay public without Vercel
authentication. It needs no application server, model files or secrets.

For CLI account checks, use `vercel whoami` and `vercel teams ls`. Use the explicit
scope `--scope tobicj23-5222s-projects` for this project. Do not log out or replace
GitHub credentials just because the Vercel username differs: GitHub commits and
pushes stay under `riad-creates`. See `../docs/GIT_ACCOUNTS.md`.
