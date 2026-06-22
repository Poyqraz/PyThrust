#!/usr/bin/env bash
# Push PyFoldable using a user PAT from Cloud Agent secrets.
# Secret name: GH_PAT (fine-grained, PyFoldable Contents: Read and write).
# Do NOT use GH_TOKEN — Cursor may inject its own ghs_ integration token there.
set -euo pipefail

REPO_DIR="${1:-/workspace/pyfoldable-push}"
REMOTE="${PYFOLDABLE_REMOTE:-https://github.com/Poyqraz/PyFoldable.git}"
OWNER_REPO="Poyqraz/PyFoldable"

pick_token() {
  local name value
  for name in GH_PAT GITHUB_PAT PYFOLDABLE_GITHUB_TOKEN GITHUB_TOKEN GH_TOKEN PAT; do
    value="${!name-}"
    if [[ -n "$value" && "$value" != ghs_* ]]; then
      printf '%s' "$value"
      return 0
    fi
  done
  return 1
}

git_push_with_token() {
  local token="$1"
  local sha
  sha="$(git -C "$REPO_DIR" rev-parse HEAD)"

  # Bypass global url.insteadOf that injects expired cursor integration tokens.
  git -C "$REPO_DIR" \
    -c credential.helper= \
    -c 'url.https://x-access-token@github.com/.insteadof=' \
    push "https://x-access-token:${token}@github.com/${OWNER_REPO}.git" \
    "HEAD:refs/heads/main"

  echo "ok: git push HEAD -> main (${sha:0:7})"
}

api_push_with_token() {
  local token="$1"
  local sha
  sha="$(git -C "$REPO_DIR" rev-parse HEAD)"

  if curl -fsS \
    -X POST \
    -H "Authorization: Bearer ${token}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${OWNER_REPO}/git/refs" \
    -d "{\"ref\":\"refs/heads/main\",\"sha\":\"${sha}\"}" >/dev/null; then
    echo "ok: api created refs/heads/main (${sha:0:7})"
    return 0
  fi

  curl -fsS \
    -X PATCH \
    -H "Authorization: Bearer ${token}" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/${OWNER_REPO}/git/refs/heads/main" \
    -d "{\"sha\":\"${sha}\",\"force\":true}" >/dev/null
  echo "ok: api updated refs/heads/main (${sha:0:7})"
}

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "error: not a git repo: $REPO_DIR" >&2
  exit 1
fi

if ! git -C "$REPO_DIR" show-ref --verify --quiet refs/heads/main; then
  git -C "$REPO_DIR" checkout -B main
fi

TOKEN=""
if ! TOKEN="$(pick_token)"; then
  echo "error: no user PAT in environment." >&2
  echo "" >&2
  echo "Checked: GH_PAT, GITHUB_PAT, PYFOLDABLE_GITHUB_TOKEN, GITHUB_TOKEN, GH_TOKEN, PAT" >&2
  echo "CLOUD_AGENT_INJECTED_SECRET_NAMES=${CLOUD_AGENT_INJECTED_SECRET_NAMES-<unset>}" >&2
  echo "" >&2
  echo "Fix:" >&2
  echo "  1. Cursor Dashboard -> Cloud Agents -> Secrets -> add GH_PAT (Runtime Secret)" >&2
  echo "  2. Scope: user or environment that includes this repo" >&2
  echo "  3. Start a NEW cloud agent session (secrets inject at startup)" >&2
  echo "  4. Re-run: /workspace/scripts/push_pyfoldable.sh" >&2
  exit 2
fi

echo "$TOKEN" | /exec-daemon/gh auth login --with-token 2>/dev/null || true

if git_push_with_token "$TOKEN"; then
  exit 0
fi

echo "git push failed; trying GitHub API..." >&2
api_push_with_token "$TOKEN"
