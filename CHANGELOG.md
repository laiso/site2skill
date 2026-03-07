# Changelog

## 0.1.1 - 2026-03-07

- Restrict recursive crawling to the starting URL scope instead of the whole domain.
- Reject localization-only query variants such as `hl`, `lang`, and `locale` during fetch.
- Add fetch-site tests that verify `wget` receives the crawl-scope filters.
