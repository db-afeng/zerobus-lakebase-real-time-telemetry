#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$APP_ROOT" rev-parse --show-toplevel)"
CONFIG_FILE="$APP_ROOT/lakebase.config"
ENV_FILE="$APP_ROOT/.env.lakebase"
REFRESH_ONLY=false
SELF_TEST=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --refresh-only) REFRESH_ONLY=true ;;
        --self-test) SELF_TEST=true ;;
        *)
            echo "Unknown option: $1" >&2
            exit 2
            ;;
    esac
    shift
done

sanitize_git_user() {
    printf '%s' "$1" |
        tr '[:upper:]' '[:lower:]' |
        sed 's/[^a-z0-9-]//g; s/--*/-/g; s/^-//; s/-$//'
}

sanitize_git_branch() {
    printf '%s' "$1" |
        tr '[:upper:]' '[:lower:]' |
        sed 's/[^a-z0-9-]/-/g; s/--*/-/g; s/^-//; s/-$//'
}

build_lakebase_branch_name() {
    local git_user git_branch raw digest prefix
    git_user="$(sanitize_git_user "$1")"
    git_branch="$(sanitize_git_branch "$2")"

    [[ -n "$git_user" ]] || {
        echo "git user.name does not contain a usable branch-name character" >&2
        return 1
    }
    [[ -n "$git_branch" ]] || {
        echo "Detached HEAD or unusable Git branch name" >&2
        return 1
    }

    raw="dev-${git_user}-${git_branch}"
    if [[ ${#raw} -le 63 ]]; then
        printf '%s\n' "$raw"
        return
    fi

    digest="$(
        printf '%s' "$raw" |
            python3 -c 'import hashlib, sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest()[:8])'
    )"
    prefix="${raw:0:54}"
    prefix="${prefix%-}"
    printf '%s-%s\n' "$prefix" "$digest"
}

endpoint_is_connectable() {
    local state="$1"
    local host="$2"
    [[ -n "$host" && "$state" =~ ^(ACTIVE|IDLE|SUSPENDED)$ ]]
}

run_self_test() {
    local actual long_name

    actual="$(build_lakebase_branch_name "Alex Feng" "feat/Lakebase Branch")"
    [[ "$actual" == "dev-alexfeng-feat-lakebase-branch" ]] || {
        echo "Expected sanitized branch name, got: $actual" >&2
        return 1
    }

    long_name="$(build_lakebase_branch_name "Alex Feng" "feature/$(printf 'x%.0s' {1..80})")"
    [[ ${#long_name} -le 63 && "$long_name" =~ -[0-9a-f]{8}$ ]] || {
        echo "Expected a bounded, hashed branch name, got: $long_name" >&2
        return 1
    }

    if build_lakebase_branch_name "!!!" "main" >/dev/null 2>&1; then
        echo "Expected an unusable Git user to be rejected" >&2
        return 1
    fi

    endpoint_is_connectable "ACTIVE" "lakebase.example" || return 1
    endpoint_is_connectable "IDLE" "lakebase.example" || return 1
    endpoint_is_connectable "SUSPENDED" "lakebase.example" || return 1
    if endpoint_is_connectable "PROVISIONING" "lakebase.example"; then
        echo "Expected a provisioning endpoint to remain unavailable" >&2
        return 1
    fi

    echo "Lakebase branch-name checks passed."
}

if [[ "$SELF_TEST" == "true" ]]; then
    run_self_test
    exit
fi

[[ -f "$CONFIG_FILE" ]] || {
    echo "Missing $CONFIG_FILE" >&2
    exit 1
}
# shellcheck disable=SC1090
source "$CONFIG_FILE"

for tool in databricks jq python3; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "$tool is required for Lakebase development" >&2
        exit 1
    }
done

if ! databricks postgres --help >/dev/null 2>&1; then
    echo "Databricks CLI Lakebase commands are unavailable; upgrade the CLI." >&2
    exit 1
fi

databricks_cli() {
    if [[ -n "$LAKEBASE_PROFILE" && "$LAKEBASE_PROFILE" != "DEFAULT" ]]; then
        databricks "$@" --profile "$LAKEBASE_PROFILE"
    else
        databricks "$@"
    fi
}

GIT_USER_RAW="$(git -C "$REPO_ROOT" config user.name || true)"
GIT_BRANCH_RAW="$(git -C "$REPO_ROOT" branch --show-current)"
LAKEBASE_BRANCH="$(build_lakebase_branch_name "$GIT_USER_RAW" "$GIT_BRANCH_RAW")"

CURRENT_USER_JSON="$(databricks_cli current-user me -o json)"
CURRENT_USER_NAME="$(jq -er '.userName // .user_name' <<<"$CURRENT_USER_JSON")"
DB_USER="$LAKEBASE_PG_ROLE"
PROJECT_PATH="projects/${LAKEBASE_PROJECT_NAME}"
LAKEBASE_BRANCH_PATH="${PROJECT_PATH}/branches/${LAKEBASE_BRANCH}"
SOURCE_BRANCH="${PROJECT_PATH}/branches/${LAKEBASE_PARENT_BRANCH}"

if ! databricks_cli postgres get-project "$PROJECT_PATH" -o json >/dev/null 2>&1; then
    echo "Lakebase project $PROJECT_PATH was not found." >&2
    echo "Create the external project or override LAKEBASE_PROJECT_NAME in lakebase.config." >&2
    exit 1
fi

ensure_branch() {
    if databricks_cli postgres get-branch "$LAKEBASE_BRANCH_PATH" -o json >/dev/null 2>&1; then
        echo "Reusing Lakebase branch $LAKEBASE_BRANCH"
        return
    fi

    if [[ "$REFRESH_ONLY" == "true" ]]; then
        echo "Lakebase branch $LAKEBASE_BRANCH does not exist; run make dev-lakebase." >&2
        exit 1
    fi

    local request
    request="$(jq -nc \
        --arg source "$SOURCE_BRANCH" \
        --arg ttl "$LAKEBASE_BRANCH_TTL" \
        '{spec: {source_branch: $source, ttl: $ttl}}')"
    echo "Creating Lakebase branch $LAKEBASE_BRANCH from $LAKEBASE_PARENT_BRANCH"
    databricks_cli postgres create-branch "$PROJECT_PATH" "$LAKEBASE_BRANCH" \
        --json "$request" -o json >/dev/null
}

ensure_endpoint() {
    local attempt endpoints_json endpoints endpoint state host request create_output

    for attempt in {1..60}; do
        endpoints_json="$(
            databricks_cli postgres list-endpoints "$LAKEBASE_BRANCH_PATH" -o json 2>/dev/null ||
                printf '[]'
        )"
        endpoints="$(jq -c 'if type == "array" then . else (.endpoints // []) end' <<<"$endpoints_json")"
        endpoint="$(
            jq -c '
                [
                    .[]
                    | select(
                        (.spec.endpoint_type // .status.endpoint_type // "")
                        == "ENDPOINT_TYPE_READ_WRITE"
                    )
                ][0] // empty
            ' <<<"$endpoints"
        )"

        if [[ -n "$endpoint" ]]; then
            ENDPOINT_NAME="$(jq -er '.name' <<<"$endpoint")"
            state="$(jq -r '.status.current_state // "unknown"' <<<"$endpoint")"
            host="$(jq -r '.status.hosts.host // empty' <<<"$endpoint")"
            if endpoint_is_connectable "$state" "$host"; then
                ENDPOINT_HOST="$host"
                echo "Lakebase endpoint is $state at $ENDPOINT_HOST"
                return
            fi
            echo "Waiting for Lakebase endpoint (${state}, attempt ${attempt}/60)"
        else
            request="$(jq -nc '{
                spec: {
                    endpoint_type: "ENDPOINT_TYPE_READ_WRITE",
                    autoscaling_limit_min_cu: 0.5,
                    autoscaling_limit_max_cu: 2.0
                }
            }')"
            if create_output="$(
                databricks_cli postgres create-endpoint \
                    "$LAKEBASE_BRANCH_PATH" "$LAKEBASE_ENDPOINT_ID" \
                    --json "$request" -o json 2>&1
            )"; then
                echo "Creating Lakebase read-write endpoint"
            else
                echo "Waiting to create Lakebase endpoint (attempt ${attempt}/60): $create_output" >&2
            fi
        fi

        sleep 5
    done

    echo "Timed out waiting for a connectable Lakebase endpoint" >&2
    exit 1
}

write_env_file() {
    local credential_json token expires tmp_file
    credential_json="$(
        databricks_cli postgres generate-database-credential "$ENDPOINT_NAME" -o json
    )"
    token="$(jq -er '.token' <<<"$credential_json")"
    expires="$(jq -er '.expire_time' <<<"$credential_json")"

    umask 077
    tmp_file="$(mktemp "${ENV_FILE}.tmp.XXXXXX")"
    trap 'rm -f "$tmp_file"' EXIT
    {
        echo "# Generated by scripts/lakebase-branch.sh; do not commit."
        echo "# Branch: $LAKEBASE_BRANCH"
        echo "# OAuth token identity: $CURRENT_USER_NAME"
        echo "# Credential expires: $expires"
        printf 'PGHOST=%s\n' "$ENDPOINT_HOST"
        printf 'PGPORT=5432\n'
        printf 'PGUSER=%s\n' "$DB_USER"
        printf 'PGPASSWORD=%s\n' "$token"
        printf 'PGDATABASE=%s\n' "$LAKEBASE_DATABASE"
        printf 'PGSSLMODE=require\n'
        printf 'ENDPOINT_NAME=%s\n' "$ENDPOINT_NAME"
        printf 'LAKEBASE_PG_ROLE=%s\n' "$LAKEBASE_PG_ROLE"
        printf 'LAKEBASE_BRANCH_PATH=%s\n' "$LAKEBASE_BRANCH_PATH"
        printf 'DB_SOURCE=lakebase/%s\n' "$LAKEBASE_BRANCH"
    } >"$tmp_file"
    chmod 600 "$tmp_file"
    mv "$tmp_file" "$ENV_FILE"
    trap - EXIT

    echo "Wrote $ENV_FILE (credential expires $expires)"
}

ensure_branch
ensure_endpoint
write_env_file
