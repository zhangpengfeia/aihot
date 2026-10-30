#!/usr/bin/env bash
# Actions 通过标准输入执行此脚本；源码只来自固定 SHA 的 git archive。
set -Eeuo pipefail
umask 077
root=${1:?provide deployment root}
release=${2:?provide commit SHA}
checksum=${3:?provide archive SHA256}
[[ $root =~ ^/[a-zA-Z0-9_/-]+$ && $root != / && $root != *..* ]]
[[ $release =~ ^[a-f0-9]{40}$ && $checksum =~ ^[a-f0-9]{64}$ ]]
archive=$root/incoming/$release.tar.gz
trap 'rm -f -- "$archive"' EXIT
printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --status
directory=$root/releases/$release
mkdir -p "$directory"
tar -xzf "$archive" --no-same-owner -C "$directory"
bash "$directory/deploy/deploy.sh" "$root" "$release"
