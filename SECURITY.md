# Security Policy

## Reporting a Vulnerability

We take the security of Synkora seriously. If you discover a security vulnerability, please report it responsibly.

**Please do NOT create a public GitHub issue for security vulnerabilities.**

### How to Report

Please use **GitHub's private security advisory** feature: go to the repository → Security → Advisories → "Report a vulnerability".

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to Expect

- Acknowledgment within 48 hours
- Regular updates on progress
- Credit in release notes (unless you prefer to remain anonymous)

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| < Latest| :x:                |

## Security Best Practices

When using Synkora:
- Keep dependencies updated
- Use environment variables for secrets
- Enable authentication for production
- Use HTTPS in production
- Regularly review access logs
- Follow principle of least privilege
- Implement rate limiting
- Use secure session management

## Security Features

Synkora includes:
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection
- Secure password hashing
- JWT token authentication
- Role-based access control (RBAC)
- Secure file upload handling
- API rate limiting
