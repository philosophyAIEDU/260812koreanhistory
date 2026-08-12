# -*- coding: utf-8 -*-
"""index.html 자체 검수 — 실제 브라우저로 확인한다."""
import json
import sys
from playwright.sync_api import sync_playwright

PATH = "file:///home/user/260812koreanhistory/index.html"
fails = []
notes = []


def check(name, ok, detail=""):
    print(("  [OK] " if ok else "  [!!] ") + name + ((" — " + detail) if detail else ""))
    if not ok:
        fails.append(name + (" — " + detail if detail else ""))


def run():
    with sync_playwright() as pw:
        # 인터넷을 끊은 상태를 흉내낸다: 외부 요청을 전부 막는다
        browser = pw.chromium.launch(headless=True, executable_path="/opt/pw-browsers/chromium", args=["--no-sandbox"])
        ctx = browser.new_context(offline=True)
        page = ctx.new_page()

        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text)
                if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        page.goto(PATH)
        page.wait_for_timeout(400)

        print("\n【1】 인터넷을 끊은 상태에서 실행")
        check("페이지가 뜬다", page.locator("#screen-start").is_visible())
        check("자바스크립트 오류 없음", not console_errors, "; ".join(console_errors[:3]))
        check("자료 기준일 표시", "자료 기준일" in page.locator("#baseDate").inner_text())
        check("하단 출처 4줄 고정", page.locator(".foot span").count() == 4)
        check("개인정보 입력란 없음",
              page.locator("input[type=text], input[type=email], textarea").count() == 0)
        total = page.evaluate("PEOPLE.length")
        check("인물 916명 적재", total == 916, "실제 %d명" % total)

        print("\n【2】 훈격 3개를 각각 골랐을 때")
        for order in ["대한민국장", "대통령장", "독립장"]:
            for grade in ["elem", "mid", "high"]:
                res = page.evaluate(
                    """([order, grade]) => {
                      state.grade = grade;
                      state.orders = [order];
                      state.moves = [];
                      state.pool = computePool();
                      const seen = {};
                      let bad = 0, made = 0, dupAns = 0, photoNoPhoto = 0;
                      for (let t = 0; t < 12; t++) {
                        const seenIds = [];
                        state.study = shuffle(state.pool).slice(0,5);
                        const qs = makeQuiz();
                        made += qs.length;
                        if (qs.length < 10) bad++;
                        qs.forEach(q => {
                          seen[q.type] = (seen[q.type]||0)+1;
                          const texts = q.choices.map(c => c.text);
                          if (new Set(texts).size !== texts.length) dupAns++;
                          const ansTxt = q.choices[q.answerIdx].text;
                          if (texts.filter(x => x === ansTxt).length !== 1) dupAns++;
                          if (q.type === '사진') {
                            if (!q.person.photo) photoNoPhoto++;
                            q.choices.forEach(c => {
                              const p = BY_ID[c.id];
                              if (p && !p.photo) photoNoPhoto++;
                            });
                          }
                        });
                      }
                      return {bad, made, dupAns, photoNoPhoto, types: seen,
                              pool: state.pool.length};
                    }""",
                    [order, grade])
                label = "%s / %s" % (order, {"elem": "초등", "mid": "중등",
                                             "high": "고등"}[grade])
                check("%s — 10문항 생성" % label, res["bad"] == 0,
                      "12회 중 %d회 부족 (평균 %.1f문항)" % (res["bad"], res["made"]/12))
                check("%s — 선택지에 정답 중복 없음" % label, res["dupAns"] == 0,
                      "%d건" % res["dupAns"])
                check("%s — 사진 없는 인물에 사진 문항 없음" % label,
                      res["photoNoPhoto"] == 0, "%d건" % res["photoNoPhoto"])
                notes.append((label, res["pool"], res["types"]))

        print("\n【3】 학년별로 실제로 다르게 동작하는가")
        multi = page.evaluate(
            """() => {
              state.orders = ['대한민국장','대통령장','독립장'];
              state.moves = [];
              state.pool = computePool();
              const out = {};
              ['elem','mid','high'].forEach(g => {
                state.grade = g;
                const types = {};
                for (let t=0;t<15;t++){
                  state.study = shuffle(state.pool).slice(0,5);
                  makeQuiz().forEach(q => types[q.type]=(types[q.type]||0)+1);
                }
                out[g] = types;
              });
              return out;
            }""")
        for g, lab in [("elem", "초등"), ("mid", "중등"), ("high", "고등")]:
            print("      %s 출제 유형: %s" % (lab, multi[g]))
        check("초등과 고등의 카드 내용이 다름",
              page.evaluate("""() => {
                 const p = PEOPLE[0];
                 state.grade='elem'; const a = personCard(p);
                 state.grade='high'; const b = personCard(p);
                 return a !== b;
              }"""))

        print("\n【4】 실제로 눌러서 끝까지 진행")
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_timeout(300)
        page.locator('#gradePick .pick[data-grade="mid"]').click()
        page.locator('#orderPick .pick[data-order="대한민국장"]').click()
        # 대한민국장이 기본 선택이라 위 클릭이 해제일 수 있으니 상태를 확인해 맞춘다
        if page.evaluate("state.orders.length") == 0:
            page.locator('#orderPick .pick[data-order="대한민국장"]').click()
        page.locator("#startBtn").click()
        page.wait_for_timeout(300)
        check("인물 카드 화면으로 이동", page.locator("#screen-card").is_visible())
        for _ in range(5):
            page.locator("#cardNext").click()
            page.wait_for_timeout(150)
        check("퀴즈 화면으로 이동", page.locator("#screen-quiz").is_visible())

        for i in range(10):
            page.keyboard.press("1")
            page.wait_for_timeout(120)
            vis = page.locator("#verdictBox .verdict").count()
            if vis == 0:
                check("%d번 문항 채점 표시" % (i + 1), False)
                break
            page.keyboard.press("Enter")
            page.wait_for_timeout(150)
        check("결과 화면 도달", page.locator("#screen-result").is_visible())
        check("누적 인원 표시", "기억한 독립운동가" in page.locator("#tallyLine").inner_text())

        print("\n【5】 깨진 이미지 / 큰 화면 모드")
        broken = page.evaluate("""() => {
            const imgs = Array.from(document.images);
            return imgs.filter(i => i.complete && i.naturalWidth === 0 &&
                                    i.offsetParent !== null).length;
        }""")
        check("화면에 깨진 이미지 없음", broken == 0, "%d개" % broken)
        before = page.evaluate("getComputedStyle(document.documentElement).fontSize")
        page.locator("#bigToggle").click()
        page.wait_for_timeout(150)
        after = page.evaluate("getComputedStyle(document.documentElement).fontSize")
        check("큰 화면 모드 1.5배", abs(float(after[:-2]) / float(before[:-2]) - 1.5) < 0.01,
              "%s → %s" % (before, after))

        check("전 과정 자바스크립트 오류 없음", not console_errors,
              "; ".join(console_errors[:3]))
        browser.close()


run()
print("\n" + "=" * 58)
if fails:
    print(" 실패 %d건" % len(fails))
    for f in fails:
        print("   - " + f)
else:
    print(" 전 항목 통과")
print("=" * 58)
sys.exit(1 if fails else 0)
