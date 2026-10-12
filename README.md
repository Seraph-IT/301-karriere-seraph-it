# 301-karriere-seraph-it

Career site for Seraph IT — built with Hugo.

**Live**: https://karriere.seraph-it.de (Sprint-3+)
**Preview**: GitHub Pages (Sprint-2 V1)

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
