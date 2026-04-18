# Security Policy

## Privacy posture

dictate processes all audio locally. The app does not transmit audio, transcriptions, or telemetry to any server. The Python sidecar binds strictly to `127.0.0.1` and is never exposed on the network.

If you find any behavior that violates this posture, please report it as a security issue.

## Reporting a vulnerability

**Please do not open a public issue for security reports.**

Use GitHub's private vulnerability reporting:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability**.
3. Describe the issue with enough detail to reproduce — affected version, steps, expected vs. actual behavior.

You should receive an acknowledgment within a few days. Once a fix is ready, I'll coordinate disclosure with you.

## Scope

In scope:

- Issues that cause dictate to leak audio, transcriptions, or settings off the local machine.
- Privilege escalation via the sidecar, hotkey backends, or auto-paste mechanism.
- Supply-chain concerns in the build or release process.

Out of scope:

- Vulnerabilities in third-party dependencies (report those upstream; feel free to file a non-sensitive issue asking for a version bump).
- Issues that require the attacker to already have local code execution as the user.
