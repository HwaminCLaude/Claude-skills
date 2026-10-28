from vizkit import *
from random import seed

seed(41)
np.random.seed(41)


class Hook(CueScene):
    """에피소드 첫 씬 예시. 큐마다 `with self.cue("<id>"):` 블록을 하나씩 쓴다.

    - 큐 id와 길이는 shots.json → cues.py → timing.json에서 온다. 아래 c001, c002는
      예시 id다. shots.json의 큐 id로 바꾼다(없으면 CueNotFound로 렌더가 멈춘다).
    - 블록 안에는 박자(self.play)를 1개 이상 넣고, run_time은 0.5~1.0초로 둔다.
      play가 0번인 큐는 render.py가 WARN CUE_NO_BEAT로 알린다.
    - 남는 시간은 CueScene이 기다려 채운다. 큐보다 길면 CUE_OVERRUN이 찍힌다.
    - 글자는 label/title/source(크기 토큰 S, M, T, L, XL), 수식은 tex(size=...)로만 만든다.
      키트가 1080p 잉크 높이에 맞춰 크기를 보정하므로 .scale()로 키우지 않는다.
    """

    def construct(self):
        with self.cue("c001"):
            head = title("LoRA?")
            self.play(FadeIn(head), run_time=0.6)
        with self.cue("c002"):
            w = Square(2.0).set_fill(OBJ[0], 0.7).set_stroke(width=0)
            name = tex("W_0", size="L").next_to(w, DOWN, buff=BUFF[0])
            self.play(FadeIn(w), FadeIn(name, shift=UP * 0.25), run_time=1.0)
