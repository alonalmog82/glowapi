# GlowAPI

> Turn your GitOps repo into an API.

[![CI](https://github.com/alonalmog82/glowapi/actions/workflows/ci.yml/badge.svg)](https://github.com/alonalmog82/glowapi/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

GlowAPI is a self-hosted API service that sits between your applications and your GitOps repositories. Send a JSON request; GlowAPI creates a branch, renders a template that already lives in your repo, commits the result alongside a machine-readable sidecar, opens a pull request, and notifies you when it merges — without bypassing your existing review workflow.

Works with **GitHub** and **Bitbucket Cloud**. Designed to run as a single Kubernetes pod.

---

## How it works

```
Your service  ──POST /create-pr──►  GlowAPI  ──branch + commit──►  GitHub / Bitbucket
                                                    │                       │
                                                    │◄── webhook (merged) ──┘
                                                    │
                                      POST callback_url ──► Your service
```

1. You send a request describing what to create: which repo, which template, target path, substitution values, and an optional callback URL.
2. GlowAPI reads the template from the repo, applies your substitutions, and commits the rendered file plus a JSON sidecar to a new branch.
3. GlowAPI opens a pull request.
4. When the PR merges (or is declined), GlowAPI delivers a webhook callback to your registered URL.
5. You can also call `/update` later — GlowAPI reads the sidecar from `main`, merges your new values, and opens a new PR with the diff.

---

## Quickstart

```bash
docker run -p 8080:8080 \
  -e GITHUB_CLIENT_ID=your-app-client-id \
  -e GITHUB_APP_INSTALLATION_ID=your-installation-id \
  -e JWT_TOKEN="$(cat your-private-key.pem)" \
  ghcr.io/alonalmog82/glowapi:latest
```

API docs available at `http://localhost:8080/docs`.

---

## API Reference

### `POST /api/v1/gitops/create-pr`

Full flow: create branch → render template → commit files → open PR.

```json
{
  "provider": "github",
  "repo_name": "myorg/my-infra-repo",
  "branch_name": "add/customer-a/vpn",
  "base_branch": "main",
  "template_file": "templates/vpn/customer.tpl",
  "target_file": "customers/customer-a/vpn.tf",
  "substitutions": {
    "customer_name": "customer-a",
    "region": "us-east-1"
  },
  "pr_title": "Add VPN config for customer-a",
  "pr_body": "Provisioned via GlowAPI",
  "callback_url": "https://my-service/glowapi-callback"
}
```

**Response:**
```json
{
  "branch_name": "add/customer-a/vpn",
  "pr_url": "https://github.com/myorg/my-infra-repo/pull/42",
  "pr_id": "42",
  "target_file": "customers/customer-a/vpn.tf",
  "sidecar_file": "customers/customer-a/vpn.tf.json"
}
```

### `POST /api/v1/gitops/branch`

Create branch and commit files only — no PR. Same body as above minus `pr_title`/`pr_body`.

### `POST /api/v1/gitops/update`

Modify an existing managed file. GlowAPI reads the sidecar from `base_branch`, merges your new substitutions over the originals, and opens a new PR.

```json
{
  "provider": "github",
  "repo_name": "myorg/my-infra-repo",
  "target_file": "customers/customer-a/vpn.tf",
  "new_substitutions": { "region": "eu-west-1" },
  "branch_name": "update/customer-a/region",
  "pr_title": "Update region for customer-a"
}
```

**Response** includes `applied_substitutions` — the full merged map — for caller verification.

### `GET /api/v1/gitops/status`

Poll PR state.

```
GET /api/v1/gitops/status?provider=github&repo_name=myorg/my-infra-repo&branch_name=add/customer-a/vpn
```

**Response:**
```json
{ "state": "MERGED", "pr_url": "...", "pr_id": "42", "branch_name": "...", "repo_name": "..." }
```

States: `OPEN` | `MERGED` | `DECLINED` | `UNKNOWN`

### `POST /api/v1/webhooks/github` / `POST /api/v1/webhooks/bitbucket`

Receive PR webhooks from GitHub or Bitbucket. When a registered PR merges or is declined, GlowAPI POSTs to the `callback_url` you provided at creation time:

```json
{
  "event": "PR_MERGED",
  "pr_id": "42",
  "pr_url": "https://github.com/...",
  "branch_name": "add/customer-a/vpn",
  "repo_name": "myorg/my-infra-repo",
  "provider": "github"
}
```

---

## Template Format

Templates use `{{key}}` double-brace markers. This is intentionally different from Python's `str.format()` and safe alongside Terraform HCL (which uses `${}` for interpolation).

```hcl
# templates/vpn/customer.tpl
module "{{customer_name}}" {
  source = "../module"
  region = "{{region}}"
}
```

Unresolved markers are left as-is. Missing keys in the template are silently ignored.

---

## Sidecar JSON

Every committed file gets a companion `{target_file}.json` on the same branch:

```
customers/customer-a/vpn.tf        ← rendered Terraform
customers/customer-a/vpn.tf.json   ← original request payload
```

The sidecar is what makes `/update` possible — GlowAPI reconstructs the previous state from `main` without a database. After each PR merges, the sidecar on `main` reflects the currently-deployed configuration.

---

## Configuration

Copy `config.env.example` to `config.env` and fill in your values.

| Variable | Required | Description |
|---|---|---|
| `GITHUB_CLIENT_ID` | For GitHub | GitHub App Client ID |
| `GITHUB_APP_INSTALLATION_ID` | For GitHub | GitHub App Installation ID |
| `JWT_TOKEN` | For GitHub | Raw PEM private key (preserve newlines) |
| `GITHUB_WEBHOOK_SECRET` | Optional | Validates incoming GitHub webhooks |
| `BITBUCKET_WORKSPACE_TOKEN` | For Bitbucket | Workspace Access Token |
| `BITBUCKET_WEBHOOK_SECRET` | Optional | Validates incoming Bitbucket webhooks |
| `APP_PORT` | No | Default: `8080` |
| `APP_WORKERS` | No | Default: `1` |
| `LOG_LEVEL` | No | `10`=DEBUG, `20`=INFO. Default: `20` |

### GitHub App setup

1. Create a GitHub App at `github.com/settings/apps/new`
2. Grant permissions: Contents (read/write), Pull Requests (read/write)
3. Install the app on your organization
4. Note the Client ID and Installation ID
5. Generate a private key and set its content as `JWT_TOKEN`

### Bitbucket Workspace Token setup

1. Go to Workspace Settings → Access Tokens
2. Create a token with Repositories (read/write) and Pull Requests (read/write) scopes
3. Set as `BITBUCKET_WORKSPACE_TOKEN`

### Webhook setup (optional, for push callbacks)

**GitHub:** In your repo/org settings, add a webhook pointing to `https://your-glowapi/api/v1/webhooks/github`. Set a secret and configure it as `GITHUB_WEBHOOK_SECRET`. Subscribe to Pull Request events.

**Bitbucket:** In Repository Settings → Webhooks, add `https://your-glowapi/api/v1/webhooks/bitbucket`. Subscribe to Pull Request events.

---

## Deployment (Kubernetes)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: glowapi
spec:
  replicas: 1
  selector:
    matchLabels:
      app: glowapi
  template:
    metadata:
      labels:
        app: glowapi
    spec:
      containers:
        - name: glowapi
          image: ghcr.io/alonalmog82/glowapi:latest
          ports:
            - containerPort: 8080
          envFrom:
            - secretRef:
                name: glowapi-secrets
          livenessProbe:
            httpGet:
              path: /healthcheck
              port: 8080
```

> **Note:** The in-memory callback store is lost on pod restart. If you need durable callbacks, use `replicas: 1` and a `PodDisruptionBudget`, or replace the store with Redis.

---

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/ -v
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup (venv, dependencies, running tests) and PR guidelines.

---

## License

[MIT](LICENSE)
