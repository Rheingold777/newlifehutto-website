# Deploying newlifehutto.com

**Release source:** the `site/` folder in this repo, packaged by `scripts/package-cloudflare.py` (plus `routes.json` and `cloudflare-runtime/`). As of 2026-10-10, `main` (after the sync-live-2026-10-10 PR) rebuilds production deploy **cf494522** byte for byte. Host: Cloudflare Pages project `newlifehutto` (Direct Upload, production branch `main`), account `ca5665f0bc2c4a49c15f353f527a4394`.

Edit `site/` only, never a deploy folder. Commit the change to Git before you deploy, so the repo always matches what's live.

## Safe release steps

1. **Build** into a new folder: `python scripts/package-cloudflare.py --out output/<new-name>`.
2. **Preview first:** `npx wrangler@4.85.0 pages deploy output/<new-name>/deploy --project-name newlifehutto --branch <feature-branch>`. Any branch other than `main` is a preview at `<branch>.newlifehutto.pages.dev`.
3. **Crawl and compare:** fetch every URL (sitemap, /privacy/, /terms/, /sms/, /textos/, nav and footer links, assets, legacy redirects, plus one unknown URL that should 404) on both the current production deployment URL and the preview. Every page must return the same status. Only the pages you meant to change may differ (pages.dev robots.txt is always `Disallow`, which is expected).
4. **Production:** deploy the same folder with `--branch main`. Then re-crawl https://newlifehutto.com and compare against the crawl you took just before deploying.
5. **Record it:** add the deploy ID and the previous ID (for rollback) to the commit or PR.

**Rollback:** Cloudflare Pages > newlifehutto > Deployments > previous deployment > "Rollback to this deployment".

Never deploy the repo root or bare `site/`, and never commit credentials. Use a Cloudflare token or key from the environment.
