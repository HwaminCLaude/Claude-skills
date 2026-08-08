# curriculum-notion

강의자료(노트북·PDF)를 **기초지식 0인 사람이 from scratch로 따라가며 완전히 이해하는 학습 커리큘럼**으로
재구성해 Notion 중첩 DB로 발행하고, 유닛마다 **자동 채점되는 Colab 노트북**을 만드는 스킬.

> 강의를 다 들었는데도 "돌아가긴 하는데 왜 그런지 모르겠는" 상태를 없애는 것이 목적입니다.

## 왜 필요한가

강사 자료는 기초를 안다고 가정하고 만들어집니다. 6주차에 갑자기 PyTorch가 나오는데
그 전에 텐서·미분 얘기가 없는 식이죠. 이 스킬은 그 **공백을 메운 학습 경로**를 새로 만듭니다.

그리고 이론을 아는 것과 코드로 구현해 맞는지 아는 것은 다른 문제라서,
유닛마다 **직접 구현 → 라이브러리 정답과 대조**하는 자동 채점기를 넣습니다.

```python
# 3장 — 직접 채우기
def sigmoid(z):
    # TODO: z를 0과 1 사이 확률로 바꿔 보세요.

# 4장 — 자동 채점
assert np.allclose(w, clf.coef_.ravel(), atol=2e-2)
print("✅ 직접 구현한 계수와 손실이 sklearn 결과와 맞아요.")
```

## 결과물

```
<커리큘럼 DB>
├ 00 · 학습 지도
├ 01주차 · <주제>
│    └ 📂 유닛 (인라인 하위 DB)   ← 이름·순서·유형·난이도·상태·콜랩·예상시간
│         ├ 01 · <개념>
│         └ …
└ …
```

**유닛 페이지 9층** — 🎯목표 · 🧭선수지식 · 📖개념(그림) · 🧮수식(숫자 대입) ·
💻직접 만들기 · 🔬맞는지 확인 · 🧪강의자료 적용 · ✅스스로 확인 · 🔗더 보기

**콜랩 노트북 7장** — 준비물 · 눈으로 보기 · **TODO 직접 만들기** · **자동 채점** ·
강의자료 적용 · 망가뜨리기 · 정답(접힘)

## 빠른 시작

```bash
export NOTION_TOKEN=ntn_...            # 또는 .env
export CURRICULUM_MATERIALS=/path/to/강의자료   # 주차 폴더들이 있는 곳
export RCLONE_BIN=rclone

# 1) 커리큘럼 설계 (scripts/curriculum.py 의 WEEKS·U 를 내 강의에 맞게 수정)
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/curriculum.py --dump

# 2) 뼈대 발행
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/publish_skeleton.py
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/verify_skeleton.py

# 3) 유닛 저작 (Codex 사용 시)
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/make_week_prompt.py --all
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/run_weeks.py --rest -j 4

# 4) 검증 + 발행
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/publish_all.py --check-only
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python scripts/publish_all.py
```

## 스크립트

| 파일 | 역할 |
|---|---|
| `curriculum.py` | 커리큘럼 정의 → `curriculum.json` (모든 단계의 단일 진실 공급원) |
| `publish_skeleton.py` | 주차 페이지 + 인라인 유닛 DB + 유닛 행 생성 (멱등) |
| `verify_skeleton.py` | 유닛 수 대조 — **누락·중복 양쪽** 검사 |
| `make_week_prompt.py` | 주차별 저작 프롬프트 생성 (실제 강의자료 파일 목록 주입) |
| `run_weeks.py` | Codex 병렬 저작 실행 |
| `preflight_unit.py` | 규약 검사 — 섹션 순서·수식·언어·이미지·**정답 누출** |
| `build_unit_notebook.py` | 유닛 spec → 7장 Colab 노트북 (정답은 맨 끝에 접어서) |
| `verify_unit_nb.py` | **검산 셀을 실제 실행** (경고도 에러로) |
| `publish_all.py` | 검증→발행→노트북 업로드→콜랩 링크 (멱등) |
| `unitkit.py` | 그림 저장 · Notion File Upload · 청크 발행 · 블록 수 검증 |
| `blocks.py` / `notion_api.py` | 블록 빌더 · Notion REST (vendor) |

## 검증이 실제로 잡아낸 것

이 스킬의 검사기들은 전부 **실제로 문제가 터져서** 추가된 것입니다.

- **정답 누출** — 1장 준비물에 `sigmoid_ref`라는 이름으로 정답이 들어가 TODO보다 6칸 위에 답이 있었음.
  이름을 바꿔도 잡도록 **정답 본문 줄을 비교**합니다.
- **곧 사라질 API** — `LogisticRegression(penalty=None)`은 sklearn 1.10에서 제거 예정.
  preflight는 통과했지만(글자만 검사) 검산 실행기가 잡았습니다 → `C=np.inf`.
- **블록 수 초과** — 발행 재시도로 같은 블록이 두 번 올라간 전례. 부족·초과 양쪽을 셉니다.

## 함정

- code 블록 `language="text"` → 400. **`"plain text"`**
- 인라인 파서가 `_..._`를 이탤릭으로 오인 → **밑줄 든 식별자는 백틱 필수**
- Google **Workspace** 계정은 Drive `lh3` 임베드가 302로 막힘 → **Notion File Upload API** 필수
  (`file_upload` id는 **1회용**)
- 발행은 **순차 1회**. 병렬·재시도하면 블록이 중복됩니다
- Windows에서 `codex`는 npm 셔임 → `shutil.which("codex")`로 실제 경로를 찾아야 합니다

## 관련 스킬

- `code-guidebook-notion` — 노트북 코드 한 줄 풀이 (이미 있는 코드 설명)
- `pdf-to-notion` — PDF 스캔 이미지 + 해설 2단 레이아웃
- `book-outline-notion` — 목차 계층 그대로 중첩 DB
