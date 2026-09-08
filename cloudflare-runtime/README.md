# Cloudflare runtime and release

The packager creates a Pages advanced-mode `_worker.js`, `_routes.json`, 404 response, assets and 14 mapped HTML routes. `env.ASSETS` reads internal `/_nlh-pages/*.page` files; public paths are mapped by the Worker. Production HTTPS/apex/slash redirects preserve paths and queries. Localhost and pages.dev responses are noindex; production allows crawling.

The last verified production baseline is static v4 deployment `75e07616-2695-48d0-80df-ff71bcdb16b4`, September 8, 2026. Project `newlifehutto` is Direct Upload, branch `main`, compatibility date `2026-03-20`, no flags, standard usage. Recheck these before release. The v4 ZIP fingerprint and deployment reference are in `release-context.json`; the church retains the actual recovery archive privately.

All candidate requests invoke Pages Functions. The last project check reported `fail_open: true`. A September 8 account-dashboard check established adequate current headroom; detailed account usage remains in private operational evidence. The allowance is shared and can change. If exhausted, static fallback could bypass redirects and the mapped HTML routes. Monitor account usage and preserve a tested rollback. This repository makes no account or plan change.

Build from the repository root with `python scripts/package-cloudflare.py --out output/release`. For a release-preparation build, add `--rollback-archive PATH` and verify the independently retained v4 archive. A normal portable build does not establish recovery availability. Generated `ROLLBACK.md` states whether the archive was checked.

Deploy the entire generated `output/release/deploy/` directory with Wrangler 4.85.0. The root README documents the manual workflow. Do not deploy the repository root, raw site folder, or archive. Before deployment, confirm production has not changed since the verified baseline. After deployment, verify all canonical pages, assets, redirects, missing routes, robots/sitemap, exact maps and Giving/contact links. Roll back through Cloudflare to the verified baseline if necessary.

Package fingerprints in `config/approved-release-2026-09-08.json` preserve the exact reviewed release. Future intentional source changes require a new reviewed fingerprint set and an explicit update to the verification target.

Official references: [advanced mode](https://developers.cloudflare.com/pages/functions/advanced-mode/), [Pages serving rules](https://developers.cloudflare.com/pages/configuration/serving-pages/), [Functions routing](https://developers.cloudflare.com/pages/functions/routing/), [Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/).
