# 301-karriere-seraph-it

Career site for Seraph IT — built with Hugo.

**Live**: https://karriere.seraph-it.de (Sprint-3+)
**Preview**: none. The repo has no Pages build, and GitHub is only a read mirror of Gitea.

## Structure

```
content/jobs/    — Job postings as Markdown (Hugo content)
layouts/         — Minimal career theme (no external dependencies)
hugo.toml        — Site config
```

## Build

```bash
hugo --minify
```

## Integration

Job Postings are exported from ERPNext (`420-erpnext-SeraphIT`) via the
`Job Posting Render` Doctype. Each render generates Hugo-compatible
Markdown with YAML frontmatter.

Config: `Career Site Setting` Singleton in recruiting_extension.

Since 22.11.2026 `bin/karriere_feed.py` pulls the signed career feed
(`recruiting_extension.api.career_feed.get_career_feed`, contract v1) into
`content/jobs/`. Without `--schreiben` it only shows what would change. It writes
only after the HMAC check (`CAREER_FEED_HMAC_SECRET`, same value as site_config
`recruiting_career_feed_hmac_secret`, kept in Keeper) and never deletes: jobs that
leave the feed become `draft: true`. Hand-written files without
`quelle: "erpnext-feed"` stay untouched. In 420 the feed is off until
`recruiting_career_feed_enabled` is set.

## Sprint-2 Stub Jobs

- SOC-Analyst (Umschulung / Quereinstieg)
- IT-Helpdesk-Techniker (1st/2nd Level)
- Senior Network Engineer (Cisco / FortiGate)
- Backend-Engineer Python / ERPNext
- Werkstudent IT-Security (SOC / Vulnerability Management)

## Cross-Repo

- **020-network-baselines**: TLS-Cert pre-ping (Sprint-3)
- **042-gitea**: Reverse-Proxy pre-ping (Sprint-3)
- **420-erpnext-SeraphIT**: recruiting_extension integration

## Secret scan (gitleaks)

CI runs gitleaks over the history of HEAD, i.e. the checked-out commit and its ancestors
(`--log-opts=HEAD`). Other branches are not scanned, so a PR only reports what it brings in
or what is already on the target branch. PRs and main run the same command.

Keeper record UIDs are references to a vault entry, not secrets. `.gitleaks.toml` therefore
allows exactly one value of 22 characters `[A-Za-z0-9_-]` directly behind a key ending in
`_UID` or `_uid`, in any case. Every other rule is unchanged. This repo has no
`.gitleaksignore`.

`tests/gitleaks/test-gitleaks-rules.sh` pins this down and runs in the CI gitleaks job:
GitHub PAT, AWS key, private key and values behind `token:` or `password:` fire, the UID
does not, and without the UID rule it fires again.
