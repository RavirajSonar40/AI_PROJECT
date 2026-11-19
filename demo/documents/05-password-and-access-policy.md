# Password and Access Policy — Nova Retail

## Length and composition
Corporate passwords must be at least 16 characters long.
Passwords are not forced to change every 90 days; a change is only required when compromise is suspected.

Long, memorable passphrases are recommended.
Reusing passwords from personal services is forbidden.

## Multi-factor authentication
MFA has been mandatory for all corporate systems since 1 January 2025.
TOTP apps and FIDO2 security keys are supported.
SMS codes are disabled because of SIM-swapping risk.

## Password manager
The company provides a corporate password manager with a shared vault per team.
Production credentials may only live in the vault, never in documents or chat.

## Privileged accounts
Administrator accounts are granted for a maximum of 8 hours and with a logged justification.
Every privileged session is recorded and retained for 180 days.

## Account lockout
After 5 failed attempts the account is locked for 30 minutes.
The service desk unlocks it after verifying identity over a video call.

## Devices
Disks must be encrypted (BitLocker or FileVault) and antivirus must be active.
Devices are enrolled in the corporate MDM; an unenrolled device cannot access email.

## Access reviews
Every quarter managers review their team's access and remove what is no longer needed.
Access not reviewed within 30 days is revoked automatically.

## API keys
API keys rotate every 90 days, are stored in the secrets manager
and are never committed to source code or Git repositories.

## Reporting
Any suspected compromise must be reported immediately to security@novaretail.example
or in the #security-incidents Slack channel.
