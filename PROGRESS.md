# 독립운동가 인물 사전 퀴즈 앱 — 진행 상황

마지막 갱신: 2026-08-12

## 현재 단계
**0단계 완료 / 2단계 앱 뼈대 완성 / 1단계(API 수집)만 대기 중**

`index.html` 이 이미 만들어져 있고 브라우저 검수를 전부 통과했습니다.
다만 엑셀 6개 항목만 들어 있어, API 데이터가 오면 `python3 build_app.py` 한 번으로
생몰년·활동·조직·사건·본문·집필자가 채워지고 문항 유형도 8가지로 늘어납니다.

### 파일 구성
| 파일 | 역할 |
|---|---|
| `app_template.html` | 앱 본체 (자료 자리는 `/*__DATA__*/`) |
| `build_app.py` | 자료를 본체에 부어 넣어 `index.html` 을 만든다 |
| `fetch_data.py` | 독립기념관 API 수집기 (선생님 PC에서 실행 가능) |
| `data/excel_master.json` | 엑셀 916명 |
| `index.html` | **완성물 — 더블클릭으로 실행** |

### API 데이터가 도착하면
1. `api_raw.json` 을 이 폴더에 둔다
2. `python3 build_app.py` 실행 → 끝

### 사진 주소를 알게 되면
`build_app.py` 의 `PHOTO_BASE = ""` 한 줄만 채우고 다시 실행.

## 완료된 것

### 엑셀 3개 확인 완료 ✅
`data/excel_master.json` 에 916명 전원 저장 완료.
컬럼: 번호 · 인명 · 이명 · 운동계열 · 출생지 · 포상년도

| 훈격 | 인원 | 운동계열 종류 |
|---|---|---|
| 대한민국장 | 33 | 9 |
| 대통령장 | 89 | 12 |
| 독립장 | 794 | 15 |
| 합계 | **916** | |

인명 형식 확인: `김구(金九)` / 외국인 `쑨원(손문)(孫文)`, `장제스(장개석)(蔣介石)`

## 막혀 있는 것

### 1. 독립기념관 API 차단 ⛔
```
https://search.i815.or.kr/openApiData.do?type=4&orders=AA&page=1
→ 403 (CONNECT tunnel failed) — 클라우드 환경 egress 정책에 의한 차단
```
`raw.githubusercontent.com` 은 200 정상. i815 도메인만 막힘.

**해결 방법**: claude.ai/code 메시지 입력창 위 구름 아이콘 → 환경 설정 →
Network access 를 **Custom** 으로 바꾸고 Allowed domains 에 아래 추가

```
search.i815.or.kr
raw.githubusercontent.com
```
+ "Also include default list of common package managers" 체크

> 환경 설정은 세션 시작 시점에 적용되므로, 변경 후 **새 세션**을 시작해야 할 수 있음.

### 2. 사진 저장소 주소 미확인 ⛔
사용자의 GitHub 아이디 / 저장소 이름을 아직 받지 못함.
현재 세션 저장소(`philosophyAIEDU/260812koreanhistory`)에는 photos 폴더 없음 (404 확인).

필요 형식: `https://raw.githubusercontent.com/{아이디}/{저장소}/main/photos/{한글이름}.jpg`
사진은 대한민국장 33명분만 존재.

## 남은 단계
- **1단계** — `fetch_data.py` 작성 후 실행 (AA 4p + AB 9p + AC 80p = 약 93회 요청,
  요청 간 0.5초 대기, 실패 시 3회 재시도)
  - content 앞 400자만 저장, references 미저장
  - `⋮집필자⋮` 정규식 추출 → author 필드, 본문에서 제거
  - orders `"대통령장(1962)"` → 훈격/포상연도 분리
  - 고유 id = 이름 + 생몰년
  - 대한민국장 33명에만 photo URL 부여 (괄호 제거 후 맨 앞 한글 이름, encodeURIComponent)
  - `collected_at` 기록
  - 엑셀 916명 ↔ API 결과 이름 대조 보고
- **2단계** — `index.html` 단일 파일 (data.json 을 HTML 안에 직접 삽입, fetch 사용 금지)
- **3단계** — 자체 검수 6항목
- **4단계** — 교사용 인수인계 문서

## 대한민국장 33명 (사진 파일명 후보)
강우규, 김구, 김규식, 김좌진, 김창숙, 민영환, 서재필, 손병희, 신익희, 쑨원,
쑹메이링, 안중근, 안창호, 여운형, 오동진, 유관순, 윤봉길, 이강년, 이승만, 이승훈,
이시영, 이준, 임병직, 장제스, 조만식, 조병세, 조소앙, 천궈푸, 천치메이, 최익현,
한용운, 허위, 홍범도
