#!/usr/bin/env bash
# Pod의 파일을 로컬로 가져온다. 사용법(Git Bash, 저장소 루트에서):
#   tools/pod_get.sh A /workspace/<과정폴더>/check_gpu.py <로컬 폴더>
# 폴더도 통째로 가져온다(scp -r). 접속값·호스트 키 위치는 pod.sh와 같다(루트의 .env.local, 저장소 .ssh/).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.env.local"
which="${1:?usage: pod_get.sh A|B remote_path local_dir}"; remote="${2:?remote_path}"; dest="${3:?local_dir}"
host_var="POD_${which}_HOST"; port_var="POD_${which}_PORT"
if [ -z "${!host_var:-}" ] || [ -z "${!port_var:-}" ] || [ -z "${POD_USER:-}" ]; then
  echo "pod_get.sh: .env.local에 ${host_var}·${port_var}·POD_USER 값이 없다 — .env.local.example의 POD_${which}_* 줄 주석을 풀고 RunPod Connect 패널(SSH over exposed TCP) 값으로 채운다" >&2
  exit 2
fi
case "${!host_var}${!port_var}" in
  *CHANGE_ME*) echo "pod_get.sh: .env.local의 ${host_var}·${port_var}가 아직 CHANGE_ME 자리 표시다 — 실제 값으로 채운다" >&2; exit 2 ;;
esac
mkdir -p "$ROOT/.ssh" "$dest"
scp -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o "UserKnownHostsFile=\"$ROOT/.ssh/known_hosts\"" \
    -o LogLevel=ERROR -i "$HOME/.ssh/id_ed25519" -P "${!port_var}" -r "${POD_USER}@${!host_var}:$remote" "$dest"
