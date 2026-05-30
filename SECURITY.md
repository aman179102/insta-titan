# Security Policy

## Supported Versions

| Version | Supported          |
|---------|-------------------|
| 2.x     | :white_check_mark: |
| 1.x     | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please:

1. **Do NOT** open a public issue
2. Send an email to security@instatitan.dev
3. Include detailed steps to reproduce the issue
4. Allow 48 hours for initial response

## Security Features

- PBKDF2-HMAC-SHA256 encrypted credential vault
- Fernet-based session encryption at rest
- Automatic EXIF stripping from uploaded media
- Proxy rotation for anonymized scraping
- User-agent rotation to prevent fingerprinting
- Rate limiting with exponential backoff
- Encrypted configuration storage
- No plaintext passwords in logs or memory dumps

## Best Practices

- Always use environment variables via `.env` for secrets
- Enable proxy rotation when scraping at scale
- Rotate session files periodically
- Review scheduled posts before auto-publishing
- Keep dependencies updated via `pip-audit`
