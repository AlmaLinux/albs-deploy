#!/usr/bin/env bash
#
# Ensure a usable Bitwarden session and print the session key on stdout.
# Managed by Ansible (bitwarden_cli role). Reusable by any service that needs
# a shared BW_SESSION (e.g. multi-worker servers where each worker must reuse
# one session instead of racing `bw login`/`bw unlock`).
#
# Usage: bw-ensure-session <username> <password_file>
#
# Assumes `bw config server` has already been run for the invoking user
# (the bitwarden_cli role does this).
set -euo pipefail

username="${1:?username required}"
pass_file="${2:?password file path required}"

# `bw login --check` exits 0 when logged in, 1 otherwise.
if ! bw login --check >/dev/null 2>&1; then
    bw login "${username}" --raw --passwordfile "${pass_file}" >/dev/null
fi

# Print the session key so the caller can `export BW_SESSION="$(...)"`.
bw unlock --raw --passwordfile "${pass_file}"
