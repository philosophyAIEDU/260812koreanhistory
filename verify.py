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
        links = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]'))
              .map(a => ({href: a.href, target: a.target, rel: a.rel,
                          text: a.textContent.trim().replace(/\\s+/g,' ')}))""")
        check("바깥 링크는 공식 출처 하나뿐", len(links) == 1, "%d개" % len(links))
        if links:
            a = links[0]
            check("링크가 인명사전 공식 주소",
                  a["href"].startswith("https://search.i815.or.kr/dictionary/"), a["href"])
            check("새 창으로 열리고 안전하게 설정됨",
                  a["target"] == "_blank" and "noopener" in a["rel"],
                  "target=%s rel=%s" % (a["target"], a["rel"]))
            check("링크 문구에 기관·사전 이름 표기",
                  "독립기념관" in a["text"] and "한국독립운동인명사전" in a["text"], a["text"])
        bartxt = page.inner_text(".sourcebar")
        check("비상업적·교육적 목적 명시", "비상업적" in bartxt and "교육적" in bartxt)
        check("출처 띠가 머리말 바로 아래에 늘 보임",
              page.evaluate("""() => {
                  const b = document.querySelector('.sourcebar');
                  const t = document.querySelector('.top');
                  return b && b.offsetParent !== null &&
                         b.getBoundingClientRect().top >= t.getBoundingClientRect().bottom - 1;
              }"""))

        print("\n【2】 여덟 가지 활동이 모두 열리는가")
        acts = [("region", "s-region"), ("family", "s-family"), ("years", "s-years"),
                ("names", "s-names"), ("roll", "s-roll"), ("find", "s-find"),
                ("quest", "s-quest"), ("quizsetup", "s-quizsetup")]
        for go, sid in acts:
            page.click("#homeBtn")
            page.click('.menu button[data-go="%s"]' % go)
            page.wait_for_timeout(200)
            check("%s 화면" % go, page.locator("#" + sid).is_visible())
        page.click("#homeBtn"); page.wait_for_timeout(200)
        nums = page.evaluate("""() => Array.from(
            document.querySelectorAll('.menu .mnum')).map(x => x.textContent)""")
        check("활동에 번호 01~08", nums == ["01","02","03","04","05","06","07","08"],
              " ".join(nums))

        print("\n【3】 지역 → 명단 → 인물 → 이어보기")
        page.click("#homeBtn")
        page.click('.menu button[data-go="region"]')
        page.wait_for_timeout(200)
        cells = page.locator("#regionTiles .mapcell").count()
        check("지역 배치 그림 생성", cells >= 14, "%d칸" % cells)
        check("나라 밖·미상 따로 표시", page.locator("#regionTiles .tile").count() >= 5)
        shades = page.evaluate("""() => {
            const c = Array.from(document.querySelectorAll('#regionTiles .mapcell'));
            const bg = c.map(x => x.style.background);
            return new Set(bg).size;
        }""")
        check("인원에 따라 색이 다름", shades >= 10, "%d가지" % shades)
        page.locator('#regionTiles .mapcell[data-region="평북"]').click()
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

        print("\n【4-2】 막대가 실제로 채워져 그려지는가")
        page.click("#homeBtn"); page.wait_for_timeout(250)
        bars = page.evaluate("""() => {
            const bad = [];
            document.querySelectorAll('.bars .bar').forEach(b => {
              if (b.offsetParent === null) return;   // 숨겨진 화면은 건너뛴다
              const t = b.querySelector('.track'), f = b.querySelector('.fill');
              if (!t || !f) return;
              const th = t.getBoundingClientRect().height;
              const fh = f.getBoundingClientRect().height;
              const fw = f.getBoundingClientRect().width;
              if (fh < 4 || fh < th - 2 || fw < 1)
                bad.push(b.querySelector('.lbl').textContent +
                         ' 트랙' + Math.round(th) + ' 채움' + Math.round(fh) + 'x' + Math.round(fw));
            });
            return bad.slice(0, 4);
        }""")
        check("처음 화면 막대가 채워져 있음", not bars, "; ".join(bars))

        print("\n【5】 운동계열 · 연표 막대")
        page.click("#homeBtn")
        page.click('.menu button[data-go="family"]')
        page.wait_for_timeout(200)
        check("계열 막대 15개", page.locator("#familyBars .bar").count() == 15,
              "%d개" % page.locator("#familyBars .bar").count())
        page.locator("#familyBars .bar").first.click()
        page.wait_for_timeout(250)
        check("계열 상세 열림", page.locator("#s-family1").is_visible())
        fbad = page.evaluate("""() => {
            const bad = [];
            document.querySelectorAll('#s-family1 .bar').forEach(b => {
              if (b.offsetParent === null) return;
              const t=b.querySelector('.track'), f=b.querySelector('.fill');
              if(!t||!f) return;
              if(f.getBoundingClientRect().height < 4) bad.push(b.querySelector('.lbl').textContent);
            });
            return bad.slice(0,4);
        }""")
        check("계열 화면 막대가 채워져 있음", not fbad, "; ".join(fbad))
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

        print("\n【9-2】 오늘의 인물 · 발자취 · 찾아보기 과제")
        page.click("#homeBtn"); page.wait_for_timeout(250)
        t1 = page.inner_text("#todayCard")
        check("오늘의 인물 표시", "오늘 만나는 분" in t1)
        same = page.evaluate("""() => {
            const a = todayPerson().id, b = todayPerson().id;
            return a === b;
        }""")
        check("같은 날에는 같은 분 (반 전체가 동일)", same)
        check("발자취 표시", "발자취" in page.inner_text("#trackBox"))
        page.click("#todayCard"); page.wait_for_timeout(250)
        check("오늘의 인물을 눌러 카드로 이동", page.locator("#s-person").is_visible())

        page.click("#homeBtn")
        page.click('.menu button[data-go="quest"]')
        page.wait_for_timeout(250)
        nq = page.locator("#questList .quest").count()
        check("과제 5개 제시", nq == 5, "%d개" % nq)
        check("답이 처음에는 감춰져 있음",
              page.locator("#questList .qa:visible").count() == 0)
        page.locator('#questList .quest [data-act="ans"]').first.click()
        page.wait_for_timeout(200)
        check("답 맞춰보기 동작", page.locator("#questList .qa:visible").count() == 1)
        # 과제의 답이 실제 자료와 맞는지 확인
        acc = page.evaluate("""() => {
            const bad = [];
            for(let t=0;t<40;t++){
              makeQuests().forEach(q => {
                if(/에서 태어난 분은 모두 몇 분/.test(q.q) && !/나라 밖/.test(q.q)){
                  const rg = q.q.split('에서')[0];
                  const real = PEOPLE.filter(p => p._region === rg).length + '명';
                  if(real !== q.a) bad.push(q.q + ' → ' + q.a + ' / 실제 ' + real);
                }
                if(/계열에는 모두 몇 분/.test(q.q)){
                  const fm = q.q.split('\u2018')[1].split('\u2019')[0];
                  const real = PEOPLE.filter(p => p.movement === fm).length + '명';
                  if(real !== q.a) bad.push(q.q + ' → ' + q.a + ' / 실제 ' + real);
                }
                if(/나라 밖에서 태어난 분/.test(q.q)){
                  const real = PEOPLE.filter(p => !MAP_POS[p._region] &&
                                 p._region !== '미상').length + '명';
                  if(real !== q.a) bad.push(q.q + ' → ' + q.a + ' / 실제 ' + real);
                }
                if(/년대에 훈장이 드려진 분은/.test(q.q)){
                  const d = parseInt(q.q,10);
                  const real = PEOPLE.filter(p => /^\d{4}$/.test(p.awardYear||'') &&
                                 Math.floor(+p.awardYear/10)*10 === d).length + '명';
                  if(real !== q.a) bad.push(q.q + ' → ' + q.a + ' / 실제 ' + real);
                }
              });
            }
            return bad.slice(0,3);
        }""")
        check("과제의 답이 자료와 일치", not acc, "; ".join(acc))
        page.click("#questNew"); page.wait_for_timeout(250)
        check("다른 물음으로 바꾸기 동작", page.locator("#questList .quest").count() == 5)

        print("\n【9-3】 사진 — 있으면 제대로 나오는지, 없으면 흔적이 없는지")
        ph = page.evaluate("""() => {
            const withPhoto = PEOPLE.filter(p => p.photo);
            const grand = PEOPLE.filter(p => p.order === '대한민국장');
            return {n: withPhoto.length,
                    grand: grand.length,
                    grandWith: grand.filter(p => p.photo).length,
                    otherWith: withPhoto.filter(p => p.order !== '대한민국장').length,
                    allData: withPhoto.every(p => p.photo.startsWith('data:image/')),
                    creditAll: withPhoto.every(p => p.photoCredit)};
        }""")

        if ph["n"] == 0:
            # 사진을 넣지 않은 상태 — 사진 흔적이 아예 없어야 한다
            check("사진 없음 — 인물 자료에 사진 항목이 없음", True, "0장")
            check("사진 없음 — 사진 영역이 만들어지지 않음",
                  page.evaluate("""() => PEOPLE.slice(0,80)
                        .every(p => photoBlock(p) === '')"""))
            noq = page.evaluate("""() => {
                let made = 0;
                ['elem','mid','high'].forEach(g => {
                  state.grade=g; state.orders=['대한민국장']; state.pool=computePool();
                  for(let t=0;t<15;t++)
                    makeQuiz().forEach(q => { if(q.type==='사진') made++; });
                });
                return made;
            }""")
            check("사진 없음 — 사진 문항이 출제되지 않음", noq == 0, "%d문항" % noq)
            check("사진 없음 — 화면에 이미지 태그가 없음",
                  page.evaluate("document.images.length") == 0,
                  "%d개" % page.evaluate("document.images.length"))
        else:
            check("대한민국장 전원 사진", ph["grandWith"] == ph["grand"],
                  "%d/%d" % (ph["grandWith"], ph["grand"]))
            check("다른 훈격에는 사진 없음", ph["otherWith"] == 0, "%d명" % ph["otherWith"])
            check("사진이 파일 안에 심겨 있음 (인터넷 불필요)", ph["allData"])
            check("사진마다 출처 표기", ph["creditAll"])

            page.click("#homeBtn")
            page.click('.menu button[data-go="find"]')
            page.fill("#findInput", "김구")
            page.wait_for_timeout(300)
            page.locator("#findRoster .rname").first.click()
            page.wait_for_timeout(500)
            img = page.evaluate("""() => {
                const i = document.querySelector('#s-person .photo-box img');
                if (!i) return null;
                return {shown: i.parentNode.style.display !== 'none',
                        w: i.naturalWidth,
                        credit: (document.querySelector('#s-person .photo-credit')||{}).textContent};
            }""")
            check("인터넷 없이도 사진이 실제로 그려짐",
                  bool(img and img["shown"] and img["w"] > 0),
                  "naturalWidth=%s" % (img and img["w"]))
            check("사진 아래 출처 표시", bool(img) and "사진 출처" in (img["credit"] or ""))

            pq = page.evaluate("""() => {
                let bad = 0, made = 0;
                ['elem','mid','high'].forEach(g => {
                  state.grade=g; state.orders=['대한민국장']; state.pool=computePool();
                  for(let t=0;t<15;t++){
                    makeQuiz().forEach(q => {
                      if(q.type !== '사진') return;
                      made++;
                      if(!q.person.photo) bad++;
                      q.choices.forEach(c => { if(!BY_ID[c.id].photo) bad++; });
                    });
                  }
                });
                return {bad, made};
            }""")
            check("사진 문항이 출제됨", pq["made"] > 0, "%d문항" % pq["made"])
            check("사진 문항의 정답·오답 모두 사진 보유", pq["bad"] == 0, "%d건" % pq["bad"])

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

        banned = ["꽝", "실패!", "수집", "모으기", "등수", "순위", "1등", "랭킹",
                  "일제감시대상인물카드", "붙잡아 가두고", "체포·감시하며 남긴"]
        body = page.evaluate("document.body.innerText")
        found = [w for w in banned if w in body]
        check("금지 표현·사진 설명 문구 없음", not found, ",".join(found))
        # 사진 아래에는 출처 한 줄만 있어야 한다
        page.click("#homeBtn")
        page.click('.menu button[data-go="find"]')
        page.fill("#findInput", "유관순")
        page.wait_for_timeout(300)
        if page.locator("#findRoster .rname").count():
            page.locator("#findRoster .rname").first.click()
            page.wait_for_timeout(500)
            pb = page.evaluate("""() => {
                const box = document.querySelector('#s-person .photo-box');
                if (!box) return null;
                return {kids: Array.from(box.children).map(c => c.className || c.tagName),
                        text: box.innerText.trim()};
            }""")
            if pb:
                check("사진 아래에 출처 한 줄만",
                      pb["kids"] == ["IMG", "photo-credit"], str(pb["kids"]))
                check("사진에 덧붙인 설명 문구 없음",
                      pb["text"].startswith("사진 출처:") and "\n" not in pb["text"],
                      pb["text"].replace("\n", " / "))

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
