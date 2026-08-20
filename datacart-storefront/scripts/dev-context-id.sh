#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

context_id_for() {
    local git_user="$1"
    local git_branch="$2"

    [[ -n "$git_branch" ]] || {
        echo "Detached HEAD or unusable Git branch name" >&2
        return 1
    }

    if [[ "$git_branch" =~ ^cursor/([0-9a-f]{8})$ ]]; then
        printf '%s\n' "${BASH_REMATCH[1]}"
        return
    fi

    [[ -n "$git_user" ]] || {
        echo "git user.name is required to identify this development context" >&2
        return 1
    }

    printf '%s\0%s' "$git_user" "$git_branch" |
        python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:8])'
}

run_self_test() {
    local ordinary collision_a collision_b

    [[ "$(context_id_for "Alex Feng" "cursor/cc84ff57")" == "cc84ff57" ]]

    ordinary="$(context_id_for "Alex Feng" "feat/Lakebase Branch")"
    [[ "$ordinary" =~ ^[0-9a-f]{8}$ ]]

    collision_a="$(context_id_for "Alex Feng" "feat/a_b")"
    collision_b="$(context_id_for "Alex Feng" "feat/a-b")"
    [[ "$collision_a" != "$collision_b" ]]

    if context_id_for "Alex Feng" "" >/dev/null 2>&1; then
        echo "Expected a detached checkout to be rejected" >&2
        return 1
    fi

    echo "Development context ID checks passed."
}

case "${1:-}" in
    "") context_id_for \
        "$(git -C "$REPO_ROOT" config user.name || true)" \
        "$(git -C "$REPO_ROOT" branch --show-current)" ;;
    --self-test) run_self_test ;;
    *)
        echo "Usage: $0 [--self-test]" >&2
        exit 2
        ;;
esac
