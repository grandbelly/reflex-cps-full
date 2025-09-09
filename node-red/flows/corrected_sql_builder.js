// =====================================================
// 수정된 SQL 빌드(업서트) 함수
// DataId를 실제 태그명(D100, D101 등)으로 매핑
// =====================================================

// 태그 매핑 테이블 (메타 버킷에서 발견한 정보)
const TAG_MAPPING = {
  "1": "D100",
  "2": "D101", 
  "3": "D102",
  "4": "D200",
  "5": "D201",
  "6": "D202",
  "7": "D300",
  "8": "D301",
  "9": "D302"
};

// SQL 쿼리 배열
const sqlQueries = [];

// InfluxDB 데이터 처리
if (msg.payload && Array.isArray(msg.payload)) {
  for (const item of msg.payload) {
    if (item && typeof item === 'object' && '_value' in item && '_field' in item && '_time' in item) {
      
      // DataId를 실제 태그명으로 변환
      const dataId = item._field;
      const tagName = TAG_MAPPING[dataId] || `Unknown_${dataId}`;
      const timestamp = item._time;
      const value = item._value;
      
      // TimescaleDB UPSERT 쿼리 생성
      const sql = `
        INSERT INTO sensor_data (timestamp, tag_name, value) 
        VALUES ('${timestamp}', '${tagName}', ${value})
        ON CONFLICT (timestamp, tag_name) 
        DO UPDATE SET 
          value = EXCLUDED.value,
          updated_at = CURRENT_TIMESTAMP;
      `.trim();
      
      sqlQueries.push(sql);
      
      // 로그 출력
      node.log(`📊 ${tagName}: ${value} (${timestamp})`);
    } else {
      node.warn('⚠️ Invalid data structure:', item);
    }
  }
}

// 결과 메시지 설정
msg.payload = {
  queries: sqlQueries,
  count: sqlQueries.length,
  mapping_used: TAG_MAPPING
};

// 성공 로그
if (sqlQueries.length > 0) {
  node.log(`✅ ${sqlQueries.length}개 SQL 쿼리 생성 완료`);
} else {
  node.warn('⚠️ 생성된 SQL 쿼리가 없습니다');
}

return msg;

