#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-ollama/qwen3-coder:30b}"
BASE_BRANCH="${BASE_BRANCH:-main}"
LABEL="${LABEL:-agent-run}"
WORKROOT="${WORKROOT:-/Users/vsinghthiara/Documents/Learning/agentic-pr}"

mkdir -p "$WORKROOT/logs"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: run this script from inside a git repo."
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: working tree is not clean. Commit or stash changes first."
  git status --short
  exit 1
fi

OWNER_REPO="$(gh repo view --json nameWithOwner --jq '.nameWithOwner')"

echo "Repo: $OWNER_REPO"
echo "Base branch: $BASE_BRANCH"
echo "Looking for open issue with label: $LABEL"

git checkout "$BASE_BRANCH"
git pull --ff-only origin "$BASE_BRANCH"

ISSUE_JSON="$(
  gh issue list \
    --repo "$OWNER_REPO" \
    --label "$LABEL" \
    --state open \
    --limit 1 \
    --json number,title,body \
    --jq '.[0] // empty'
)"

if [ -z "$ISSUE_JSON" ]; then
  echo "No open issues found with label: $LABEL"
  exit 0
fi

ISSUE_NUMBER="$(jq -r '.number' <<< "$ISSUE_JSON")"
ISSUE_TITLE="$(jq -r '.title' <<< "$ISSUE_JSON")"
ISSUE_BODY="$(jq -r '.body // ""' <<< "$ISSUE_JSON")"

BRANCH="agent/issue-${ISSUE_NUMBER}-$(date +%Y%m%d%H%M%S)"
PROMPT_FILE="$(mktemp)"
LOG_FILE="$WORKROOT/logs/${OWNER_REPO//\//_}-issue-${ISSUE_NUMBER}.log"

cat > "$PROMPT_FILE" <<EOF
You are a local coding agent working in this git repository.

GitHub issue: #$ISSUE_NUMBER
Title: $ISSUE_TITLE

User task:
$ISSUE_BODY

Rules:
- Make the smallest safe code change that satisfies the issue.
- Do not modify secrets, .env files, credentials, or unrelated generated files.
- Keep the solution simple and readable.
- Add or update tests only if appropriate for this repo.
- Do not merge anything. Only make code changes for a PR.
EOF

echo "Creating branch: $BRANCH"
git checkout -b "$BRANCH"

echo "Running Aider with model: $MODEL"
set +e
aider \
  --model "$MODEL" \
  --no-auto-commits \
  --no-dirty-commits \
  --yes-always \
  --message-file "$PROMPT_FILE" \
  2>&1 | tee "$LOG_FILE"

AIDER_EXIT="${PIPESTATUS[0]}"
set -e

if git diff --quiet && git diff --cached --quiet; then
  gh issue comment "$ISSUE_NUMBER" \
    --repo "$OWNER_REPO" \
    --body "Local Mac Studio agent ran, but produced no file changes. Log path on Mac Studio: $LOG_FILE"

  echo "Aider produced no changes."
  exit 0
fi

echo "Changes produced:"
git status --short

git add -A
git commit -m "agent: work on issue #$ISSUE_NUMBER"
git push -u origin "$BRANCH"

PR_BODY="$(cat <<EOF
This PR was created by the local Mac Studio agent.

Issue:
- Closes #$ISSUE_NUMBER

Model:
- $MODEL

Notes:
- Review carefully before merging.
- Local log path on Mac Studio: $LOG_FILE
- Aider exit code: $AIDER_EXIT
EOF
)"

PR_URL="$(
  gh pr create \
    --repo "$OWNER_REPO" \
    --base "$BASE_BRANCH" \
    --head "$BRANCH" \
    --title "Agent: $ISSUE_TITLE" \
    --body "$PR_BODY"
)"

gh issue edit "$ISSUE_NUMBER" \
  --repo "$OWNER_REPO" \
  --remove-label "$LABEL" \
  --add-label agent-pr-created || true

echo "Created PR:"
echo "$PR_URL"
