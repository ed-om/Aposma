# Aposma Threat Model

## Assets

- local or cloned source code
- GitHub repository token / short-lived GitHub App installation token
- webhook secret
- model evidence, prompts, and outputs
- generated Markdown and the local SQLite history database

## Threats

- malicious repository code executed during build/test commands
- leaked GitHub credentials
- source code accidentally logged
- prompt injection through comments or source strings
- model hallucination or unsupported documentation claims
- destructive changes to an existing checkout
- unwanted access to local files through a remotely exposed development API

## Controls and operating assumptions

- Repository clones and analysis run locally; no repository is uploaded to an Aposma-hosted service.
- GitHub token authentication is sent using Git's environment-based HTTP extra header, not embedded in the clone URL.
- Existing GitHub checkouts are reused without automatic reset/pull; refresh is explicit so local modifications are not silently overwritten.
- The native analyzer is a structural analyzer, not a sandbox for executing repository code. Aposma does not automatically run project test/build scripts as part of review.
- Webhook signatures are verified with HMAC before handling pull-request payloads.
- Analyzer and model calls have timeouts.
- Deterministic analyzer observations remain distinct from optional AI notes.
- Generated Markdown includes evidence and limitations; it should be reviewed before treating it as authoritative.
- Bind the FastAPI service to loopback (`127.0.0.1`). Do not expose a development instance to an untrusted network, because it can read caller-selected local repository paths.
- Never commit real tokens, private keys, webhook secrets, local databases, or environment files.
