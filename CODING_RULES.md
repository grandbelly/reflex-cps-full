# Ksys App Coding Rules (PRD-first, Soft Gate)

이 문서는 "화면에서 정상 동작하는 기능만" 역공학 → PRD 보완 → 테스트 → 구현 순서를 강제하기 위한 코딩 규칙이다. 룰 위반은 빌드/머지를 **막지 않고(Soft Gate)**, `audit/rules_violations.md`에 기록만 남긴다.

## 0) 원칙
- PRD 먼저: 기능/변경은 반드시 `ksys_app/PRD.md`에 정의 후 진행한다.
- 테스트 우선: 단위/시나리오 테스트(시험 성적서)를 먼저 작성하고, 그 후 구현한다.
- 역공학 소스: 현재 정상 동작 화면과 DB(Views)에서만 사실을 수집한다. 추측 금지.
- 최소 변경: 기능 단위 외 파일 구조/네이밍 변경 금지.

## 1) 데이터/DB 룰
- Timescale **View/Continuous Aggregate**만 읽기. 원본 hypertable 직접 조회 금지.
- 모든 SQL은 **파라미터 바인딩**. 시간 범위/리밋/타임아웃 필수.
- 모든 타임스탬프는 UTC → UI 변환(Asia/Seoul)에서 처리.

## 2) 상태/계산 룰
- 계산(게이지, 증감, 상태)은 **State**에서 숫자 확정 → UI는 표현만.
- `gauge_pct = clamp01((last - min_val)/(max_val - min_val))*100` (QC 없으면 윈도우 min..max)
- `status_level: 0 정상, 1 경고, 2 치명` (warn/crit/hard bound)
- `delta_pct = (last - prev_last)/prev_last*100` , `|delta| ≤ 0.05` 중립
- 모든 표시 문자열은 State에서 포맷(`*_s`).

## 3) UI/표현 룰
- 게이지/링 색 = `status_level` 맵핑(0 green, 1 amber, 2 red)
- 증감 아이콘/색 = `delta_pct` 전용(중립은 회색/minus/"unchanged")
- 타이틀 옆 `range_label` 항상 노출

## 4) 파일/구조 룰
- PRD: `ksys_app/PRD.md` 단일 소스. 변경은 PRD PR 승인 후만.
- 테스트: `ksys_app/tests/` 아래에 시험 성적서(`*_sheet.md`)와 유닛테스트(`test_*.py`).
- 불필요 폴더 생성 금지(예: `ksys_app/ksys_app/` 같은 중첩 패키지 생성 금지).

## 5) 툴 사용 룰
- Browser MCP로 라우트/네트워크 페이로드 수집.
- DB MCP로 View 스키마/샘플/플랜 수집.
- 수집 결과는 PRD/시험 성적서에 첨부.

## 6) Soft Gate (차단 없음)
- 커밋/머지 전 자동 점검(선택):
  - PRD 변경 유무 확인(없으면 `audit/rules_violations.md`에 기록)
  - 시험 성적서 케이스 존재 여부
  - 단위 테스트 파일 존재 여부
- 차단하지 않음. 모든 위반은 기록만 남긴다.

## 7) 대화 로그 관리 룰
- 모든 세션은 `docs/chat/YYYY-MM-DD-session.md`에 기록
- 형식: 메타(커밋/범위) + **Q&A 요약** + 핵심 변경 요약 + 후속 작업
- Q&A 요약: 사용자 질문 + AI 답변의 핵심 내용을 주제별로 정리
- 세션 종료 시 반드시 커밋/푸시하여 다른 환경에서 연속성 보장
- 대화 맥락은 PRD/코딩 룰 참조로 연결

## 8) 구현 순서 체크리스트
1. 현재 화면/DB에서 사실 수집(Browser/DB MCP)
2. `PRD.md` 보완(데이터 소스/계약/수용 기준)
3. `tests/*_sheet.md`에 시험 시나리오/예상값 작성
4. 유닛테스트 `test_*.py` 작성(순수 계산/상태 리듀서)
5. 최소 구현 → 테스트 → 화면 확인
6. `audit/rules_violations.md`에 위반 내역 기록(자동/수동)
7. `docs/chat/`에 세션 로그 업데이트 및 커밋/푸시
