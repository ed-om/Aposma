# Aposma Threat Model

## Assets

- source code
- GitHub installation token
- webhook secret
- model prompts and outputs
- local database

## Threats

- malicious repository code executed during tests
- leaked GitHub credentials
- source code accidentally logged
- prompt injection through comments or source strings
- model hallucination

## Controls

- local inference by default
- webhook HMAC verification
- no credentials in repository
- containerized test execution
- explicit timeouts
- deterministic analyzer facts separated from model text
- evidence shown with findings
