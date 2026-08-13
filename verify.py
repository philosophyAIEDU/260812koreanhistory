# -*- coding: utf-8 -*-
"""index.html 자체 검수 — 인터넷을 끊은 실제 브라우저로 확인한다."""
import sys
from playwright.sync_api import sync_playwright

PATH = "file:///home/user/260812koreanhistory/index.html"
CHROME = "/opt/pw-browsers/chromium"
fails = []


def check(name, ok, detail=""):
    print(("  [OK] " if ok else "  [!!] ") + name + ((" — " + detail) if detail else ""))
    if not ok:
        fails.append(name + (" — " + detail if detail else ""))


def run():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=CHROME,
                                     args=["--no-sandbox"])
        # offline=True : 인터넷이 없는 교실을 그대로 흉내낸다
        ctx = browser.new_context(offline=True, viewport={"width": 900, "height": 1000})
        page = ctx.new_page()
        errs = []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errs.append(str(e)))

        page.goto(PATH)
        page.wait_for_timeout(400)

        print("\n【1】 인터넷을 끊은 상태")
        check("페이지가 뜬다", page.locator("#s-home").is_visible())
        check("자바스크립트 오류 없음", not errs, "; ".join(errs[:3]))
        check("916명 적재", page.evaluate("PEOPLE.length") == 916)
        check("자료 기준일 표시", "자료 기준일" in page.inner_text("#baseDate"))
        check("하단 출처 4줄 고정", page.locator(".foot span").count() == 4)
        check("학생 개인정보 입력란 없음",
              page.evaluate("""() => Array.from(document.querySelectorAll('input'))
                     .filter(i => i.type !== 'search').length""") == 0)
        check("외부 링크 없음",
              page.evaluate("document.querySelectorAll('a[href^=http]').length") == 0)

        print("\n【2】 일곱 가지 활동이 모두 열리는가")
        acts = [("region", "s-region"), ("family", "s-family"), ("years", "s-years"),
                ("names", "s-names"), ("roll", "s-roll"), ("find", "s-find"),
                ("quizsetup", "s-quizsetup")]
        for go, sid in acts:
            page.click("#homeBtn")
            page.click('.menu button[data-go="%s"]' % go)
            page.wait_for_timeout(200)
            check("%s 화면" % go, page.locator("#" + sid).is_visible())

        print("\n【3】 지역 → 명단 → 인물 → 이어보기")
        page.click("#homeBtn")
        page.click('.menu button[data-go="region"]')
        page.wait_for_timeout(200)
        tiles = page.locator("#regionTiles .tile").count()
        check("지역 타일 생성", tiles >= 15, "%d개" % tiles)
        page.locator('#regionTiles .tile[data-region="평북"]').click()
        page.wait_for_timeout(250)
        check("평북 명단 124명",
              "124명" in page.inner_text("#listCount"), page.inner_text("#listCount"))
        page.locator("#listRoster .rname").first.click()
        page.wait_for_timeout(250)
        check("인물 화면 열림", page.locator("#s-person").is_visible())
        check("이어서 보기 버튼", page.locator("#goSameRegion").is_visible())
        page.click("#goSameFam")
        page.wait_for_timeout(250)
        check("계열로 이어보기 동작", page.locator("#s-list").is_visible())

        print("\n【4】 명단 좁혀 보기 · 이름으로 찾기")
        page.fill("#listSearch", "김")
        page.wait_for_timeout(250)
        n1 = page.inner_text("#listCount")
        check("이름으로 좁히기 동작", "가운데" in n1, n1)
        page.click("#homeBtn")
        page.click('.menu button[data-go="find"]')
        page.fill("#findInput", "김구")
        page.wait_for_timeout(250)
        check("이름 찾기 결과", "찾았습니다" in page.inner_text("#findCount"),
              page.inner_text("#findCount"))
        page.fill("#findInput", "金九")
        page.wait_for_timeout(250)
        check("한자로도 찾기", "찾았습니다" in page.inner_text("#findCount"))
        page.fill("#findInput", "없는이름xyz")
        page.wait_for_timeout(250)
        check("없는 이름 처리", "없습니다" in page.inner_text("#findCount"))

        print("\n【5】 운동계열 · 연표 막대")
        page.click("#homeBtn")
        page.click('.menu button[data-go="family"]')
        page.wait_for_timeout(200)
        check("계열 막대 15개", page.locator("#familyBars .bar").count() == 15,
              "%d개" % page.locator("#familyBars .bar").count())
        page.locator("#familyBars .bar").first.click()
        page.wait_for_timeout(250)
        check("계열 상세 열림", page.locator("#s-family1").is_visible())
        check("출생지 분포 표시", page.locator("#f1Region .bar").count() > 0)
        check("포상연도 분포 표시", page.locator("#f1Years .bar").count() > 0)
        page.click("#f1List")
        page.wait_for_timeout(250)
        check("계열 명단 열림", page.locator("#s-list").is_visible())

        page.click("#homeBtn")
        page.click('.menu button[data-go="years"]')
        page.wait_for_timeout(200)
        bars = page.locator("#yearsBars .bar").count()
        check("연표 막대", bars >= 7, "%d개" % bars)
        page.locator("#yearsBars .bar").nth(2).click()
        page.wait_for_timeout(250)
        check("연대별 명단 열림", page.locator("#s-list").is_visible())

        print("\n【6】 이름 부르기")
        page.click("#homeBtn")
        page.click('.menu button[data-go="roll"]')
        page.wait_for_timeout(200)
        first = page.inner_text("#rollBox")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(200)
        check("다음 분으로 넘어감", page.inner_text("#rollBox") != first)
        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(200)
        check("이전으로 돌아옴", page.inner_text("#rollBox") == first)
        check("진행 표시", "/ 916" in page.inner_text("#rollProgress"))

        print("\n【7】 학년별로 다르게 보이는가")
        diff = page.evaluate("""() => {
            const p = PEOPLE.find(x => x.alias && x.alias.length > 80);
            state.grade='elem'; const a = personCard(p);
            state.grade='mid';  const b = personCard(p);
            state.grade='high'; const c = personCard(p);
            return {ab: a!==b, bc: b!==c,
                    elemShort: a.length < b.length,
                    labels: [a.includes('태어난 곳'), b.includes('출생지')]};
        }""")
        check("초등과 중등 카드가 다름", diff["ab"])
        check("중등과 고등 카드가 다름", diff["bc"])
        check("초등은 이명을 줄여 보여줌", diff["elemShort"])
        check("학년별 용어가 바뀜", diff["labels"] == [True, True])

        print("\n【8】 확인해 보기 (문제)")
        res = page.evaluate("""() => {
          const out = {};
          ['대한민국장','대통령장','독립장'].forEach(o => {
            ['elem','mid','high'].forEach(g => {
              state.grade=g; state.orders=[o]; state.pool=computePool();
              let short=0, dup=0, made=0; const types={};
              for(let t=0;t<12;t++){
                const qs=makeQuiz(); made+=qs.length;
                if(qs.length<10) short++;
                qs.forEach(q=>{
                  types[q.type]=(types[q.type]||0)+1;
                  const tx=q.choices.map(c=>c.text);
                  if(new Set(tx).size!==tx.length) dup++;
                  if(tx.filter(x=>x===q.choices[q.answerIdx].text).length!==1) dup++;
                });
              }
              out[o+'/'+g]={short,dup,avg:made/12,types};
            });
          });
          return out;
        }""")
        for k, v in res.items():
            check("%s — 10문항" % k, v["short"] == 0, "평균 %.1f" % v["avg"])
            check("%s — 정답 중복 없음" % k, v["dup"] == 0, "%d건" % v["dup"])
        print("      초등 유형:", res["독립장/elem"]["types"])
        print("      중등 유형:", res["독립장/mid"]["types"])
        print("      고등 유형:", res["독립장/high"]["types"])
        et = set(res["독립장/elem"]["types"])
        mt = set(res["독립장/mid"]["types"])
        ht = set(res["독립장/high"]["types"])
        check("초등과 중등 출제 유형이 다름", et != mt)
        check("중등과 고등 출제 유형이 다름", mt != ht, "중등 %d종 / 고등 %d종" % (len(mt), len(ht)))

        print("\n【9】 문제를 끝까지 풀어 보기")
        page.evaluate("localStorage.clear()")
        page.reload(); page.wait_for_timeout(300)
        page.click('.menu button[data-go="quizsetup"]')
        page.wait_for_timeout(200)
        page.click("#startQuiz")
        page.wait_for_timeout(300)
        check("문제 화면 열림", page.locator("#s-quiz").is_visible())
        for i in range(10):
            page.keyboard.press("1")
            page.wait_for_timeout(110)
            if page.locator("#verdictBox .verdict").count() == 0:
                check("%d번 채점 표시" % (i+1), False)
                break
            page.keyboard.press("Enter")
            page.wait_for_timeout(130)
        check("결과 화면 도달", page.locator("#s-result").is_visible())
        check("누적 인원 표시", "만난 독립운동가" in page.inner_text("#tallyLine"))

        print("\n【10】 사진 · 큰 화면 · 어투")
        broken = page.evaluate("""() => Array.from(document.images)
              .filter(i => i.complete && i.naturalWidth===0 && i.offsetParent!==null).length""")
        check("깨진 이미지 없음", broken == 0, "%d개" % broken)
        with_photo = page.evaluate("PEOPLE.filter(p=>p.photo).length")
        no_photo_q = page.evaluate("""() => {
            let bad=0;
            PEOPLE.slice(0,60).forEach(p => { if(!p.photo && photoBlock(p) !== '') bad++; });
            return bad;
        }""")
        check("사진 없는 인물은 사진 영역 자체가 없음", no_photo_q == 0,
              "사진 보유 %d명" % with_photo)
        before = page.evaluate("getComputedStyle(document.documentElement).fontSize")
        page.click("#bigToggle"); page.wait_for_timeout(150)
        after = page.evaluate("getComputedStyle(document.documentElement).fontSize")
        check("큰 화면 1.5배", abs(float(after[:-2])/float(before[:-2]) - 1.5) < .01,
              "%s → %s" % (before, after))

        banned = ["꽝", "실패!", "수집", "모으기", "등수", "순위", "1등", "랭킹"]
        body = page.evaluate("document.body.innerText")
        found = [w for w in banned if w in body]
        check("경박한 표현 없음", not found, ",".join(found))

        check("전 과정 오류 없음", not errs, "; ".join(errs[:3]))
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
