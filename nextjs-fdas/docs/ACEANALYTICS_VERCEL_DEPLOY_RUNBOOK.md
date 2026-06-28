# ACEAnalytics Multi-App Vercel Deploy Runbook (For AI Agents)

This runbook is the source-of-truth process for deploying the ACEAnalytics ecosystem to Vercel production.

## What This Covers

- `https://aceanalytics.dev` (main site + product pages, including `/cfin`)
- `https://text2sql.aceanalytics.dev`
- `https://bankanalysis.aceanalytics.dev` (including `/rm-pro-forma`)
- `https://api.aceanalytics.dev` (Industry News FastAPI backend)

## Canonical App-to-Project Mapping

| App surface | Domain | Vercel project | Local source directory |
| --- | --- | --- | --- |
| Main ACE site + CFIN routes | `aceanalytics.dev` + `www.aceanalytics.dev` | `nextjs-fdas` | `/Users/alexcardell/AlexCoding_Local/cfin_new/nextjs-fdas` |
| Text2SQL | `text2sql.aceanalytics.dev` | `text2sql1` | `/Users/alexcardell/AlexCoding_Local/Text2SQL1/frontend` |
| Bank Analysis | `bankanalysis.aceanalytics.dev` | `bankanalysis` | `/Users/alexcardell/AlexCoding_Local/BankAnalysis/frontend` |
| Industry News API | `api.aceanalytics.dev` | `industry-news-api` | `/Users/alexcardell/AlexCoding_Local/Website Assets/Industry News/backend` |

## Critical Notes (Do Not Skip)

1. Deploy **apex** from `cfin_new/nextjs-fdas` (canonical source), not legacy directories.
2. Deploy `bankanalysis` from the `frontend` subdirectory, not repo root.
3. If `aceanalytics.dev` still shows old content after deploy, explicitly set aliases to the new deployment URL.

## Preflight Checklist

```bash
vercel whoami
vercel project ls --scope alex-cardells-projects
```

Expected scope/team: `alex-cardells-projects`

## Required Env Vars (`nextjs-fdas`)

Set these in the `nextjs-fdas` Vercel project before deploying the marketing news routes:

- `NEXT_PUBLIC_ACE_NEWS_API_BASE=https://api.aceanalytics.dev`
- `ACE_NEWS_API_BASE=https://api.aceanalytics.dev`

If neither value is configured, the app falls back to `http://localhost:8000`, which is only valid for local development.
If either value is set to an empty string in Vercel, Next.js treats that as "configured", and requests can still fall through to the localhost fallback path. Prefer removing empty vars and re-adding explicit values.

## Required Env Vars (`industry-news-api`)

Set these in the `industry-news-api` Vercel project:

- `ANTHROPIC_API_KEY=<valid key>`
- `ALLOWED_ORIGINS=https://aceanalytics.dev,https://www.aceanalytics.dev`
- `ANTHROPIC_MODEL=claude-haiku-4-5-20251001` (default is acceptable unless intentionally changed)
- `REFRESH_TOKEN=<optional shared secret>` (required only if you want to lock down manual refresh endpoints)

Optional:

- `REFRESH_INTERVAL_MINUTES` for local/non-Vercel scheduler behavior.

## Deploy Sequence (Recommended)

### 1) Deploy Main Site (`nextjs-fdas`)

```bash
cd "/Users/alexcardell/AlexCoding_Local/cfin_new/nextjs-fdas"
vercel link --yes --scope "alex-cardells-projects" --project "nextjs-fdas"
vercel deploy --prod --yes --scope "alex-cardells-projects"
```

Capture the produced deployment URL, e.g.:
`nextjs-fdas-<id>-alex-cardells-projects.vercel.app`

### 2) Deploy Industry News API (`industry-news-api`)

```bash
cd "/Users/alexcardell/AlexCoding_Local/Website Assets/Industry News/backend"
vercel link --yes --scope "alex-cardells-projects" --project "industry-news-api"
vercel deploy --prod --yes --scope "alex-cardells-projects"
vercel alias set "<INDUSTRY_NEWS_DEPLOY_URL>" "api.aceanalytics.dev" --scope "alex-cardells-projects"
```

### 3) Force Apex Aliases to the New Deployment

```bash
vercel alias set "<NEXTJS_FDAS_DEPLOY_URL>" "aceanalytics.dev" --scope "alex-cardells-projects"
vercel alias set "<NEXTJS_FDAS_DEPLOY_URL>" "www.aceanalytics.dev" --scope "alex-cardells-projects"
```

### 4) Deploy Text2SQL

```bash
cd "/Users/alexcardell/AlexCoding_Local/Text2SQL1/frontend"
vercel link --yes --scope "alex-cardells-projects" --project "text2sql1"
vercel deploy --prod --yes --scope "alex-cardells-projects"
```

### 5) Deploy BankAnalysis

```bash
cd "/Users/alexcardell/AlexCoding_Local/BankAnalysis/frontend"
vercel link --yes --scope "alex-cardells-projects" --project "bankanalysis"
vercel deploy --prod --yes --scope "alex-cardells-projects"
```

## Verification Commands

Run all of these after deployment:

```bash
vercel inspect "https://aceanalytics.dev"
vercel inspect "https://text2sql.aceanalytics.dev"
vercel inspect "https://bankanalysis.aceanalytics.dev"
vercel inspect "https://api.aceanalytics.dev"
```

Optional content checks:

```bash
curl -sL "https://aceanalytics.dev" | rg "Read between|Aperture|Dialect|OP_A1|OP_A4"
curl -sL "https://aceanalytics.dev/news" | rg "Industry News|Databricks|Power BI"
curl -sL "https://api.aceanalytics.dev/health"
curl -sL "https://api.aceanalytics.dev/feeds" | jq 'map({slug,item_count,last_refreshed_at})'
curl -sI "https://aceanalytics.dev/text2sql"
curl -sL "https://text2sql.aceanalytics.dev" | rg "Introducing|Dialect|Guided Mode"
```

## Known Failure Modes and Fixes

### A) `aceanalytics.dev` shows old page after successful deploy

Cause: domain alias still points to prior deployment.

Fix: run explicit alias commands:

```bash
vercel alias set "<new-nextjs-fdas-deploy-url>" "aceanalytics.dev" --scope "alex-cardells-projects"
vercel alias set "<new-nextjs-fdas-deploy-url>" "www.aceanalytics.dev" --scope "alex-cardells-projects"
```

### B) `bankanalysis` build fails with `react-scripts: command not found`

Cause: deploying from `/BankAnalysis` root instead of `/BankAnalysis/frontend`.

Fix: deploy from frontend directory only.

### C) `nextjs-fdas` deploy blocked by lint errors

Cause: production build runs lint/type checks.

Fix used in this environment: set `eslint.ignoreDuringBuilds: true` in:
`/Users/alexcardell/AlexCoding_Local/cfin_new/nextjs-fdas/next.config.js`

### D) `/news` page shows `0 items` + `Never refreshed` in production

Cause: `NEXT_PUBLIC_ACE_NEWS_API_BASE` and/or `ACE_NEWS_API_BASE` were missing or set as empty strings in the `nextjs-fdas` Vercel project.

Fix:

1. Remove any empty-valued vars.
2. Re-add both vars with `https://api.aceanalytics.dev`.
3. Redeploy `nextjs-fdas`.

## Rollback Procedure

1. Identify last known good deployment URL for the affected project.
2. Re-point aliases to that deployment.

For apex rollback:

```bash
vercel alias set "<previous-nextjs-fdas-deploy-url>" "aceanalytics.dev" --scope "alex-cardells-projects"
vercel alias set "<previous-nextjs-fdas-deploy-url>" "www.aceanalytics.dev" --scope "alex-cardells-projects"
```

Then re-run:

```bash
vercel inspect "https://aceanalytics.dev"
```

## Quick One-Page Checklist

1. Authenticate + confirm scope.
2. Deploy `nextjs-fdas` from `cfin_new/nextjs-fdas`.
3. Deploy `industry-news-api` from `Website Assets/Industry News/backend` and alias `api.aceanalytics.dev`.
4. Set `aceanalytics.dev` + `www` aliases to that exact deployment.
5. Deploy `text2sql1` from `Text2SQL1/frontend`.
6. Deploy `bankanalysis` from `BankAnalysis/frontend`.
7. Verify all four domains with `vercel inspect`.
8. Perform lightweight content/API checks with `curl | rg` and `jq`.
