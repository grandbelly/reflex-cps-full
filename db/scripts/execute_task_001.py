"""
TASK_001: ai_knowledge_base 테이블 생성 실행 스크립트
실행 시간과 결과를 모두 기록
"""

import psycopg
import os
import sys
from datetime import datetime
from pathlib import Path

# 라즈베리파이 DB 연결 문자열 직접 설정
TS_DSN = "postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable"
os.environ['TS_DSN'] = TS_DSN

def log_message(message, level="INFO"):
    """실행 로그 출력"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] [{level}] {message}")
    return timestamp

def execute_sql_file(conn, filepath):
    """SQL 파일 실행"""
    log_message(f"SQL 파일 읽기: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    cur = conn.cursor()
    try:
        log_message("SQL 실행 시작")
        cur.execute(sql_content)
        conn.commit()
        log_message("SQL 실행 완료 및 커밋")
        return True
    except Exception as e:
        conn.rollback()
        log_message(f"SQL 실행 실패: {e}", "ERROR")
        return False
    finally:
        cur.close()

def verify_table_creation(conn):
    """테이블 생성 검증"""
    verifications = []
    cur = conn.cursor()
    
    # 1. 테이블 존재 확인
    log_message("테이블 존재 확인")
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'ai_knowledge_base'
        )
    """)
    table_exists = cur.fetchone()[0]
    verifications.append(("테이블 존재", table_exists))
    log_message(f"  → 테이블 존재: {table_exists}")
    
    if not table_exists:
        return verifications
    
    # 2. 컬럼 수 확인
    log_message("컬럼 정보 확인")
    cur.execute("""
        SELECT COUNT(*) 
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND table_name = 'ai_knowledge_base'
    """)
    column_count = cur.fetchone()[0]
    verifications.append(("컬럼 수", column_count))
    log_message(f"  → 컬럼 수: {column_count}")
    
    # 3. 인덱스 확인
    log_message("인덱스 확인")
    cur.execute("""
        SELECT COUNT(*) 
        FROM pg_indexes
        WHERE tablename = 'ai_knowledge_base'
        AND schemaname = 'public'
    """)
    index_count = cur.fetchone()[0]
    verifications.append(("인덱스 수", index_count))
    log_message(f"  → 인덱스 수: {index_count}")
    
    # 4. 데이터 개수 확인
    log_message("데이터 개수 확인")
    cur.execute("SELECT COUNT(*) FROM ai_knowledge_base")
    data_count = cur.fetchone()[0]
    verifications.append(("데이터 개수", data_count))
    log_message(f"  → 데이터 개수: {data_count}")
    
    # 5. 샘플 데이터 확인
    if data_count > 0:
        log_message("샘플 데이터 확인")
        cur.execute("""
            SELECT id, content_type, priority, array_length(tags, 1)
            FROM ai_knowledge_base
            ORDER BY priority DESC
            LIMIT 3
        """)
        sample_data = cur.fetchall()
        for row in sample_data:
            log_message(f"  → ID: {row[0]}, Type: {row[1]}, Priority: {row[2]}, Tags: {row[3]}")
    
    cur.close()
    return verifications

def main():
    """메인 실행 함수"""
    start_time = log_message("=== TASK_001 실행 시작 ===")
    
    # DB 연결
    try:
        dsn = os.getenv('TS_DSN')
        if not dsn:
            log_message("TS_DSN 환경변수가 설정되지 않음", "ERROR")
            return 1
            
        log_message(f"DB 연결 시도: {dsn.split('@')[1].split('?')[0]}")  # 비밀번호 제외하고 출력
        conn = psycopg.connect(dsn)
        log_message("DB 연결 성공")
    except Exception as e:
        log_message(f"DB 연결 실패: {e}", "ERROR")
        return 1
    
    # SQL 파일 경로
    sql_file = Path(__file__).parent / "001_create_ai_knowledge_base.sql"
    
    if not sql_file.exists():
        log_message(f"SQL 파일을 찾을 수 없음: {sql_file}", "ERROR")
        conn.close()
        return 1
    
    # SQL 실행
    success = execute_sql_file(conn, sql_file)
    
    if success:
        # 검증 실행
        log_message("\n=== 생성 검증 시작 ===")
        verifications = verify_table_creation(conn)
        
        log_message("\n=== 검증 결과 요약 ===")
        all_passed = True
        for check_name, result in verifications:
            status = "✓" if result else "✗"
            log_message(f"{status} {check_name}: {result}")
            if not result:
                all_passed = False
        
        if all_passed:
            log_message("\n모든 검증 통과! TASK_001 완료", "SUCCESS")
        else:
            log_message("\n일부 검증 실패", "WARNING")
    
    conn.close()
    end_time = log_message("=== TASK_001 실행 종료 ===")
    
    # 실행 로그 파일로 저장
    log_file = Path(__file__).parent / f"TASK_001_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_message(f"\n실행 로그 저장: {log_file}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())