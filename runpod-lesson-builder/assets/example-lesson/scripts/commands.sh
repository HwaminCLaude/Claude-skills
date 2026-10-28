#!/usr/bin/env bash
# C02-L02 에서 JupyterLab Terminal에 입력한 명령 모음 (참고용).
# 이 파일을 통째로 실행하지 말고, README의 STEP 순서대로 한 줄씩 입력하며 결과를 확인하세요.
# 실행 위치: JupyterLab Terminal (Pod 안 bash)

pwd                                   # STEP 8: 지금 위치 확인
cd /workspace/llm-course              # STEP 8: 작업 폴더로 이동(성공하면 출력 없음)
nvidia-smi                            # STEP 9: GPU 상태 전체 보기
clear                                 # STEP 10: 화면 지우기
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv   # STEP 10: GPU 요약
python --version                      # STEP 11: 파이썬 버전
which python                          # STEP 11: 파이썬 위치
clear                                 # STEP 15: 화면 지우기
python check_gpu.py                   # STEP 15: 파이썬 파일 실행
nvidia-smi                            # STEP 24-1: 노트북 커널이 살아 있을 때(VRAM 사용 중)
clear                                 # STEP 24-3: 화면 지우기
nvidia-smi                            # STEP 24-3: 커널을 끈 뒤 VRAM 반환 확인
ls -la                                # STEP 25: 만든 파일 확인
# STEP 26(Pod 끄기)은 터미널이 아니라 RunPod 콘솔에서 합니다: Pods → 내 Pod → Stop
