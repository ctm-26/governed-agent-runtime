#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

OWNER="${GITHUB_OWNER:-ctm-26}"
REPO="${GITHUB_REPO:-governed-agent-runtime}"
HOST="${GITHUB_HOST:-github.com}"
VISIBILITY="${GITHUB_VISIBILITY:-public}"
BRANCH="${GITHUB_BRANCH:-main}"
DESCRIPTION="${GITHUB_DESCRIPTION:-A governed continual-learning runtime for AI agents, built around verified outcomes and non-expansive authority.}"
DRY_RUN="${BOOTSTRAP_DRY_RUN:-0}"

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap-github.sh [--dry-run]

Safely initialize and publish this repository. Re-running the command reuses
the local commit, Git remote, and GitHub repository that already exist.

Options:
  --dry-run  Inspect authentication and state, but make no local or remote changes.
  -h, --help Show this help.

Environment:
  GITHUB_OWNER       Repository owner (default: ctm-26)
  GITHUB_REPO        Repository name (default: governed-agent-runtime)
  GITHUB_HOST        GitHub host (default: github.com)
  GITHUB_VISIBILITY  public or private (default: public)
  GITHUB_BRANCH      Initial branch (default: main)
  BOOTSTRAP_DRY_RUN  Set to 1 for dry-run behavior.
EOF
}

note() {
  printf '%s\n' "$*"
}

plan() {
  printf 'DRY-RUN: %s\n' "$*"
}

fail() {
  local message="$1"
  local recovery="${2:-}"

  printf 'ERROR: %s\n' "${message}" >&2
  if [[ -n "${recovery}" ]]; then
    printf '\nRecovery:\n%b\n' "${recovery}" >&2
  fi
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail \
    "$1 is required." \
    "Install $1, then rerun scripts/bootstrap-github.sh."
}

git_network() {
  GIT_TERMINAL_PROMPT=0 git \
    -c credential.helper= \
    -c 'credential.helper=!gh auth git-credential' \
    "$@"
}

refuse_active_hooks() {
  local operation="$1"
  shift
  local hook_name
  local hook_path

  for hook_name in "$@"; do
    if ! hook_path="$(git rev-parse --git-path "hooks/${hook_name}" 2>&1)"; then
      fail \
        "Could not inspect the ${hook_name} hook before ${operation}." \
        "Git reported:\n${hook_path}\n\nInspect core.hooksPath and the Git metadata yourself, then rerun."
    fi
    if [[ -x "${hook_path}" ]]; then
      fail \
        "Active Git hook ${hook_path} would run during ${operation}; the bootstrap will not bypass it or risk letting it modify existing work." \
        "Run the ${operation} manually so you can review the hook's behavior, then rerun scripts/bootstrap-github.sh. The resulting state will be detected and reused."
    fi
  done
}

lowercase() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

scope_is_present() {
  local requested="$1"
  case ",${AUTH_SCOPES}," in
    *,"${requested}",*) return 0 ;;
    *) return 1 ;;
  esac
}

remote_slug() {
  local url="$1"
  local value

  value="${url%/}"
  value="${value%.git}"
  case "${value}" in
    "https://${HOST}/"*) value="${value#https://${HOST}/}" ;;
    "ssh://git@${HOST}/"*) value="${value#ssh://git@${HOST}/}" ;;
    "git@${HOST}:"*) value="${value#git@${HOST}:}" ;;
    *) value="" ;;
  esac
  lowercase "${value}"
}

remote_matches_target() {
  local url="$1"
  local expected_url="$2"
  local actual_slug

  if [[ "${url%/}" == "${expected_url%/}" ]] ||
     [[ "${url%.git}" == "${expected_url%.git}" ]]; then
    return 0
  fi

  actual_slug="$(remote_slug "${url}")"
  [[ -n "${actual_slug}" && "${actual_slug}" == "${TARGET_LOWER}" ]]
}

remote_has_only_target_urls() {
  local remote_name="$1"
  local expected_url="$2"
  local fetch_urls
  local fetch_url
  local push_urls
  local push_url
  local mirror_value

  REMOTE_MISMATCH_URL=""
  if mirror_value="$(git config --bool --get "remote.${remote_name}.mirror" 2>&1)"; then
    if [[ "${mirror_value}" == "true" ]]; then
      REMOTE_MISMATCH_URL="<remote ${remote_name} is configured as a mirror>"
      return 1
    fi
  else
    mirror_status=$?
    if [[ "${mirror_status}" -ne 1 ]]; then
      REMOTE_MISMATCH_URL="${mirror_value}"
      return 1
    fi
  fi

  if ! fetch_urls="$(git remote get-url --all "${remote_name}" 2>&1)"; then
    REMOTE_MISMATCH_URL="${fetch_urls}"
    return 1
  fi
  if [[ -z "${fetch_urls}" ]]; then
    REMOTE_MISMATCH_URL="<no fetch URL configured>"
    return 1
  fi
  while IFS= read -r fetch_url; do
    [[ -z "${fetch_url}" ]] && continue
    if ! remote_matches_target "${fetch_url}" "${expected_url}"; then
      REMOTE_MISMATCH_URL="${fetch_url}"
      return 1
    fi
  done <<<"${fetch_urls}"

  if ! push_urls="$(git remote get-url --push --all "${remote_name}" 2>&1)"; then
    REMOTE_MISMATCH_URL="${push_urls}"
    return 1
  fi
  if [[ -z "${push_urls}" ]]; then
    REMOTE_MISMATCH_URL="<no push URL configured>"
    return 1
  fi
  while IFS= read -r push_url; do
    [[ -z "${push_url}" ]] && continue
    if ! remote_matches_target "${push_url}" "${expected_url}"; then
      REMOTE_MISMATCH_URL="${push_url}"
      return 1
    fi
  done <<<"${push_urls}"

  return 0
}

direct_url_is_safe() {
  local url="$1"
  local expected_url="$2"
  local resolved_fetch
  local resolved_push
  local local_push_rewrites

  REMOTE_MISMATCH_URL=""
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if local_push_rewrites="$(git config --local --get-regexp '^url\..*\.pushInsteadOf$' 2>&1)"; then
      REMOTE_MISMATCH_URL="local pushInsteadOf configuration requires review: ${local_push_rewrites}"
      return 1
    else
      local_config_status=$?
      if [[ "${local_config_status}" -ne 1 ]]; then
        REMOTE_MISMATCH_URL="${local_push_rewrites}"
        return 1
      fi
    fi
    if ! resolved_fetch="$(git ls-remote --get-url "${url}" 2>&1)"; then
      REMOTE_MISMATCH_URL="${resolved_fetch}"
      return 1
    fi
  else
    if ! resolved_fetch="$(git \
      --git-dir="${URL_CHECK_GIT_DIR}" \
      ls-remote --get-url "${url}" 2>&1)"; then
      REMOTE_MISMATCH_URL="${resolved_fetch}"
      return 1
    fi
  fi
  if ! remote_matches_target "${resolved_fetch}" "${expected_url}"; then
    REMOTE_MISMATCH_URL="${resolved_fetch}"
    return 1
  fi

  if ! git \
    --git-dir="${URL_CHECK_GIT_DIR}" \
    remote add __bootstrap_target__ "${url}" 2>/dev/null; then
    REMOTE_MISMATCH_URL="<could not configure isolated URL check>"
    return 1
  fi
  if ! resolved_push="$(git \
    --git-dir="${URL_CHECK_GIT_DIR}" \
    remote get-url --push __bootstrap_target__ 2>&1)"; then
    REMOTE_MISMATCH_URL="${resolved_push}"
    return 1
  fi
  if ! remote_matches_target "${resolved_push}" "${expected_url}"; then
    REMOTE_MISMATCH_URL="${resolved_push}"
    return 1
  fi

  return 0
}

make_external_temp_dir() {
  local base
  local candidate
  local canonical

  for base in /tmp /var/tmp; do
    [[ -d "${base}" && -w "${base}" ]] || continue
    if ! candidate="$(mktemp -d "${base}/governed-agent-bootstrap.XXXXXX")"; then
      continue
    fi
    canonical="$(cd -- "${candidate}" && pwd -P)"
    if [[ "${canonical}/" == "${ROOT_DIR}/"* ]]; then
      rm -r -- "${candidate}"
      continue
    fi
    printf '%s\n' "${canonical}"
    return 0
  done

  return 1
}

query_repository() {
  local output
  local error_output

  if gh api \
    --hostname "${HOST}" \
    "repos/${TARGET}" \
    --jq '[.full_name, .clone_url, .visibility, (.permissions.push // false)] | @tsv' \
    >"${TEMP_STATE_DIR}/repository.out" \
    2>"${TEMP_STATE_DIR}/repository.err"; then
    output="$(<"${TEMP_STATE_DIR}/repository.out")"
    REPOSITORY_EXISTS=1
    IFS=$'\t' read -r REPOSITORY_FULL_NAME REPOSITORY_URL REPOSITORY_VISIBILITY REPOSITORY_CAN_PUSH <<<"${output}"
    if [[ -z "${REPOSITORY_FULL_NAME}" ||
          -z "${REPOSITORY_URL}" ||
          -z "${REPOSITORY_VISIBILITY}" ||
          -z "${REPOSITORY_CAN_PUSH}" ]]; then
      fail \
        "GitHub returned incomplete metadata for ${TARGET}." \
        "Run: gh api --hostname ${HOST} repos/${TARGET}\nThen correct the authentication or repository metadata and rerun."
    fi
    if [[ "$(lowercase "${REPOSITORY_FULL_NAME}")" != "${TARGET_LOWER}" ]]; then
      fail \
        "GitHub resolved ${TARGET} to canonical repository ${REPOSITORY_FULL_NAME}; refusing to follow a rename or transfer implicitly." \
        "Confirm the intended owner and repository. Set GITHUB_OWNER and GITHUB_REPO to the canonical name only after reviewing the existing remotes, then rerun."
    fi
    return
  fi

  error_output="$(<"${TEMP_STATE_DIR}/repository.err")"
  if printf '%s\n' "${error_output}" | grep -Eq '^gh: Not Found \(HTTP 404\)$'; then
    REPOSITORY_EXISTS=0
    REPOSITORY_FULL_NAME=""
    REPOSITORY_URL="https://${HOST}/${TARGET}.git"
    REPOSITORY_VISIBILITY=""
    REPOSITORY_CAN_PUSH=""
    return
  fi

  fail \
    "Could not determine whether ${TARGET} exists; stopping without further GitHub or Git changes." \
    "Run: gh api --hostname ${HOST} repos/${TARGET}\nConfirm whether the repository exists before creating anything manually. Resolve the authentication, network, or API error, then rerun."
}

validate_repository_tree() {
  local validation_root="$1"

  if ! python3 - "${validation_root}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
required = [
    "README.md",
    "LICENSE",
    "NOTICE",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "GOVERNANCE.md",
    "CITATION.cff",
    "docs/project-charter.md",
    "docs/quality-gates.md",
    "docs/threat-model.md",
]
errors: list[str] = []

for relative in required:
    if not (root / relative).is_file():
        errors.append(f"missing required file: {relative}")

schema_root = root / "spec" / "schemas"
for path in sorted(schema_root.glob("*.json")):
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid JSON in {path.relative_to(root)}: {exc}")

if errors:
    print("Repository checks failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    raise SystemExit(1)

print("Repository scaffold checks passed.")
PY
  then
    fail \
      "Repository structural validation failed." \
      "Fix the reported required-file or JSON errors, run python3 scripts/check-repo.py, then rerun. No GitHub repository was created or pushed."
  fi
}

validate_commit_snapshot() {
  local snapshot_ref="$1"
  local archive_path="${TEMP_STATE_DIR}/snapshot-${snapshot_ref}.tar"
  local checkout_path="${TEMP_STATE_DIR}/snapshot-${snapshot_ref}"

  if ! mkdir -- "${checkout_path}"; then
    fail \
      "Could not create an isolated commit-validation directory." \
      "Verify temporary storage under ${TEMP_STATE_DIR}, then rerun. No push was attempted."
  fi
  if ! git archive \
    --format=tar \
    --output="${archive_path}" \
    "${snapshot_ref}"; then
    fail \
      "Could not archive local snapshot ${snapshot_ref} for exact-snapshot validation." \
      "Verify git archive ${snapshot_ref} succeeds, then rerun. No GitHub repository was created or pushed."
  fi
  if ! tar -xf "${archive_path}" -C "${checkout_path}"; then
    fail \
      "Could not unpack local snapshot ${snapshot_ref} for validation." \
      "Verify tar can read ${archive_path}, then rerun. No GitHub repository was created or pushed."
  fi
  validate_repository_tree "${checkout_path}"
}

for argument in "$@"; do
  case "${argument}" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      fail "Unknown argument: ${argument}"
      ;;
  esac
done

case "${DRY_RUN}" in
  0|false|FALSE|no|NO) DRY_RUN=0 ;;
  1|true|TRUE|yes|YES) DRY_RUN=1 ;;
  *) fail "BOOTSTRAP_DRY_RUN must be 0, 1, false, or true." ;;
esac

case "${VISIBILITY}" in
  public|private) ;;
  *) fail "GITHUB_VISIBILITY must be public or private." ;;
esac

if [[ ! "${OWNER}" =~ ^[A-Za-z0-9_.-]+$ ]] ||
   [[ ! "${REPO}" =~ ^[A-Za-z0-9_.-]+$ ]]; then
  fail "GITHUB_OWNER and GITHUB_REPO may contain only letters, numbers, dot, underscore, and hyphen."
fi

if [[ ! "${BRANCH}" =~ ^[A-Za-z0-9._/-]+$ ]] ||
   [[ "${BRANCH}" == -* ]] ||
   [[ "${BRANCH}" == *..* ]]; then
  fail "GITHUB_BRANCH is not a safe branch name: ${BRANCH}"
fi

TARGET="${OWNER}/${REPO}"
TARGET_LOWER="$(lowercase "${TARGET}")"
AUTH_SCOPES=""
REPOSITORY_EXISTS=0
REPOSITORY_FULL_NAME=""
REPOSITORY_URL=""
REPOSITORY_VISIBILITY=""
REPOSITORY_CAN_PUSH=""

require_command git
require_command gh
require_command python3
require_command mktemp
require_command mkdir
require_command tar

cd -- "${ROOT_DIR}"

if ! TEMP_STATE_DIR="$(make_external_temp_dir)"; then
  fail \
    "Could not create a temporary state directory outside the repository." \
    "Ensure /tmp or /var/tmp is writable and outside ${ROOT_DIR}, then rerun. No repository files were staged."
fi
cleanup() {
  if [[ -n "${TEMP_STATE_DIR:-}" &&
        -d "${TEMP_STATE_DIR}" &&
        "${TEMP_STATE_DIR}" == *"/governed-agent-bootstrap."* ]]; then
    rm -rf -- "${TEMP_STATE_DIR}"
  fi
}
trap cleanup EXIT

URL_CHECK_GIT_DIR="${TEMP_STATE_DIR}/url-check.git"
if ! git init --bare --quiet "${URL_CHECK_GIT_DIR}"; then
  fail \
    "Could not initialize the isolated temporary Git URL checker." \
    "Verify that Git can create a bare repository under ${TEMP_STATE_DIR}, then rerun. No project Git state was changed."
fi

if ! git \
  --git-dir="${URL_CHECK_GIT_DIR}" \
  check-ref-format --branch "${BRANCH}" >/dev/null 2>&1; then
  fail "GITHUB_BRANCH is not a valid Git branch name: ${BRANCH}"
fi

AUTH_OUTPUT=""
if ! AUTH_OUTPUT="$(gh auth status --hostname "${HOST}" 2>&1)"; then
  fail \
    "GitHub CLI is not authenticated for ${HOST}; no local or remote resources were changed." \
    "Run: gh auth login --hostname ${HOST} --scopes repo,workflow\nThen verify with: gh auth status --hostname ${HOST}\nRerun this script after authentication succeeds."
fi

if ! gh api \
  --hostname "${HOST}" \
  --include \
  user \
  >"${TEMP_STATE_DIR}/user.out" \
  2>"${TEMP_STATE_DIR}/user.err"; then
  fail \
    "The active GitHub credential could not call the GitHub API; no local or remote resources were changed." \
    "Run: gh api --hostname ${HOST} user\nResolve the authentication or network error, then rerun."
fi

AUTH_API_OUTPUT="$(<"${TEMP_STATE_DIR}/user.out")"
AUTH_SCOPE_LINE="$(printf '%s\n' "${AUTH_API_OUTPUT}" | grep -i '^x-oauth-scopes:' | head -n 1 || true)"
if [[ -n "${AUTH_SCOPE_LINE}" ]]; then
  AUTH_SCOPES="${AUTH_SCOPE_LINE#*:}"
  AUTH_SCOPES="$(printf '%s' "${AUTH_SCOPES}" | tr -d " '" | tr -d '\r\t')"
fi

WORKFLOW_FILES_PRESENT=0
if [[ -L .github/workflows ]]; then
  WORKFLOW_FILES_PRESENT=1
elif [[ -e .github/workflows ]]; then
  if [[ -d .github/workflows ]]; then
    if ! WORKFLOW_SCAN="$(find .github/workflows -mindepth 1 -print -quit 2>&1)"; then
      fail \
        "Could not inspect .github/workflows for the required workflow permission." \
        "Inspect the path and permissions, then rerun. No repository was created."
    fi
    if [[ -n "${WORKFLOW_SCAN}" ]]; then
      WORKFLOW_FILES_PRESENT=1
    fi
  else
    WORKFLOW_FILES_PRESENT=1
  fi
fi

EXISTING_TOPLEVEL=""
EXACT_REPOSITORY=0
if EXISTING_TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  EXISTING_TOPLEVEL="$(cd -- "${EXISTING_TOPLEVEL}" && pwd -P)"
  if [[ "${EXISTING_TOPLEVEL}" == "${ROOT_DIR}" ]]; then
    EXACT_REPOSITORY=1
    if git rev-parse --verify 'HEAD^{commit}' >/dev/null 2>&1; then
      if ! WORKFLOW_TREE="$(git ls-tree -r --name-only HEAD -- .github/workflows 2>&1)"; then
        fail \
          "Could not inspect the committed workflow tree." \
          "Verify git ls-tree -r --name-only HEAD -- .github/workflows succeeds, then rerun. No repository was created."
      fi
      if [[ -n "${WORKFLOW_TREE}" ]]; then
        WORKFLOW_FILES_PRESENT=1
      fi
    fi
  fi
elif [[ -e .git || -L .git ]]; then
  fail \
    "Git metadata exists at ${ROOT_DIR}/.git but cannot be read; refusing to initialize over it." \
    "Repair or inspect the existing Git metadata yourself, verify git rev-parse --show-toplevel succeeds, then rerun. Nothing was initialized or overwritten."
fi

if [[ "${WORKFLOW_FILES_PRESENT}" -eq 1 ]]; then
  if [[ -z "${AUTH_SCOPES}" ]] || ! scope_is_present workflow; then
    fail \
      "The active GitHub credential does not expose the required workflow permission; no repository was created." \
      "Authenticate with a credential that has repository contents write access and workflow-file write access.\nFor GitHub CLI OAuth, run: gh auth refresh --hostname ${HOST} --scopes repo,workflow\nIf GH_TOKEN is set, replace it with an appropriately scoped token, verify with gh auth status, and rerun."
  fi
fi

GIT_READY=0
if [[ "${EXACT_REPOSITORY}" -eq 1 ]]; then
  GIT_READY=1
elif [[ -n "${EXISTING_TOPLEVEL}" ]]; then
  fail \
    "This directory is nested inside a different Git repository: ${EXISTING_TOPLEVEL}" \
    "Move the bootstrap directory outside that repository or initialize it intentionally yourself. No Git state was changed."
else
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    plan "would initialize ${ROOT_DIR} with branch ${BRANCH}"
    LOCAL_COMMIT_PENDING=1
  else
    if ! git init -b "${BRANCH}"; then
      fail \
        "Could not initialize the local Git repository." \
        "Resolve the Git error and rerun. No GitHub repository has been created."
    fi
    GIT_READY=1
    LOCAL_COMMIT_PENDING=0
    if ! GIT_TOPLEVEL="$(git rev-parse --show-toplevel 2>&1)"; then
      fail \
        "Git initialization returned success, but the repository cannot be inspected." \
        "Git reported:\n${GIT_TOPLEVEL}\n\nInspect ${ROOT_DIR}/.git and repair it yourself before rerunning. No GitHub repository was created."
    fi
    GIT_TOPLEVEL="$(cd -- "${GIT_TOPLEVEL}" && pwd -P)"
    if [[ "${GIT_TOPLEVEL}" != "${ROOT_DIR}" ]]; then
      fail \
        "Git initialized an unexpected worktree at ${GIT_TOPLEVEL}." \
        "Inspect the Git metadata and correct it yourself before rerunning. No GitHub repository was created."
    fi
  fi
fi

LOCAL_SHA=""
CURRENT_BRANCH="${BRANCH}"
if [[ "${GIT_READY}" -eq 1 ]]; then
  if ! INSIDE_WORK_TREE="$(git rev-parse --is-inside-work-tree 2>&1)"; then
    fail \
      "Could not confirm that ${ROOT_DIR} is a Git worktree." \
      "Git reported:\n${INSIDE_WORK_TREE}\n\nRepair the Git metadata, verify git rev-parse --is-inside-work-tree prints true, then rerun."
  fi
  if [[ "${INSIDE_WORK_TREE}" != "true" ]]; then
    fail \
      "${ROOT_DIR} is not a Git worktree; refusing to continue." \
      "Inspect the repository layout and run the bootstrap only from a working tree."
  fi
  if ! CURRENT_BRANCH="$(git symbolic-ref --quiet --short HEAD)"; then
    fail \
      "The local repository is in detached HEAD state; refusing to choose a branch or push target." \
      "Create or switch to ${BRANCH}, then rerun. Example: git switch -c ${BRANCH}"
  fi
  if [[ "${CURRENT_BRANCH}" != "${BRANCH}" ]]; then
    fail \
      "Current branch ${CURRENT_BRANCH} does not match configured bootstrap branch ${BRANCH}." \
      "Switch to ${BRANCH}, or explicitly set GITHUB_BRANCH=${CURRENT_BRANCH}. No branch was renamed or overwritten."
  fi

  if LOCAL_SHA="$(git rev-parse --verify 'HEAD^{commit}' 2>/dev/null)"; then
    note "Reusing local commit ${LOCAL_SHA} on ${CURRENT_BRANCH}."
    LOCAL_COMMIT_PENDING=0
    if ! WORKTREE_STATUS="$(git status --porcelain=v1 --untracked-files=all 2>&1)"; then
      fail \
        "Could not inspect the local worktree and index; refusing to assume they are clean." \
        "Git reported:\n${WORKTREE_STATUS}\n\nRepair the Git index or worktree metadata, verify git status succeeds, then rerun. No push was attempted."
    fi
    if [[ -n "${WORKTREE_STATUS}" ]]; then
      fail \
        "Local commit ${LOCAL_SHA} exists, but the worktree or index has uncommitted changes; refusing to validate one snapshot and push another." \
        "Review git status --short. Commit the intended work, or preserve it in another branch/worktree yourself, then rerun. The script did not stage, discard, or overwrite anything."
    fi
  else
    if ! INITIAL_INDEX_ENTRIES="$(git ls-files --stage 2>&1)"; then
      fail \
        "Could not inspect the unborn repository index; refusing to stage over it." \
        "Git reported:\n${INITIAL_INDEX_ENTRIES}\n\nRepair or inspect the index yourself, then rerun."
    fi
    if [[ -n "${INITIAL_INDEX_ENTRIES}" ]]; then
      fail \
        "The unborn repository index already contains entries; refusing to replace or commit them." \
        "Review git ls-files --stage. Commit or restore the intended index yourself, then rerun; the bootstrap did not alter it."
    fi
    if ! git diff --cached --quiet; then
      fail \
        "The unborn repository already has staged work; refusing to alter or commit that index." \
        "Review with git diff --cached. Commit it yourself or restore the intended index, then rerun."
    fi

    validate_repository_tree "${ROOT_DIR}"
    refuse_active_hooks \
      "initial commit" \
      pre-commit \
      prepare-commit-msg \
      commit-msg \
      post-commit

    if [[ "${DRY_RUN}" -eq 1 ]]; then
      plan "would stage the initial repository snapshot and create a DCO-signed bootstrap commit"
      LOCAL_COMMIT_PENDING=1
    else
      if ! git add --all -- .; then
        fail \
          "Could not stage the initial repository snapshot." \
          "Inspect git status. Existing files remain in place; correct the problem and rerun."
      fi
      if git diff --cached --quiet; then
        fail \
          "There is no content to commit." \
          "Restore the repository scaffold, run python3 scripts/check-repo.py, and rerun."
      fi
      if ! INTENDED_TREE="$(git write-tree 2>&1)"; then
        fail \
          "Could not record the intended initial tree before commit." \
          "Git reported:\n${INTENDED_TREE}\n\nInspect the staged index, repair it yourself, then rerun."
      fi
      validate_commit_snapshot "${INTENDED_TREE}"
      if ! git commit -s -m "chore: bootstrap governed agent runtime"; then
        fail \
          "Could not create the initial local commit. The staged snapshot was preserved." \
          "Fix Git author/sign-off configuration, commit the staged snapshot, then rerun. The script will reuse that commit."
      fi
      LOCAL_SHA="$(git rev-parse --verify 'HEAD^{commit}')"
      ACTUAL_TREE="$(git rev-parse --verify 'HEAD^{tree}')"
      if [[ "${ACTUAL_TREE}" != "${INTENDED_TREE}" ]]; then
        fail \
          "A commit hook or Git configuration changed the staged tree during commit; refusing to create or push a GitHub repository." \
          "Inspect git show --stat ${LOCAL_SHA} and git status. The commit was preserved for review; reconcile it deliberately, then rerun."
      fi
      if ! COMMIT_MESSAGE="$(git show -s --format=%B "${LOCAL_SHA}" 2>&1)"; then
        fail \
          "Could not inspect the initial commit message after hooks ran; refusing to push." \
          "Git reported:\n${COMMIT_MESSAGE}\n\nInspect commit ${LOCAL_SHA}, repair it deliberately, then rerun."
      fi
      if ! printf '%s\n' "${COMMIT_MESSAGE}" | grep -Eq '^Signed-off-by: .+ <[^>]+>$'; then
        fail \
          "The initial commit does not contain a DCO sign-off after commit hooks ran; refusing to push." \
          "Inspect git show -s --format=%B ${LOCAL_SHA}. Add a valid sign-off in a deliberate replacement commit, then rerun."
      fi
      LOCAL_COMMIT_PENDING=0
      if ! POST_COMMIT_STATUS="$(git status --porcelain=v1 --untracked-files=all 2>&1)"; then
        fail \
          "The initial commit was created, but worktree verification failed; refusing to create or push a GitHub repository." \
          "Git reported:\n${POST_COMMIT_STATUS}\n\nInspect the preserved commit and Git metadata, repair them yourself, then rerun."
      fi
      if [[ -n "${POST_COMMIT_STATUS}" ]]; then
        fail \
          "The initial commit left uncommitted work; refusing to create or push a different snapshot." \
          "Review git status --short. The commit and working files were preserved; reconcile them deliberately, then rerun."
      fi
      note "Created local commit ${LOCAL_SHA}."
    fi
  fi
fi

if [[ "${LOCAL_COMMIT_PENDING}" -eq 0 ]]; then
  validate_commit_snapshot "${LOCAL_SHA}"
elif [[ "${GIT_READY}" -eq 0 ]]; then
  validate_repository_tree "${ROOT_DIR}"
fi

query_repository

REMOTE_NAME=""
REMOTE_URL=""
if [[ "${GIT_READY}" -eq 1 ]]; then
  if ! REMOTE_LIST="$(git remote 2>&1)"; then
    fail \
      "Could not inspect existing Git remotes; refusing to add or push a remote." \
      "Git reported:\n${REMOTE_LIST}\n\nRepair the Git configuration, verify git remote -v succeeds, then rerun."
  fi
  ORIGIN_PRESENT=0
  for candidate in ${REMOTE_LIST}; do
    if [[ "${candidate}" == "origin" ]]; then
      ORIGIN_PRESENT=1
      break
    fi
  done

  if [[ "${ORIGIN_PRESENT}" -eq 1 ]]; then
    if ! REMOTE_URL="$(git remote get-url origin 2>&1)"; then
      fail \
        "Remote origin exists but its fetch URL cannot be read; refusing to replace it." \
        "Git reported:\n${REMOTE_URL}\n\nRepair origin yourself after inspecting git config, then rerun."
    fi
    if remote_has_only_target_urls origin "${REPOSITORY_URL}"; then
      REMOTE_NAME="origin"
      note "Reusing remote origin (${REMOTE_URL})."
    else
      fail \
        "Remote origin has fetch or push URL ${REMOTE_MISMATCH_URL}, which does not target ${TARGET}; refusing to overwrite it or push elsewhere." \
        "Choose the intended repository explicitly. If origin is wrong, rename or change it yourself after reviewing git remote -v and git remote get-url --push --all origin, then rerun."
    fi
  else
    for candidate in ${REMOTE_LIST}; do
      if ! candidate_url="$(git remote get-url "${candidate}" 2>&1)"; then
        fail \
          "Remote ${candidate} exists but its fetch URL cannot be read; refusing to add another remote." \
          "Git reported:\n${candidate_url}\n\nRepair the existing remote yourself, then rerun."
      fi
      if remote_has_only_target_urls "${candidate}" "${REPOSITORY_URL}"; then
        REMOTE_NAME="${candidate}"
        REMOTE_URL="${candidate_url}"
        note "Reusing remote ${REMOTE_NAME} (${REMOTE_URL})."
        break
      fi
    done
  fi
fi

if [[ -z "${REMOTE_NAME}" ]] &&
   ! direct_url_is_safe "${REPOSITORY_URL}" "${REPOSITORY_URL}"; then
  fail \
    "Git URL rewriting maps ${REPOSITORY_URL} to ${REMOTE_MISMATCH_URL}; refusing to add or push that target." \
    "Inspect git config --show-origin --get-regexp '^url\\..*\\.(insteadOf|pushInsteadOf)$'. Remove or correct the unexpected rewrite yourself, then rerun."
fi

if [[ "${REPOSITORY_EXISTS}" -eq 1 ]]; then
  note "Reusing existing GitHub repository ${TARGET}."
  if [[ "${REPOSITORY_CAN_PUSH}" != "true" ]]; then
      fail \
        "The authenticated GitHub identity does not report push permission for ${TARGET}; no push was attempted." \
      "Run GH_HOST=${HOST} gh repo view ${TARGET} --json viewerPermission and confirm write or admin access. Authenticate with the intended account or obtain access, then rerun."
  fi
  if [[ "${REPOSITORY_VISIBILITY}" != "${VISIBILITY}" ]]; then
    fail \
      "Existing repository ${TARGET} is ${REPOSITORY_VISIBILITY}, but GITHUB_VISIBILITY is ${VISIBILITY}; refusing to change it." \
      "Set GITHUB_VISIBILITY=${REPOSITORY_VISIBILITY} to reuse it, or change visibility deliberately in GitHub and rerun."
  fi
else
  if [[ "${VISIBILITY}" == "private" ]]; then
    REQUIRED_REPOSITORY_SCOPE="repo"
  else
    REQUIRED_REPOSITORY_SCOPE="public_repo"
  fi
  if [[ -z "${AUTH_SCOPES}" ]] ||
     { ! scope_is_present repo && ! scope_is_present "${REQUIRED_REPOSITORY_SCOPE}"; }; then
    fail \
      "The active GitHub credential cannot be confirmed for ${VISIBILITY} repository creation; no repository was created." \
      "Run: gh auth refresh --hostname ${HOST} --scopes repo,workflow\nVerify the scopes with gh auth status --hostname ${HOST}, then rerun."
  fi

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    plan "would create ${VISIBILITY} repository ${TARGET} without adding a remote or pushing"
  else
    if [[ "${VISIBILITY}" == "public" ]]; then
      visibility_flag="--public"
    else
      visibility_flag="--private"
    fi
    if ! create_output="$(GH_HOST="${HOST}" gh repo create "${TARGET}" "${visibility_flag}" --description "${DESCRIPTION}" 2>&1)"; then
      query_repository
      if [[ "${REPOSITORY_EXISTS}" -eq 1 ]]; then
        note "Repository creation returned an error, but ${TARGET} now exists; reusing it."
      else
        fail \
          "GitHub repository creation failed. No existing repository or Git remote was removed." \
          "GitHub reported:\n${create_output}\n\nCheck whether ${TARGET} was created with GH_HOST=${HOST} gh repo view ${TARGET}. Fix the reported problem, then rerun; an existing repository will be reused."
      fi
    fi
    if [[ "${REPOSITORY_EXISTS}" -ne 1 ]]; then
      query_repository
    fi
    if [[ "${REPOSITORY_EXISTS}" -ne 1 ]]; then
      fail \
        "GitHub reported successful creation, but ${TARGET} cannot be read back." \
        "Run GH_HOST=${HOST} gh repo view ${TARGET}. Resolve visibility or access, then rerun; do not recreate the repository manually unless it is confirmed absent."
    fi
    if [[ "${REPOSITORY_CAN_PUSH}" != "true" ]]; then
      fail \
        "Repository ${TARGET} exists, but the authenticated identity does not report push permission." \
        "Inspect GH_HOST=${HOST} gh repo view ${TARGET} --json viewerPermission. Correct access, then rerun; the repository and local commit will be reused."
    fi
    if [[ "${REPOSITORY_VISIBILITY}" != "${VISIBILITY}" ]]; then
      fail \
        "Repository ${TARGET} is ${REPOSITORY_VISIBILITY} after creation/readback, but ${VISIBILITY} was requested; refusing to push." \
        "Inspect GH_HOST=${HOST} gh repo view ${TARGET} --json visibility. Reconcile the visibility deliberately, then rerun; no remote or push was added."
    fi
    note "Repository ${TARGET} is ready; no push has occurred yet."
  fi
fi

if [[ -z "${REMOTE_NAME}" ]]; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    plan "would add remote origin as ${REPOSITORY_URL}"
    REMOTE_REFERENCE="${REPOSITORY_URL}"
  else
    if ! git remote add origin "${REPOSITORY_URL}"; then
      fail \
        "Could not add remote origin. Existing remotes were not changed." \
        "Inspect git remote -v and ${TARGET}, make the intended remote relationship explicit, then rerun."
    fi
    if ! remote_has_only_target_urls origin "${REPOSITORY_URL}"; then
      fail \
        "New remote origin resolves to ${REMOTE_MISMATCH_URL}, not ${TARGET}; refusing to push." \
        "Inspect git remote -v, git remote get-url --all origin, and git remote get-url --push --all origin. The newly added remote was left visible for review; correct or remove it yourself, then rerun."
    fi
    REMOTE_NAME="origin"
    REMOTE_URL="${REPOSITORY_URL}"
    REMOTE_REFERENCE="${REMOTE_NAME}"
    note "Added remote origin (${REMOTE_URL})."
  fi
else
  REMOTE_REFERENCE="${REMOTE_NAME}"
fi

if [[ "${LOCAL_COMMIT_PENDING}" -eq 1 ]]; then
  plan "would push the new local commit to ${TARGET}:${BRANCH} after the commit exists"
  note "Dry run complete; no local or remote state was changed."
  exit 0
fi

if [[ "${DRY_RUN}" -eq 1 && "${REPOSITORY_EXISTS}" -eq 0 ]]; then
  plan "would push ${LOCAL_SHA} as new branch ${TARGET}:${BRANCH} after repository creation"
  note "Dry run complete; no local or remote state was changed."
  exit 0
fi

REMOTE_SHA=""
REMOTE_REF=""
if git_network ls-remote \
  --exit-code \
  "${REMOTE_REFERENCE}" \
  "refs/heads/${BRANCH}" \
  >"${TEMP_STATE_DIR}/ls-remote.out" \
  2>"${TEMP_STATE_DIR}/ls-remote.err"; then
  if ! IFS=$'\t' read -r REMOTE_SHA REMOTE_REF <"${TEMP_STATE_DIR}/ls-remote.out"; then
    fail \
      "Git reported success but returned no remote branch metadata; no push was attempted." \
      "Run git ls-remote ${REMOTE_REFERENCE} refs/heads/${BRANCH}, inspect the remote response, then rerun."
  fi
  if [[ ! "${REMOTE_SHA}" =~ ^[0-9a-fA-F]{40,64}$ ]] ||
     [[ "${REMOTE_REF}" != "refs/heads/${BRANCH}" ]] ||
     [[ -n "$(sed -n '2p' "${TEMP_STATE_DIR}/ls-remote.out")" ]]; then
    fail \
      "Git returned unexpected metadata for ${TARGET}:${BRANCH}; no push was attempted." \
      "Run git ls-remote ${REMOTE_REFERENCE} refs/heads/${BRANCH}, verify the exact ref and object ID, then rerun."
  fi
  if [[ "${REMOTE_SHA}" == "${LOCAL_SHA}" ]]; then
    note "Remote ${BRANCH} already points to ${LOCAL_SHA}; no push is needed."
    if [[ "${DRY_RUN}" -eq 1 ]]; then
      note "Dry run complete; no local or remote state was changed."
    fi
    exit 0
  fi
else
  remote_status=$?
  if [[ "${remote_status}" -ne 2 ]]; then
    remote_error="$(<"${TEMP_STATE_DIR}/ls-remote.err")"
    fail \
      "Could not inspect ${TARGET}:${BRANCH}; no push was attempted." \
      "Git reported:\n${remote_error}\n\nRun: git ls-remote ${REMOTE_REFERENCE} refs/heads/${BRANCH}\nResolve authentication, network, or remote URL errors, then rerun."
  fi
fi

refuse_active_hooks "push" pre-push

UPSTREAM_REMOTE=""
UPSTREAM_MERGE=""
if UPSTREAM_REMOTE="$(git config --get-all "branch.${BRANCH}.remote" 2>&1)"; then
  HAS_UPSTREAM_REMOTE=1
else
  upstream_remote_status=$?
  if [[ "${upstream_remote_status}" -eq 1 ]]; then
    HAS_UPSTREAM_REMOTE=0
    UPSTREAM_REMOTE=""
  else
    fail \
      "Could not inspect the configured upstream remote for ${BRANCH}; no push was attempted." \
      "Git reported:\n${UPSTREAM_REMOTE}\n\nInspect git config --get-all branch.${BRANCH}.remote, repair it yourself, then rerun."
  fi
fi
if UPSTREAM_MERGE="$(git config --get-all "branch.${BRANCH}.merge" 2>&1)"; then
  HAS_UPSTREAM_MERGE=1
else
  upstream_merge_status=$?
  if [[ "${upstream_merge_status}" -eq 1 ]]; then
    HAS_UPSTREAM_MERGE=0
    UPSTREAM_MERGE=""
  else
    fail \
      "Could not inspect the configured upstream branch for ${BRANCH}; no push was attempted." \
      "Git reported:\n${UPSTREAM_MERGE}\n\nInspect git config --get-all branch.${BRANCH}.merge, repair it yourself, then rerun."
  fi
fi

EXPECTED_UPSTREAM_REMOTE="${REMOTE_NAME:-origin}"
EXPECTED_UPSTREAM_MERGE="refs/heads/${BRANCH}"
if [[ "${HAS_UPSTREAM_REMOTE}" -ne "${HAS_UPSTREAM_MERGE}" ]]; then
  fail \
    "Branch ${BRANCH} has incomplete upstream configuration; refusing to overwrite it." \
    "Inspect git config --get-regexp '^branch\\.${BRANCH}\\.(remote|merge)$', correct it yourself, then rerun."
fi
if [[ "${HAS_UPSTREAM_REMOTE}" -eq 1 ]]; then
  if [[ "${UPSTREAM_REMOTE}" != "${EXPECTED_UPSTREAM_REMOTE}" ||
        "${UPSTREAM_MERGE}" != "${EXPECTED_UPSTREAM_MERGE}" ]]; then
    fail \
      "Branch ${BRANCH} tracks ${UPSTREAM_REMOTE}:${UPSTREAM_MERGE}, not ${EXPECTED_UPSTREAM_REMOTE}:${EXPECTED_UPSTREAM_MERGE}; refusing to overwrite it." \
      "Review git status --short --branch and the branch upstream. Change it deliberately yourself if ${EXPECTED_UPSTREAM_REMOTE}/${BRANCH} is intended, then rerun."
  fi
  SET_UPSTREAM=0
else
  SET_UPSTREAM=1
fi

if ! push_preview="$(git_network \
  -c push.followTags=false \
  push \
  --dry-run \
  --no-verify \
  --no-follow-tags \
  --recurse-submodules=no \
  "${REMOTE_REFERENCE}" \
  "HEAD:refs/heads/${BRANCH}" 2>&1)"; then
  fail \
    "A non-destructive push preflight was rejected; no push was attempted." \
    "Review the Git output below, then reconcile without force-pushing:\n${push_preview}\n\nUseful checks:\n  git status --short --branch\n  git remote -v\n  git fetch ${REMOTE_REFERENCE} ${BRANCH}\nRerun after the local and remote histories are safely reconciled."
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  if [[ -n "${REMOTE_SHA}" ]]; then
    plan "would fast-forward ${TARGET}:${BRANCH} from ${REMOTE_SHA} to ${LOCAL_SHA}"
  else
    plan "would push ${LOCAL_SHA} as new branch ${TARGET}:${BRANCH}"
  fi
  note "Dry run complete; no local or remote state was changed."
  exit 0
fi

if [[ "${SET_UPSTREAM}" -eq 1 ]]; then
  if push_output="$(git_network \
    -c push.followTags=false \
    push \
    --set-upstream \
    --no-follow-tags \
    --recurse-submodules=no \
    "${REMOTE_NAME}" \
    "HEAD:refs/heads/${BRANCH}" 2>&1)"; then
    push_status=0
  else
    push_status=$?
  fi
else
  if push_output="$(git_network \
    -c push.followTags=false \
    push \
    --no-follow-tags \
    --recurse-submodules=no \
    "${REMOTE_NAME}" \
    "HEAD:refs/heads/${BRANCH}" 2>&1)"; then
    push_status=0
  else
    push_status=$?
  fi
fi
if [[ "${push_status}" -ne 0 ]]; then
  fail \
    "Push failed after preflight. The bootstrap did not recreate the GitHub repository, remote, or local commit." \
    "Review the Git output below:\n${push_output}\n\nA configured pre-push hook may have run, so inspect git status before continuing. Resolve the hook, authentication, network, or branch-policy failure, then rerun scripts/bootstrap-github.sh. It will reuse ${TARGET}, remote ${REMOTE_NAME}, and local commit ${LOCAL_SHA}; it will not recreate them."
fi

note "Pushed ${LOCAL_SHA} to ${TARGET}:${BRANCH}."
note "Bootstrap complete. Apply and verify docs/repository-settings.md separately."
