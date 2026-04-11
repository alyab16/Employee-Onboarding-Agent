# Acme Corp IT Security Policy

## Password Requirements
- Minimum 14 characters
- Must include uppercase, lowercase, numbers, and special characters
- Passwords must not be reused within the last 12 cycles
- Passwords expire every 90 days
- Use the company-approved password manager (1Password) — do not store passwords in browsers or plain text

## Multi-Factor Authentication (MFA)
MFA is mandatory for all company systems and applications. Approved methods:
- Authenticator app (preferred): Google Authenticator, Authy, 1Password
- Hardware key (required for L4+ and access to production systems): YubiKey 5
- SMS is not an approved MFA method due to SIM-swap risks

## Device Security
- All company-issued devices must have full-disk encryption enabled
- Screen lock activates after 5 minutes of inactivity; password required to unlock
- Do not disable automatic OS updates
- Lost or stolen devices must be reported to IT within 1 hour: it-security@acme.com
- Do not connect to public Wi-Fi without using the company VPN (Tailscale)

## Software Installation
Only software on the approved list may be installed on company devices. To request new software:
1. Submit a request via the IT portal (Jira Service Management)
2. IT reviews within 3 business days
3. Security team approves for L3+ software requests
Unapproved software will be flagged by MDM (Jamf) and may be remotely removed.

## Data Classification
| Level | Examples | Handling |
|---|---|---|
| Public | Marketing materials, job postings | No restrictions |
| Internal | Internal docs, org charts | Do not share externally without approval |
| Confidential | Customer data, financial data, source code | Encrypt in transit and at rest; need-to-know only |
| Restricted | Passwords, private keys, PII | Never share; store in approved vaults only |

## Remote Access
- VPN (Tailscale) is required when accessing internal systems from outside the office
- Do not access company systems from shared or public computers
- Production system access requires VPN + MFA at all times

## Phishing and Social Engineering
- Never click links or open attachments in unexpected emails
- Verify unusual requests from colleagues by calling them directly, not by replying to the email
- Report phishing attempts to security@acme.com immediately
- IT will never ask for your password over email, chat, or phone

## Incident Reporting
Security incidents (suspected breaches, malware, unauthorized access) must be reported to it-security@acme.com within 1 hour of discovery. Include: what happened, when, what systems were involved, and what actions you took.
