# RAG Knowledge Base Structure

## 개요
이 폴더는 AI 응답 생성을 위한 지식 베이스를 관리합니다.
모든 지식은 JSON 파일로 관리되며, 6하 원칙(5W1H)에 따라 구조화됩니다.

## 폴더 구조
```
rag_knowledge/
├── sensor_specs/        # 센서 사양 및 기술 정보
├── troubleshooting/     # 문제 해결 가이드
├── maintenance/         # 유지보수 절차
├── operational_patterns/# 운영 패턴 및 정상 동작
├── correlations/        # 센서 간 상관관계
└── domain_knowledge/    # 도메인 특화 지식
```

## 6하 원칙 (5W1H) 구조
모든 지식은 다음 구조를 따릅니다:
- **What** (무엇): 현상, 상태, 데이터
- **Why** (왜): 원인, 이유
- **When** (언제): 시간, 주기, 타이밍
- **Where** (어디): 위치, 영향 범위
- **Who** (누가): 담당자, 책임 주체
- **How** (어떻게): 해결 방법, 절차

## 파일 명명 규칙
- 센서 관련: `{sensor_type}_specs.json`
- 문제 해결: `troubleshooting_{issue_type}.json`
- 유지보수: `maintenance_{task_type}.json`

## 지식 추가 방법
1. 해당 카테고리 폴더에 JSON 파일 생성
2. 6하 원칙 구조 준수
3. 메타데이터 포함 (tags, priority, last_updated 등)