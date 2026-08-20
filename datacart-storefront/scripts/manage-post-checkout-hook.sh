#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
COMMON_DIR="$(git -C "$REPO_ROOT" rev-parse --path-format=absolute --git-common-dir)"
USER_HOOK_DIR="$HOME/.databricks/user-githooks"
USER_HOOK="$USER_HOOK_DIR/post-checkout"
MARKER="# datacart-storefront-common-dir: $COMMON_DIR"
LEGACY_MARKER="# datacart-storefront-root: $REPO_ROOT"

usage() {
    echo "Usage: $0 install|uninstall" >&2
    exit 2
}

render_hook() {
    local quoted_common_dir
    printf -v quoted_common_dir '%q' "$COMMON_DIR"
    cat <<EOF
#!/usr/bin/env bash
$MARKER

EXPECTED_COMMON_DIR=$quoted_common_dir
CURRENT_ROOT="\$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
CURRENT_COMMON_DIR="\$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || exit 0
[[ "\$CURRENT_COMMON_DIR" == "\$EXPECTED_COMMON_DIR" ]] || exit 0

REPO_HOOK="\$CURRENT_ROOT/.githooks/post-checkout"
if [[ ! -x "\$REPO_HOOK" ]]; then
    echo "post-checkout: expected executable hook at \$REPO_HOOK" >&2
    exit 0
fi

"\$REPO_HOOK" "\$@" || true
EOF
}

install_hook() {
    local existing_marker tmp_file
    mkdir -p "$USER_HOOK_DIR"

    if [[ -e "$USER_HOOK" ]]; then
        existing_marker="$(awk 'NR == 2 { print; exit }' "$USER_HOOK")"
        if [[ "$existing_marker" != "$MARKER" && "$existing_marker" != "$LEGACY_MARKER" ]]; then
            echo "Refusing to overwrite existing user hook: $USER_HOOK" >&2
            echo "Chain $REPO_ROOT/.githooks/post-checkout from that hook manually." >&2
            exit 1
        fi
    fi

    umask 077
    tmp_file="$(mktemp "${USER_HOOK}.tmp.XXXXXX")"
    trap 'rm -f "$tmp_file"' EXIT
    render_hook >"$tmp_file"
    chmod 700 "$tmp_file"
    mv "$tmp_file" "$USER_HOOK"
    trap - EXIT
    echo "Installed repo-scoped user hook at $USER_HOOK"
}

uninstall_hook() {
    local existing_marker
    if [[ ! -e "$USER_HOOK" ]]; then
        echo "No user hook is installed at $USER_HOOK"
        return
    fi

    existing_marker="$(awk 'NR == 2 { print; exit }' "$USER_HOOK")"
    if [[ "$existing_marker" != "$MARKER" && "$existing_marker" != "$LEGACY_MARKER" ]]; then
        echo "Refusing to remove a user hook not owned by this clone: $USER_HOOK" >&2
        exit 1
    fi

    rm "$USER_HOOK"
    rmdir "$USER_HOOK_DIR" 2>/dev/null || true
    echo "Removed this clone's user hook registration."
}

case "${1:-}" in
    install) install_hook ;;
    uninstall) uninstall_hook ;;
    *) usage ;;
esac
