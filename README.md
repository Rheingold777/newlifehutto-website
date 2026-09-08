# New Life Hutto website

GitHub holds the versioned website source. Cloudflare Pages project `newlifehutto` serves the public website. Church-controlled Drive storage holds recovery archives and private audit evidence. Obsidian records church direction; Monday records task ownership and release acceptance.

This source contains the approved September 8, 2026 design: retained full-width worship hero, face-hidden crop, credited baptism photo, direct email/phone contact, Planning Center Giving with one transitional Breeze fallback, and the confirmed building directions. Public address: **623 W Front St, Hutto, TX 78634**; arrival guidance identifies **Suite 1800**. Services: Sunday 11 AM and Tuesday 7 PM.

## Source layout

- `site/`: finished editable HTML, CSS, images and client JavaScript.
- `templates/` and `scripts/`: accepted section templates, focused helpers, packaging and checks.
- `config/`: frozen public-content reconciliation and approved deploy-file fingerprints.
- `routes.json` and `cloudflare-runtime/`: canonical routes, legacy redirects, real 404 behavior and the Pages Worker.
- `server.mjs`: local preview server; removes analytics from responses and adds noindex protections.
- `output/`: generated releases and local test evidence, ignored by Git.

Edit the finished `site/` source. The old full construction generator is intentionally not an active build input: rerunning it would restore historical copy. The reconciliation helper is offline and loads public frozen data from `config/production-v4-baseline.json`. If applying historical focused helpers, run current production reconciliation last; review their changes before saving.

## Preview and build

Use Python 3.12+ and Node.js 22+:

```sh
node server.mjs
```

Open http://127.0.0.1:8770/. Preview serving is local only. Saved HTML retains production analytics; do not expose the source with an arbitrary public server.

```sh
python scripts/package-cloudflare.py --out output/release
python scripts/verify-approved-release.py --package output/release
node --test scripts/cloudflare-routing.test.mjs
npx --yes wrangler@4.85.0 pages dev output/release/deploy --ip 127.0.0.1 --port 8787 --compatibility-date 2026-03-20
python scripts/verify-cloudflare-http.py --base http://127.0.0.1:8787 --package output/release
```

Choose a new output directory on each build. The packager refuses to overwrite a release. Its `deploy/` directory contains the full production artifact; **never deploy the repository root or bare `site/`**. The archive is for recovery/review, not a Wrangler upload input.

## Release control and rollback

The GitHub deployment workflow is **manual `workflow_dispatch` only**, on `main`; pushing or merging does not trigger that workflow. It packages and verifies the approved 35-file release, then uses Wrangler **4.85.0** and existing secrets `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID`. Secret values never belong in files. The separate legacy GitHub Pages publishing configuration was disabled September 8, 2026; Cloudflare remains the live host.

Before a public release, refresh the actual Cloudflare deployment and account configuration, confirm authorization and recovery availability, and review `cloudflare-runtime/README.md`. The recorded baseline is deployment `75e07616-2695-48d0-80df-ff71bcdb16b4`; changes to production after that record must be reconciled. Verify the privately held `website-publish-v4.zip` through the optional `--rollback-archive PATH` build argument before release. The archive is not required for portable source builds and is not copied into them.

Cloudflare currently uses Direct Upload. This repository does not change its Git integration, DNS, registrar, email, giving providers or Search Console access. A source commit is not proof of a public deployment. Confirm the final Cloudflare deployment and all 14 routes after publishing; use the verified baseline deployment for rollback if needed.

Do not commit private GSC exports, church operational records, donor/member data, credentials, browser profiles, `.wrangler`, screenshots of authenticated systems, or bulk backups. The public site assets and their visible credits are included deliberately.
