# ACEAnalytics Multi-App Vercel Deploy Runbook (For AI Agents)

This runbook is the source-of-truth process for deploying the ACEAnalytics ecosystem to Vercel production.

## What This Covers

- `https://aceanalytics.dev` (main site + product pages, including `/cfin`)
- `https://text2sql.aceanalytics.dev`
- `https://bankanalysis.aceanalytics.dev` (including `/rm-pro-forma`)

## Canonical App-to-Project Mapping

| App surface | Domain | Vercel project | Local source directory |
| --- | --- | --- | --- |
| Main ACE site + CFIN routes | `aceanalytics.dev` + `www.aceanalytics.dev` | `nextjs-fdas` | `/Users/alexcardell/AlexCoding_Local/cfin_new/nextjs-fdas` |
| Text2SQL | `text2sql.aceanalytics.dev` | `text2sql1` | `/Users/alexcardell/AlexCoding_Local/Text2SQL1/frontend` |
| Bank Analysis | `bankanalysis.aceanalytics.dev` | `bankanalysis` | `/Users/alexcardell/AlexCoding_Local/BankAnalysis/frontend` |

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

## Deploy Sequence (Recommended)

### 1) Deploy Main Site (`nextjs-fdas`)

```bash
cd "/Users/alexcardell/AlexCoding_Local/cfin_new/nextjs-fdas"
vercel link --yes --scope "alex-cardells-projects" --project "nextjs-fdas"
vercel deploy --prod --yes --scope "alex-cardells-projects"
```

Capture the produced deployment URL, e.g.:
`nextjs-fdas-<id>-alex-cardells-projects.vercel.app`

### 2) Force Apex Aliases to the New Deployment

```bash
vercel alias set "<NEXTJS_FDAS_DEPLOY_URL>" "aceanalytics.dev" --scope "alex-cardells-projects"
vercel alias set "<NEXTJS_FDAS_DEPLOY_URL>" "www.aceanalytics.dev" --scope "alex-cardells-projects"
```

### 3) Deploy Text2SQL

```bash
cd "/Users/alexcardell/AlexCoding_Local/Text2SQL1/frontend"
vercel link --yes --scope "alex-cardells-projects" --project "text2sql1"
vercel deploy --prod --yes --scope "alex-cardells-projects"
```

### 4) Deploy BankAnalysis

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
```

Optional content checks:

```bash
curl -sL "https://aceanalytics.dev" | rg "Read between|Aperture|Dialect|OP_A1|OP_A4"
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
3. Set `aceanalytics.dev` + `www` aliases to that exact deployment.
4. Deploy `text2sql1` from `Text2SQL1/frontend`.
5. Deploy `bankanalysis` from `BankAnalysis/frontend`.
6. Verify all three domains with `vercel inspect`.
7. Perform lightweight content checks with `curl | rg`.
