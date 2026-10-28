#!/usr/bin/env bash
# Pod에 SSH로 명령을 보낸다. 사용법(Git Bash, 저장소 루트에서):
#   tools/pod.sh A 'nvidia-smi'        # Pod A에서 명령 실행
#   tools/pod.sh B < script.sh         # 표준입력 스크립트를 Pod B의 bash로 실행
# 저장소 루트 = 이 파일이 들어 있는 tools/ 폴더의 부모. 접속값은 루트의 .env.local에서 읽는다
#   (POD_<글자>_HOST, POD_<글자>_PORT, POD_USER — 글자는 A, B, C …). SSH 키는 ~/.ssh/id_ed25519.
#   Pod B를 쓰려면 .env.local의 POD_B_* 줄 주석을 먼저 풀고 채운다(.env.local.example은 B를 주석으로 둔다).
# 호스트 키는 사용자 ~/.ssh 대신 저장소의 .ssh/known_hosts(git 제외)에 보관한다.
# (Git Bash의 ssh가 한글 사용자 경로의 ~/.ssh를 열지 못하는 문제를 피하기 위함)
# UserKnownHostsFile 값의 안쪽 따옴표는 저장소 경로에 공백이 있어도 깨지지 않게 하려는 것이다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.env.local"
which="${1:?usage: pod.sh A|B [command]}"; shift
host_var="POD_${which}_HOST"; port_var="POD_${which}_PORT"
if [ -z "${!host_var:-}" ] || [ -z "${!port_var:-}" ] || [ -z "${POD_USER:-}" ]; then
  echo "pod.sh: .env.local에 ${host_var}·${port_var}·POD_USER 값이 없다 — .env.local.example의 POD_${which}_* 줄 주석을 풀고 RunPod Connect 패널(SSH over exposed TCP) 값으로 채운다" >&2
  exit 2
fi
case "${!host_var}${!port_var}" in
  *CHANGE_ME*) echo "pod.sh: .env.local의 ${host_var}·${port_var}가 아직 CHANGE_ME 자리 표시다 — 실제 값으로 채운다" >&2; exit 2 ;;
esac
mkdir -p "$ROOT/.ssh"
opts=(-o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30
      -o StrictHostKeyChecking=accept-new -o "UserKnownHostsFile=\"$ROOT/.ssh/known_hosts\""
      -o LogLevel=ERROR -i "$HOME/.ssh/id_ed25519")
if [ $# -eq 0 ]; then
  exec ssh "${opts[@]}" -p "${!port_var}" "${POD_USER}@${!host_var}" 'bash -s'
else
  exec ssh "${opts[@]}" -p "${!port_var}" "${POD_USER}@${!host_var}" "$@"
fi
