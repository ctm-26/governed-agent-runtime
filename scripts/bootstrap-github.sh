#!/usr/bin/env bash
set -euo pipefail

OWNER="${GITHUB_OWNER:-ctm-26}"
REPO="${GITHUB_REPO:-governed-agent-runtime}"
VISIBILITY="${GITHUB_VISIBILITY:-public}"
DESCRIPTION="A governed continual-learning runtime for AI agents, built around verified outcomes and non-expansive authority."

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v gh >/dev/null || { echo "GitHub CLI (gh) is required" >&2; exit 1; }
gh auth status >/dev/null

python3 scripts/check-repo.py

if [[ ! -d .git ]]; then
  git init -b main
fi

git add .
if ! git diff --cached --quiet; then
  git commit -s -m "chore: bootstrap governed agent runtime"
fi

if gh repo view "${OWNER}/${REPO}" >/dev/null 2>&1; then
  echo "Repository ${OWNER}/${REPO} already exists; not recreating it."
else
  case "${VISIBILITY}" in
    public) visibility_flag="--public" ;;
    private) visibility_flag="--private" ;;
    *) echo "GITHUB_VISIBILITY must be public or private" >&2; exit 1 ;;
  esac
  gh repo create "${OWNER}/${REPO}" "${visibility_flag}" --source=. --remote=origin --description "${DESCRIPTION}" --push
fi

cat <<EOF

Repository content is pushed. Complete the settings in docs/repository-settings.md.
Do not enable a required external approval while there is only one maintainer.
EOF
