# 📊 판다스 기반 동적 데이터 분석 시스템

## 🎯 시스템 개요

사용자 요청에 따라 구현된 완전한 판다스 기반 동적 데이터 분석 시스템입니다. 자연어 질문을 통해 실시간으로 센서 데이터를 분석하고 시각화합니다.

## ⚡ 핵심 기능

### 1. 키워드 기반 자동 분석
```
💬 "D101과 D102의 상관관계는?" 
   → 🔗 상관관계 분석 (Pearson, Spearman)

💬 "센서 시간대별 패턴을 히트맵으로"
   → 🗺️ 시간 패턴 히트맵 분석

💬 "내일 센서 값 예측해줘"
   → 🔮 머신러닝 예측 (XGBoost, RandomForest)

💬 "이상한 값 있나 확인해줘"
   → 🚨 이상치 탐지 (Isolation Forest)

💬 "전체 시스템 종합 분석"
   → 📊 종합 분석 리포트
```

### 2. 분석 엔진 아키텍처

```
┌─────────────────────────────────────────┐
│        사용자 자연어 질문                 │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│      키워드 감지 & 분석 타입 선택         │
│   ├ 상관: 상관, 관계, 연관, 영향         │
│   ├ 예측: 예측, 미래, 추정, 예상         │  
│   ├ 히트맵: 히트맵, 패턴, 시간대         │
│   ├ 이상: 이상, 비정상, 특이             │
│   └ 종합: 종합, 전체, 완전한             │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│      TimescaleDB 데이터 수집             │
│   ├ influx_hist 테이블 쿼리              │
│   ├ 120,943+ 센서 레코드               │
│   └ pandas DataFrame 변환              │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│         판다스 분석 엔진                 │
│   ├ 상관관계: Pearson, Spearman        │
│   ├ 예측: XGBoost, RandomForest        │
│   ├ 히트맵: 시간/센서별 패턴 분석        │
│   ├ 이상탐지: IsolationForest          │
│   └ 통계: 평균, 표준편차, 백분위수       │
└─────────────────┬───────────────────────┘
                  ▼
┌─────────────────────────────────────────┐
│        Reflex UI 시각화                 │
│   ├ 상관관계 히트맵                      │
│   ├ 예측 차트 (신뢰구간 포함)           │
│   ├ 이상치 탐지 결과                     │
│   ├ 시간 패턴 차트                       │
│   └ 종합 분석 대시보드                   │
└─────────────────────────────────────────┘
```

## 🔧 기술 스택

### 데이터 분석
- **pandas**: DataFrame 기반 데이터 처리
- **numpy**: 수치 연산
- **scipy**: 통계 분석
- **statsmodels**: 시계열 분석

### 머신러닝
- **xgboost**: 그래디언트 부스팅
- **lightgbm**: 경량화 부스팅
- **scikit-learn**: 일반 ML 알고리즘
- **isolation forest**: 이상치 탐지

### 시각화
- **matplotlib**: 기본 차트
- **seaborn**: 통계 시각화
- **Reflex recharts**: 웹 인터랙티브 차트

### 데이터베이스
- **TimescaleDB**: 시계열 데이터
- **psycopg**: PostgreSQL 연결

## 📊 분석 타입별 상세

### 1. 상관관계 분석
```python
# 피어슨 상관계수 (선형 관계)
pearson_corr = sensor_data.corr(method='pearson')

# 스피어만 상관계수 (순위 기반)
spearman_corr = sensor_data.corr(method='spearman')

# 결과: -1 ~ 1 범위
#  1.0: 완전한 양의 상관관계
#  0.0: 무상관
# -1.0: 완전한 음의 상관관계
```

### 2. 예측 분석
```python
# 앙상블 모델 사용
models = [
    RandomForestRegressor(n_estimators=100),
    XGBRegressor(n_estimators=100),
    LinearRegression()
]

# 시계열 특성 추가
features = ['hour', 'day_of_week', 'is_weekend', 'rolling_mean']

# 신뢰구간 계산
confidence_upper = prediction * 1.1
confidence_lower = prediction * 0.9
```

### 3. 히트맵 분석
```python
# 시간대별 패턴
hourly_pattern = data.groupby(data.timestamp.dt.hour)['value'].agg([
    'mean', 'std', 'count'
])

# 일자별 패턴  
daily_pattern = data.groupby(data.timestamp.dt.day)['value'].agg([
    'mean', 'std', 'count'
])

# 센서별 상관관계 히트맵
correlation_matrix = sensor_data.corr()
```

### 4. 이상치 탐지
```python
# Isolation Forest
isolation_forest = IsolationForest(contamination=0.1)
anomaly_scores = isolation_forest.fit_predict(sensor_data)

# 통계적 방법 (Z-score)
z_scores = np.abs(stats.zscore(sensor_data))
statistical_anomalies = z_scores > 3

# 결합 결과
final_anomalies = anomaly_scores | statistical_anomalies
```

## 🎨 UI 컴포넌트

### 1. 상관관계 히트맵
- 센서 간 상관계수 매트릭스
- 색상 코딩으로 강도 표시
- 인사이트 요약 제공

### 2. 예측 차트
- 시계열 라인 차트
- 예측값 + 신뢰구간
- 모델 정확도 표시

### 3. 이상치 표시
- 이상치 목록
- 심각도별 색상 구분
- 발생 시점 및 수치 표시

### 4. 종합 분석
- 신뢰도 점수
- 데이터 품질 점수
- 핵심 인사이트 요약

## 🚀 사용 방법

### 1. Docker 컨테이너 실행
```bash
docker-compose up --build -d
```

### 2. 웹 브라우저 접속
```
http://localhost:13000/ai
```

### 3. 자연어 질문 예시
```
🔍 "D101과 D102 센서 상관관계 분석해줘"
🔍 "센서들의 시간대별 패턴을 히트맵으로"
🔍 "내일 D101 센서 값 예측해줘" 
🔍 "이상치 탐지 결과 알려줘"
🔍 "전체 센서 시스템 종합 분석"
```

## 📈 성능 최적화

### 데이터 처리
- **배치 처리**: 대용량 데이터 청크 단위 처리
- **인덱싱**: TimescaleDB 시간 기반 인덱스 활용
- **캐싱**: 분석 결과 메모리 캐싱 (TTL 30분)

### 예측 모델
- **특성 선택**: 중요한 특성만 선별하여 성능 향상
- **모델 앙상블**: 여러 모델 결합으로 정확도 향상
- **하이퍼파라미터 튜닝**: 최적 파라미터 자동 선택

### 시각화
- **렌더링 최적화**: 필요한 차트만 동적 렌더링
- **데이터 압축**: 시각화용 데이터 압축 전송
- **반응형 차트**: 사용자 인터랙션 최적화

## 🔍 품질 보증

### 데이터 품질
```python
# 완성도 점수 계산
data_quality_score = (실제_데이터_수 / 예상_데이터_수) * 100

# 누락 데이터 감지
expected_timestamps = 1분_간격_타임스탬프_생성()
missing_data = expected_timestamps - actual_timestamps
```

### 분석 신뢰도
```python
# 신뢰도 점수 계산  
confidence_score = {
    'data_size': min(1.0, len(data) / 1000),      # 데이터 크기
    'model_accuracy': prediction_accuracy,         # 모델 정확도
    'data_completeness': data_quality_score       # 데이터 완성도
}
```

## 🎯 향후 확장 계획

### 1. 고급 분석
- ARIMA 시계열 예측
- 계절성 분해 분석
- 주파수 도메인 분석

### 2. 실시간 스트리밍
- Apache Kafka 연동
- 실시간 이상치 알림
- 스트리밍 ML 파이프라인

### 3. AI 모델 업그레이드
- Transformer 기반 시계열 예측
- 딥러닝 이상치 탐지
- 자동 특성 엔지니어링

---

**구현 완료일**: 2025-09-02  
**개발자**: Claude Code AI Assistant  
**버전**: 1.0.0