# -*- coding: utf-8 -*-
"""
index.html 조립기
─────────────────────────────────────────────────────────
읽어들이는 것 (있는 것만 씁니다. 없으면 그 부분만 빠집니다)
  data/excel_master.json  … 엑셀 916명 (필수)
  api_raw.json            … 독립기념관 API 수집 결과 (선택)
  photo_credits.json      … 인물별 사진 출처 (선택)

만들어 내는 것
  index.html   … 더블클릭만으로 실행되는 단일 파일
  data.json    … 확인용 (앱은 이 파일을 읽지 않습니다)

실행:  python3 build_app.py
"""

import json
import os
import re
import sys
import unicodedata
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
EXCEL = os.path.join(HERE, "data", "excel_master.json")
API = os.path.join(HERE, "api_raw.json")
CREDITS = os.path.join(HERE, "photo_credits.json")
TEMPLATE = os.path.join(HERE, "app_template.html")
OUT_HTML = os.path.join(HERE, "index.html")
OUT_JSON = os.path.join(HERE, "data.json")

# ── 사진 저장소 주소 ────────────────────────────────
# 선생님의 GitHub 아이디와 저장소 이름을 받으면 아래 한 줄만 채우면 됩니다.
# 예: "https://raw.githubusercontent.com/philosophyAIEDU/dokrip-photos/main"
PHOTO_BASE = ""

DEFAULT_CREDIT = "국가보훈부 공훈전자사료관 · 독립기념관"

# ── 자료 기준일 ─────────────────────────────────────
# 엑셀을 내려받은 날짜입니다. 화면 맨 위에 "자료 기준일" 로 표시됩니다.
# api_raw.json 이 있으면 그 안의 수집 날짜가 이 값보다 우선합니다.
# 자료를 새로 받으면 이 날짜도 함께 고쳐 주세요.
DATA_DATE = "2026-08-12"

# 사진이 있는 훈격 (대한민국장 33명분만 존재)
PHOTO_ORDERS = {"대한민국장"}


def log(m):
    print(m, flush=True)


def load(path, what):
    if not os.path.exists(path):
        log("   · %s 없음 — 건너뜁니다 (%s)" % (os.path.basename(path), what))
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ══════════════════════════════════════════════════
#  인명 분해
# ══════════════════════════════════════════════════
HAN = re.compile(r"[一-鿿㐀-䶿]")


def split_name(full):
    """
    "김구(金九)"          → ("김구", "金九", "")
    "쑨원(손문)(孫文)"     → ("쑨원", "孫文", "손문")
    "조지 루이스 쇼(George Lewis Shaw)" → ("조지 루이스 쇼", "", "George Lewis Shaw")
    """
    full = unicodedata.normalize("NFC", str(full or "")).replace("\xa0", " ").strip()
    groups = re.findall(r"\(([^()]*)\)", full)
    head = re.sub(r"\(.*$", "", full).strip()

    hanja, other = "", ""
    for g in groups:
        g = g.strip()
        if not g:
            continue
        if HAN.search(g):
            hanja = g          # 한자가 들어 있는 마지막 괄호를 한자로 본다
        elif not other:
            other = g          # 한자가 아닌 첫 괄호는 다른 표기(음독/원어)
    return head, hanja, other


def photo_name(full):
    """사진 파일 이름 — 괄호를 모두 떼고 맨 앞 이름만 쓴다."""
    head, _, _ = split_name(full)
    return head


# ══════════════════════════════════════════════════
#  API 응답 가공
# ══════════════════════════════════════════════════
AUTHOR_RE = re.compile(r"[⋮:⋮]\s*([^⋮:⋮]{2,20}?)\s*[⋮:⋮]\s*$")
ORDER_RE = re.compile(r"^\s*([^()]+?)\s*\(\s*(\d{4})\s*\)\s*$")


def split_author(content):
    """content 끝의 ⋮집필자⋮ 를 떼어내 (본문, 집필자) 로 돌려준다."""
    if not content:
        return "", ""
    text = str(content).replace("\r", " ").strip()
    m = AUTHOR_RE.search(text)
    if not m:
        return text, ""
    author = m.group(1).strip()
    body = text[: m.start()].strip()
    return body, author


def split_order(orders):
    """ "대통령장(1962)" → ("대통령장", 1962) """
    if not orders:
        return "", None
    m = ORDER_RE.match(str(orders).strip())
    if m:
        try:
            return m.group(1).strip(), int(m.group(2))
        except ValueError:
            return m.group(1).strip(), None
    return str(orders).strip(), None


def tidy(v):
    if v is None:
        return ""
    s = re.sub(r"\s+", " ", str(v).replace("\xa0", " ")).strip()
    return "" if s in ("-", "null", "None") else s


# ══════════════════════════════════════════════════
#  조립
# ══════════════════════════════════════════════════
def build():
    log("=" * 58)
    log(" index.html 조립 시작")
    log("=" * 58)

    excel = load(EXCEL, "엑셀 916명")
    if not excel:
        log("!! data/excel_master.json 이 없어 만들 수 없습니다.")
        sys.exit(1)

    api = load(API, "API 수집 결과")
    credits = load(CREDITS, "사진 출처") or {}

    # ── 1) 엑셀을 뼈대로 인물 목록을 만든다 ──────────
    people = {}
    order_of = {}
    for order_label, group in excel.items():
        for r in group["records"]:
            name, hanja, other = split_name(r["인명"])
            if not name:
                continue
            # 이름과 한자까지 같은 동명이인이 있으므로 엑셀 번호를 함께 넣어 구분한다.
            # (API 의 생몰년이 들어오면 그것으로 다시 확인한다)
            pid = "%s|%s|%s|%s" % (name, hanja or other, order_label, r["번호"])
            people[pid] = {
                "id": pid,
                "name": name,
                "hanja": hanja,
                "koAlias": other,
                "alias": tidy(r["이명"]),
                "movement": tidy(r["운동계열"]),
                "birthplace": tidy(r["출생지"]),
                "order": order_label,
                "awardYear": tidy(r["포상년도"]),
            }
            order_of.setdefault(name, []).append(pid)

    log("")
    log(" 엑셀에서 %d명 읽음" % len(people))

    # ── 2) API 결과를 이름으로 맞춰 붙인다 ───────────
    matched = 0
    api_only = []
    used = set()
    if api:
        for label, g in (api.get("groups") or {}).items():
            for rec in g.get("records", []):
                nm = tidy(rec.get("name"))
                if not nm:
                    continue
                nm_head, _, _ = split_name(nm)
                cands = [pid for pid in order_of.get(nm_head, []) if pid not in used]
                if not cands:
                    api_only.append((label, nm_head))
                    continue

                # 같은 훈격인 사람만 남긴다
                same_order = [pid for pid in cands if people[pid]["order"] == label]
                cands = same_order or cands

                # 동명이인이면 출생지·운동계열로 한 번 더 가른다
                if len(cands) > 1:
                    born = tidy(rec.get("addressBirth")) or tidy(rec.get("placeOfOrigin"))
                    fam = tidy(rec.get("movementFamily"))
                    scored = []
                    for pid in cands:
                        p = people[pid]
                        s = 0
                        if born and p["birthplace"]:
                            a = re.sub(r"[\s()（）]", "", born)
                            bp = re.sub(r"[\s()（）]", "", p["birthplace"])
                            if a and bp and (a in bp or bp in a):
                                s += 2
                        if fam and p["movement"] and fam == p["movement"]:
                            s += 1
                        scored.append((s, pid))
                    scored.sort(key=lambda x: -x[0])
                    cands = [pid for _, pid in scored]

                target = cands[0]
                used.add(target)

                p = people[target]
                body, author = split_author(rec.get("content"))
                ord_name, ord_year = split_order(rec.get("orders"))

                if not p.get("hanja"):
                    p["hanja"] = tidy(rec.get("nameHanja"))
                p["bornDied"] = tidy(rec.get("bornDied"))
                p["orgs"] = tidy(rec.get("engagedOrganizations"))
                p["events"] = tidy(rec.get("engagedEvents"))
                p["activities"] = tidy(rec.get("activities"))
                if body:
                    p["content"] = body[:400]
                if author:
                    p["author"] = author
                if ord_year and not p.get("awardYear"):
                    p["awardYear"] = str(ord_year)
                if not p.get("birthplace"):
                    p["birthplace"] = tidy(rec.get("addressBirth")) or tidy(
                        rec.get("placeOfOrigin"))
                if not p.get("alias"):
                    p["alias"] = tidy(rec.get("aliases"))
                matched += 1
        log(" API 결과 %d명을 엑셀 인물에 연결" % matched)
        if api_only:
            log(" API 에만 있는 인물: %d명" % len(api_only))
    else:
        log(" API 결과 없음 — 엑셀 항목만으로 만듭니다")
        log("   (생몰년·주요활동·관련조직·관련사건·본문·집필자가 비어 있습니다)")

    # ── 3) 사진 URL 을 대한민국장에만 붙인다 ─────────
    photo_n = 0
    for p in people.values():
        if p["order"] not in PHOTO_ORDERS:
            continue
        if not PHOTO_BASE:
            continue
        fname = photo_name(p["name"]) + ".jpg"
        p["photo"] = PHOTO_BASE.rstrip("/") + "/photos/" + quote(fname)
        p["photoCredit"] = credits.get(p["name"], DEFAULT_CREDIT)
        photo_n += 1

    if PHOTO_BASE:
        log(" 사진 주소 %d명에 부여" % photo_n)
    else:
        log(" 사진 저장소 주소가 아직 비어 있어 사진 없이 만듭니다")
        log("   (build_app.py 의 PHOTO_BASE 한 줄만 채우면 됩니다)")

    # ── 4) 빈 값을 정리해 파일 크기를 줄인다 ─────────
    out = []
    for p in sorted(people.values(), key=lambda x: (x["order"], x["name"])):
        out.append({k: v for k, v in p.items() if v not in ("", None)})

    collected = (api or {}).get("collected_at") or DATA_DATE
    y, m, d = collected.split("-")
    payload = {
        "collected_at": collected,
        "collected_at_ko": "%d년 %d월 %d일" % (int(y), int(m), int(d)),
        "source": "독립기념관 한국독립운동인명사전 (search.i815.or.kr)",
        "people": out,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    # ── 5) 템플릿 안에 자료를 직접 심는다 ────────────
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()

    if "/*__DATA__*/" not in html:
        log("!! app_template.html 에 자료 자리표시자가 없습니다.")
        sys.exit(1)

    # </script> 가 자료 안에 들어가면 브라우저가 코드를 일찍 끊는다 — 막아 준다
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    embedded = embedded.replace("</", "<\\/")

    html = html.replace("/*__DATA__*/", embedded)

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(OUT_HTML)
    log("")
    log("=" * 58)
    log(" 완료")
    log("   %s  (%.1f MB)" % (OUT_HTML, size / 1024 / 1024))
    log("   %s" % OUT_JSON)
    log("   인물 %d명 / 사진 %d명" % (len(out), photo_n))
    log("=" * 58)

    return payload


if __name__ == "__main__":
    build()
