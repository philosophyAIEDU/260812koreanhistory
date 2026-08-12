# -*- coding: utf-8 -*-
"""
독립기념관 한국독립운동인명사전 수집기
─────────────────────────────────────────────────────────
선생님 컴퓨터에서 한 번만 실행하면 됩니다.
추가로 설치할 것은 아무것도 없습니다. (파이썬 기본 기능만 사용)

실행 방법
  1) 파이썬 설치 (https://www.python.org/downloads/ 에서 Download 버튼)
     ※ 설치할 때 "Add Python to PATH" 체크박스를 꼭 켜세요.
  2) 이 파일이 있는 폴더에서 명령 프롬프트를 열고:  python fetch_data.py
     (또는 파일을 더블클릭)
  3) 끝나면 같은 폴더에 api_raw.json 이 생깁니다. 그 파일을 저에게 올려주세요.

약 93번 요청하며 1분 정도 걸립니다. 중간에 창을 닫지 마세요.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import date

BASE = "https://search.i815.or.kr/openApiData.do"
TYPE = 4                      # 4 = 인명사전 (고정)
ORDERS = [                    # 이번에 수집할 훈격
    ("AA", "대한민국장"),
    ("AB", "대통령장"),
    ("AC", "독립장"),
]
DELAY = 0.5                   # 요청 사이 대기 (초)
RETRIES = 3                   # 실패 시 재시도 횟수
TIMEOUT = 30

OUT_FILE = "api_raw.json"
SAMPLE_FILE = "sample_response.txt"


def log(msg):
    """진행 상황을 한 줄씩 출력한다."""
    print(msg, flush=True)


def http_get(url):
    """URL 을 읽어 문자열로 돌려준다. 실패하면 RETRIES 회까지 다시 시도한다."""
    last_error = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (educational data collection)",
                    "Accept": "application/json, text/plain, */*",
                },
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
            # 인코딩 자동 판별 (UTF-8 우선, 안 되면 EUC-KR)
            for enc in ("utf-8", "euc-kr", "cp949"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")
        except Exception as e:                      # noqa: BLE001
            last_error = e
            if attempt < RETRIES:
                wait = attempt * 2
                log("      · 실패(%d/%d) %s — %d초 후 재시도"
                    % (attempt, RETRIES, e, wait))
                time.sleep(wait)
    raise RuntimeError("요청 실패: %s (%s)" % (url, last_error))


def parse(text):
    """응답 문자열을 파이썬 자료로 바꾼다. JSON 이 아니면 원문 그대로 돌려준다."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_unparsed_raw": text}


def find_records(payload):
    """
    응답 구조가 확실하지 않으므로, 사람 정보가 들어 있을 법한 리스트를 찾아낸다.
    name 또는 nameHanja 키를 가진 사전(dict) 들의 리스트를 사람 목록으로 본다.
    """
    found = []

    def walk(node):
        if isinstance(node, list):
            people = [x for x in node
                      if isinstance(x, dict)
                      and ("name" in x or "nameHanja" in x)]
            if people:
                found.append(people)
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    walk(payload)
    if not found:
        return []
    # 가장 긴 리스트를 사람 목록으로 채택
    return max(found, key=len)


def find_number(payload, keys):
    """total_count / page_count 처럼 이름이 조금씩 다를 수 있는 숫자 값을 찾는다."""
    wanted = {k.lower().replace("_", "") for k in keys}

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower().replace("_", "") in wanted:
                    try:
                        return int(str(v).strip())
                    except (TypeError, ValueError):
                        pass
                r = walk(v)
                if r is not None:
                    return r
        elif isinstance(node, list):
            for v in node:
                r = walk(v)
                if r is not None:
                    return r
        return None

    return walk(payload)


def collect_one(code, label, sample_holder):
    """훈격 하나(code)의 전체 페이지를 수집한다."""
    log("")
    log("[%s / %s] 수집 시작" % (code, label))

    first_url = "%s?type=%d&orders=%s&page=1" % (BASE, TYPE, code)
    text = http_get(first_url)

    # 첫 응답 원문을 한 번만 따로 저장해 둔다 (구조 확인용)
    if sample_holder["text"] is None:
        sample_holder["text"] = text

    payload = parse(text)

    total = find_number(payload, ["totalCount", "total_count", "total", "totCnt"])
    pages = find_number(payload, ["pageCount", "page_count", "totalPage", "pageTotal"])

    records = find_records(payload)
    per_page = len(records) if records else 10

    if pages is None:
        if total and per_page:
            pages = (total + per_page - 1) // per_page
        else:
            pages = 1

    log("   총 인원: %s / 전체 페이지: %s (1페이지에 %d건)"
        % (total if total is not None else "?", pages, per_page))

    if not records:
        log("   ⚠ 1페이지에서 인물 목록을 찾지 못했습니다.")
        log("     %s 파일을 저에게 보내주시면 구조를 맞추겠습니다." % SAMPLE_FILE)

    all_records = list(records)
    log("   1/%s 페이지 … 누적 %d명" % (pages, len(all_records)))

    for page in range(2, pages + 1):
        time.sleep(DELAY)
        url = "%s?type=%d&orders=%s&page=%d" % (BASE, TYPE, code, page)
        page_records = find_records(parse(http_get(url)))
        all_records.extend(page_records)
        log("   %d/%s 페이지 … 누적 %d명" % (page, pages, len(all_records)))

    log("[%s / %s] 완료 — %d명" % (code, label, len(all_records)))
    return {
        "code": code,
        "label": label,
        "reported_total": total,
        "reported_pages": pages,
        "collected": len(all_records),
        "records": all_records,
    }


def main():
    log("=" * 58)
    log(" 독립기념관 한국독립운동인명사전 수집")
    log(" 수집일: %s" % date.today().isoformat())
    log("=" * 58)

    sample_holder = {"text": None}
    result = {
        "collected_at": date.today().isoformat(),
        "source": "독립기념관 한국독립운동인명사전 (search.i815.or.kr)",
        "api": BASE,
        "groups": {},
    }

    try:
        for code, label in ORDERS:
            result["groups"][label] = collect_one(code, label, sample_holder)
    except Exception as e:                          # noqa: BLE001
        log("")
        log("!! 오류가 나서 멈췄습니다: %s" % e)
        log("   인터넷 연결을 확인하고 다시 실행해 주세요.")
        log("   계속 같은 오류가 나면 이 화면을 그대로 캡처해 보내주세요.")

    if sample_holder["text"] is not None:
        with open(SAMPLE_FILE, "w", encoding="utf-8") as f:
            f.write(sample_holder["text"])

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    total = sum(g["collected"] for g in result["groups"].values())
    log("")
    log("=" * 58)
    for label, g in result["groups"].items():
        log(" %s : %d명" % (label, g["collected"]))
    log(" 합계 : %d명" % total)
    log("")
    log(" 저장 완료 → %s" % os.path.abspath(OUT_FILE))
    log(" 참고 파일 → %s" % os.path.abspath(SAMPLE_FILE))
    log("")
    log(" 이 두 파일을 클로드에게 올려주세요.")
    log("=" * 58)

    if sys.stdin and sys.stdin.isatty():
        try:
            input("\n엔터를 누르면 창이 닫힙니다…")
        except EOFError:
            pass


if __name__ == "__main__":
    main()
