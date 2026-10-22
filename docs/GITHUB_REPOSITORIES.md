# GitHub repository sources

The normal CLI and local dashboard accept either an existing local directory or a GitHub repository source. This is separate from Aposma's GitHub App pull-request webhook.

## Supported input

Use a repository-root URL such as:

```text
https://github.com/owner/repository
```

The shorthand `owner/repository` is also supported. A GitHub URL copied from a repository subpage is reduced to its owner/repository root, and the default branch is cloned. Use the root repository URL to make the chosen source unambiguous.

For example:

```bash
python -m codelens.cli review https://github.com/owner/repository --no-ai
python -m codelens.cli docs owner/repository --no-ai
```

## Where the checkout goes

Aposma keeps GitHub clones on disk so output is not lost when an API request returns:

```text
~/.local/share/aposma/workspaces/<owner>/<repository>/
```

Set `APOSMA_WORKSPACE_DIR` to use another workspace root. Documentation for a GitHub checkout is therefore written to that checkout's `.aposma/docs/` directory.

Existing local checkouts are reused without a forced reset or automatic pull. This avoids discarding local modifications. To refresh one, inspect its working tree, then run `git -C /path/to/workspace pull`.

## Public and private repositories

Public repository clones do not need a token. For private repositories, set `APOSMA_GITHUB_TOKEN` to a token that has read access to the target repository, or configure Git credentials on the system. Use least-privilege permissions. Do not commit the token, paste it into a source file, or place it directly in the repository URL.

The implementation supplies token authentication to Git using an environment-based HTTP header instead of embedding credentials in the URL.

## Limits and privacy

GitHub repository source support runs `git clone` locally; after cloning, analysis and documentation generation run on the local machine. The repository is not uploaded to Aposma's own service. If Ollama is enabled, the extracted evidence package is sent to the local Ollama endpoint configured by `APOSMA_OLLAMA_URL`.

Aposma currently analyzes C++ source files with its native analyzer. A successful clone does not mean repositories in other languages can be analyzed.
