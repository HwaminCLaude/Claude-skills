"""JupyterLab 실화면 조작·캡처 도우미 (SSH 터널 + Playwright 헤드리스 Chromium).

여러 에이전트가 동시에 쓸 수 있도록 에이전트마다 다른 로컬 포트와 JupyterLab workspace 이름을 쓴다.
접속 토큰은 Pod에서 SSH로 읽어 메모리에만 두고 화면·파일·로그에 남기지 않는다. 연결·조작 중에 오류가 나도
오류 문구 속 토큰은 <TOKEN>으로 바꿔 다시 던진다(대화·워크플로 기록·REPORT로 새지 않게).
저장소 루트 = 이 파일이 들어 있는 tools/ 폴더의 부모. 접속값은 루트의 .env.local(POD_<글자>_HOST·PORT, POD_USER),
호스트 키는 저장소 .ssh/known_hosts, SSH 키는 ~/.ssh/id_ed25519 (pod.sh와 같다).

사용 예 (Pod의 venv가 아니라 이 PC의 python으로 실행. playwright + chromium 필요):
    import sys; sys.path.insert(0, r"<저장소>\\tools")
    from jlab import JLab
    with JLab("A", port=18801, workspace="c03l03") as j:
        j.open("workspace/llm-course/ch03/l03_tokenizer.ipynb")        # 파일 열기
        j.shot(r"...\\_raw\\s05-notebook.png")                        # 화면 저장(1600x900)
        j.run_all()                                                   # Restart Kernel and Run All Cells…
        j.scroll_to_text("출력에 나오는 글자")                         # 원하는 셀까지 스크롤
        j.terminal(["cd /workspace/llm-course/ch03", "nvidia-smi"], wait=3)
        j.shot(r"...\\_raw\\s06-terminal.png")
        j.new_file_paste(code, "l03_check", folder="workspace/llm-course/ch03",      # 학습자처럼 새 Python File에
                         shots={"pasted": r"...\\_raw\\s07a-code-pasted.png",        # 붙여 넣고 첫 Ctrl+S → 이름 창 →
                                "rename": r"...\\_raw\\s07b-rename-dialog.png",      # Rename and Save
                                "saved": r"...\\_raw\\s07c-saved.png"})
        j.shutdown_terminals()                                        # 이 JLab이 연 Terminal만 닫는다
        j.shutdown_kernels()                                          # 이 JLab이 연 노트북의 커널만 정리(VRAM 반환)

같은 Pod의 JupyterLab 서버는 다른 레인도 쓴다. 서버(사용자) 설정을 바꾸는 체크박스(Do not ask me again.,
Do not ask for rename on first save.)와 Settings 메뉴는 건드리지 않는다. _dismiss_news()가 누르는 Jupyter news 알림의
No도 서버 설정으로 남으므로, 그 알림을 보여 줘야 하는 레슨은 jlab을 쓰기 전에 메인 세션이 찍는다.
화면 크기는 1600x900(16:9)으로 고정한다. 영상 카드에도 그대로 쓸 수 있다.
"""
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # Windows 콘솔(cp949)에서도 한글·기호 출력
    except ValueError:
        pass

ROOT = Path(__file__).resolve().parents[1]
VIEWPORT = {"width": 1600, "height": 900}


def _env():
    """.env.local 읽기. bash의 source와 같게 값 바깥 따옴표와 줄 앞 'export '는 무시한다."""
    env = {}
    for line in (ROOT / ".env.local").read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k.startswith("export "):
                k = k[len("export "):].strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            env[k] = v
    return env


def _ssh_base(pod):
    e = _env()
    kh = (ROOT / ".ssh" / "known_hosts").as_posix()
    key = str(Path.home() / ".ssh" / "id_ed25519")
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=30",
            "-o", "StrictHostKeyChecking=accept-new", "-o", f'UserKnownHostsFile="{kh}"',
            "-o", "LogLevel=ERROR", "-i", key, "-p", e[f"POD_{pod}_PORT"], f"{e['POD_USER']}@{e[f'POD_{pod}_HOST']}"]


def _free(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def _scrub(text, token):
    """오류 문구에서 토큰을 지운다(토큰 값 자체와 'token=…' 꼴 모두)."""
    text = str(text)
    if token:
        text = text.replace(token, "<TOKEN>")
    return re.sub(r"token=[^&\s\"'<>]+", "token=<TOKEN>", text)


def _leaks(exc, token):
    s = str(exc)
    return bool(token and token in s) or "token=" in s


class JLab:
    def __init__(self, pod, port, workspace="default", headless=True):
        self.pod, self.port, self.ws = pod, port, re.sub(r"[^A-Za-z0-9_-]", "-", workspace)
        self.headless = headless
        self.base = f"http://localhost:{port}"
        self.tunnel = self.pw = self.browser = None
        self._token = None
        self._opened = set()            # open()으로 연 경로 — shutdown_kernels()의 기본 범위
        self._terms = []                # terminal()로 연 Terminal 이름 — shutdown_terminals()의 범위

    # ---------- 연결 ----------
    def __enter__(self):
        if not _free(self.port):
            raise RuntimeError(f"local port {self.port} is busy — choose another port")
        self.tunnel = subprocess.Popen(_ssh_base(self.pod)[:-1] + ["-N", "-L", f"{self.port}:localhost:8888",
                                                                   _ssh_base(self.pod)[-1]],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(40):
                if not _free(self.port) or self.tunnel.poll() is not None:
                    break
                time.sleep(0.25)
            if _free(self.port):
                raise RuntimeError(f"SSH tunnel to Pod {self.pod} did not open local port {self.port} "
                                   f"(check .env.local and: tools/pod.sh {self.pod} 'echo ok')")
            token = subprocess.run(_ssh_base(self.pod) + ['source /etc/rp_environment >/dev/null 2>&1; printf %s "$JUPYTER_PASSWORD"'],
                                   capture_output=True, text=True, timeout=30).stdout.strip()
            if not token:
                raise RuntimeError("could not read the Jupyter token from the pod")
            self._token = token
            self.pw = sync_playwright().start()
            self.browser = self.pw.chromium.launch(headless=self.headless)
            self.ctx = self.browser.new_context(viewport=VIEWPORT, device_scale_factor=1, locale="en-US")
            self.page = self.ctx.new_page()
            self.page.goto(f"{self.base}/lab/workspaces/{self.ws}?token={token}", wait_until="domcontentloaded")
            self._ready()
            self._dismiss_news()
        except BaseException as e:
            self._close()               # 실패해도 SSH 터널·브라우저를 남기지 않는다(남으면 다음 실행이 'port is busy')
            if _leaks(e, self._token):  # 탐색 URL(…?token=…)이 든 오류 문구를 그대로 던지지 않는다
                raise RuntimeError(f"{type(e).__name__}: {_scrub(e, self._token)}") from None
            raise
        return self

    def __exit__(self, exc_type, exc, tb):
        self._close()
        if exc is not None and _leaks(exc, self._token):
            raise RuntimeError(f"{type(exc).__name__}: {_scrub(exc, self._token)}") from None
        return False

    def _close(self):
        try:
            if self.browser:
                self.browser.close()
            if self.pw:
                self.pw.stop()
        finally:
            if self.tunnel:
                self.tunnel.terminate()

    def _ready(self, timeout=60000):
        self.page.wait_for_selector("#jp-main-dock-panel", timeout=timeout)
        self.page.wait_for_timeout(1500)

    def _dismiss_news(self):
        """첫 화면의 Jupyter news 알림에서 No를 누른다(이 선택은 서버의 사용자 설정에 남는다)."""
        btn = self.page.get_by_role("button", name="No", exact=True)
        try:
            if btn.count():
                btn.first.click(timeout=2000)
        except Exception:
            pass

    def _api(self, method, path):
        """서버 REST API 호출(토큰은 헤더로만 전달)."""
        h = {"Authorization": f"token {self._token}"}
        return getattr(self.ctx.request, method)(f"{self.base}{path}", headers=h)

    # ---------- 화면 ----------
    def open(self, path, wait=2500):
        """JupyterLab 루트(/) 기준 경로(예: workspace/llm-course/ch03/x.ipynb, 폴더도 됨)를 연다."""
        self._opened.add(path.strip("/"))
        self.page.goto(f"{self.base}/lab/workspaces/{self.ws}/tree/{path}", wait_until="domcontentloaded")
        self._ready()
        self._dismiss_news()
        self.page.wait_for_timeout(wait)

    def shot(self, out_path, clip=None):
        """현재 화면을 PNG로 저장(1600x900). clip=(x, y, w, h)로 일부만."""
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        kw = {"path": str(out_path)}
        if clip:
            kw["clip"] = {"x": clip[0], "y": clip[1], "width": clip[2], "height": clip[3]}
        self.page.screenshot(**kw)
        return out_path

    def scroll_to_text(self, text, timeout=10000):
        loc = self.page.get_by_text(text).first
        loc.scroll_into_view_if_needed(timeout=timeout)
        self.page.wait_for_timeout(500)

    def _new_launcher(self):
        """새 Launcher 탭(File Browser가 보고 있는 폴더). 편집기에 포커스가 있으면 편집기가 Ctrl+Shift+L을 가져가므로
        Launcher가 새로 생기지 않았을 때는 File 메뉴의 New Launcher를 누른다."""
        n = self.page.locator(".jp-Launcher").count()
        self.page.keyboard.press("Control+Shift+L")
        self.page.wait_for_timeout(1500)
        if self.page.locator(".jp-Launcher").count() <= n:
            self.page.get_by_role("menuitem", name="File", exact=True).click()
            self.page.get_by_text("New Launcher", exact=True).first.click()
            self.page.wait_for_timeout(1500)

    # ---------- 새 파일(학습자 동작 그대로) ----------
    def new_file_paste(self, code, name, folder=None, shots=None, card="Python File"):
        """Launcher의 card(기본 Python File)로 새 파일 → 코드 붙여 넣기 → 첫 Ctrl+S → Rename file 창에 name → Rename and Save.

        학습자 STEP(붙여 넣은 모습 → 이름 창 → 저장 완료)을 그대로 찍기 위한 것이다. 코드는 한 번에 넣으므로(insert_text)
        편집기 자동 들여쓰기로 깨지지 않는다(학습자의 Ctrl+V와 같은 결과).
        folder: JupyterLab 루트 기준 폴더(예: workspace/llm-course/ch03) — 그 폴더를 연 뒤 새 Launcher에서 만든다.
        name: 확장자 없는 이름(예: l03_check). 같은 이름의 파일이 이미 있으면 멈춘다(촬영 전에 폴더를 학습자 시작 상태로).
        shots: {"pasted": 경로, "rename": 경로, "filled": 경로, "saved": 경로} 중 필요한 것 — 그 순간의 화면을 저장한다.
        반환: 저장된 파일 이름(이름 창에 들어간 값).
        """
        shots = shots or {}
        ext = {"Python File": ".py", "Text File": ".txt", "Markdown File": ".md"}.get(card)
        if folder and ext:                                     # 이름이 겹치면 JupyterLab은 조용히 untitled로 남긴다
            target = f"{folder.strip('/')}/{name}{ext}"
            if self._api("get", f"/api/contents/{quote(target)}?content=0").ok:
                raise RuntimeError(f"{target} 가 이미 있다 — 촬영 전에 폴더를 학습자 시작 상태로 맞춘다")
        if folder:
            self.open(folder.strip("/"), wait=1000)
        self._new_launcher()
        self.page.locator(".jp-LauncherCard:visible", has_text=card).first.click()   # 숨은 탭의 Launcher는 건너뛴다
        editor = self.page.locator(".jp-FileEditor .cm-content:visible").last
        editor.wait_for(timeout=30000)
        editor.click()
        self.page.keyboard.insert_text(code)
        self.page.wait_for_timeout(800)
        if "pasted" in shots:
            self.shot(shots["pasted"])
        self.page.keyboard.press("Control+s")
        dlg = self.page.locator(".jp-Dialog")
        try:
            dlg.first.wait_for(timeout=8000)
        except Exception:
            raise RuntimeError("첫 저장 때 Rename file 창이 뜨지 않았다 — 서버 설정 'Do not ask for rename on first save'가 "
                               "켜졌을 수 있다(사람이 Settings에서 확인). 이 파일은 untitled 이름으로 저장됐을 수 있다") from None
        self.page.wait_for_timeout(500)
        if "rename" in shots:
            self.shot(shots["rename"])
        self.page.keyboard.type(name, delay=30)               # 확장자를 뺀 untitled 부분만 선택되어 있다
        saved = dlg.first.locator("input").first.input_value()
        if "filled" in shots:
            self.shot(shots["filled"])
        self.page.get_by_role("button", name="Rename and Save").click()
        tab = self.page.locator("#jp-main-dock-panel .lm-TabBar-tab.lm-mod-current .lm-TabBar-tabLabel").first
        for _ in range(12):                                    # 프록시 때문에 탭 이름이 1~2초 늦게 바뀔 수 있다
            self.page.wait_for_timeout(500)
            if not dlg.count() and tab.inner_text().strip() == saved:
                break
        else:
            now = dlg.first.inner_text()[:200].replace("\n", " ") if dlg.count() else f"탭 이름 {tab.inner_text().strip()!r}"
            raise RuntimeError(f"Rename and Save 뒤 이름이 {saved}로 바뀌지 않았다({now}) — 같은 이름의 파일이 이미 있는지 "
                               "확인한다(새 파일은 untitled 이름으로 남았을 수 있다)")
        if "saved" in shots:
            self.shot(shots["saved"])
        return saved

    # ---------- 노트북 ----------
    def run_all(self, timeout_s=900):
        """Kernel → Restart Kernel and Run All Cells… → Restart, 실행이 끝날 때까지 기다린다."""
        self.page.get_by_role("menuitem", name="Kernel").click()
        self.page.get_by_text("Restart Kernel and Run All Cells…").click()
        self.page.get_by_role("button", name="Restart").click()
        self.page.wait_for_timeout(3000)
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            busy = self.page.locator(".jp-InputPrompt:has-text('[*]')").count()
            idle = "Idle" in (self.page.locator(".jp-StatusBar-TextItem").all_inner_texts() and
                              " ".join(self.page.locator(".jp-StatusBar-TextItem").all_inner_texts()))
            if busy == 0 and idle:
                break
            time.sleep(2)
        self.page.keyboard.press("Control+s")
        self.page.wait_for_timeout(1500)

    def shutdown_kernels(self, prefix=None, everything=False):
        """노트북 커널을 끈다(REST API, 토큰은 헤더로만 전달). 끈 커널 수를 돌려준다.

        기본: 이 JLab이 open()으로 연 노트북의 커널만 끈다. 같은 Pod의 JupyterLab 서버를 다른 레인도 쓰므로
        남의 커널은 건드리지 않는다.
        prefix="workspace/llm-course/ch03/": 그 폴더 아래 노트북의 커널도 함께 끈다(Launcher로 새로 만든 노트북 등).
        everything=True: 서버의 모든 커널을 끈다 — 그 Pod를 혼자 쓸 때만.
        """
        if everything:
            ids = [k["id"] for k in self._api("get", "/api/kernels").json()]
        else:
            pre = prefix.strip("/") if prefix else None
            ids = []
            for s in self._api("get", "/api/sessions").json():
                p = (s.get("path") or "").strip("/")
                mine = p in self._opened or (pre is not None and (p == pre or p.startswith(pre + "/")))
                if s.get("kernel") and mine:
                    ids.append(s["kernel"]["id"])
        ids = list(dict.fromkeys(ids))
        for kid in ids:
            self._api("delete", f"/api/kernels/{kid}")
        return len(ids)

    # ---------- 터미널 ----------
    def _terminal_names(self):
        r = self._api("get", "/api/terminals")
        return {t["name"] for t in r.json()} if r.ok else set()

    def terminal(self, commands, wait=2.0, new=True):
        """새 Terminal을 열고 명령을 한 줄씩 입력한다(각 줄 뒤 wait초 대기). 연 Terminal은 shutdown_terminals()로 닫는다."""
        if new:
            before = self._terminal_names()
            self._new_launcher()
            self.page.locator(".jp-LauncherCard[title*='terminal' i]:visible, .jp-LauncherCard:visible:has-text('Terminal')").first.click()
            self.page.wait_for_selector(".jp-Terminal", timeout=30000)
            self.page.wait_for_timeout(2500)
            mine = self._terminal_names() - before
            if len(mine) == 1:
                self._terms.extend(mine)
            else:                                                # 다른 레인이 같은 순간에 Terminal을 열면 가려낼 수 없다
                print(f"note: 새 Terminal을 가려내지 못함(새로 생긴 것 {len(mine)}개) — 끝날 때 Running Terminals and "
                      "Kernels에서 내 Terminal을 확인해 닫는다")
        term = self.page.locator(".jp-Terminal:visible").last
        term.click()
        for c in commands:
            self.page.keyboard.type(c, delay=8)
            self.page.keyboard.press("Enter")
            self.page.wait_for_timeout(int(wait * 1000))

    def type_in_terminal(self, text, enter=True, wait=1.0):
        self.page.locator(".jp-Terminal:visible").last.click()
        self.page.keyboard.type(text, delay=8)
        if enter:
            self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(int(wait * 1000))

    def shutdown_terminals(self):
        """이 JLab이 terminal()로 연 Terminal만 닫는다(REST API, 토큰은 헤더로만). 닫은 수를 돌려준다."""
        n = 0
        for name in dict.fromkeys(self._terms):
            if self._api("delete", f"/api/terminals/{name}").ok:
                n += 1
        self._terms = []
        return n


def pod_run(pod, command, timeout=3600):
    """Pod에서 명령 실행(표준출력 반환). 비밀값 출력 금지 명령(env, printenv 등)은 쓰지 말 것."""
    r = subprocess.run(_ssh_base(pod) + [command], capture_output=True, text=True, timeout=timeout,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


if __name__ == "__main__":       # 간단 자가 점검: python tools/jlab.py A 18899 <출력.png>
    pod, port, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    with JLab(pod, port, workspace="selftest") as j:
        j.open("workspace")
        j.shot(out)
    print("saved", out)
