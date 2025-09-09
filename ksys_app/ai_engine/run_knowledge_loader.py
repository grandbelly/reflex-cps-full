"""
지식 로더 실행 스크립트
TASK_005: JSON 파일을 DB로 로드
"""

import asyncio
import sys
import os
from pathlib import Path

# Windows asyncio 이벤트 루프 문제 해결
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.append(str(Path(__file__).parent.parent.parent))

from ksys_app.ai_engine.knowledge_loader import KnowledgeLoader, start_file_watcher


async def main():
    """메인 실행 함수"""
    
    print("=" * 60)
    print("JSON 지식 로더 실행")
    print("=" * 60)
    
    # DB 연결 설정
    db_dsn = "postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable"
    
    # 지식 디렉토리 경로
    knowledge_dir = Path(__file__).parent.parent.parent / 'db' / 'rag_knowledge'
    
    print(f"\n[DIR] Knowledge directory: {knowledge_dir}")
    print(f"[DB] Database: 192.168.1.80:5432/EcoAnP")
    
    # 로더 초기화
    loader = KnowledgeLoader(db_dsn, str(knowledge_dir))
    
    # 옵션 선택
    print("\n작업 선택:")
    print("1. 전체 디렉토리 로드")
    print("2. 수정된 파일만 재로드")
    print("3. 파일 감시 모드 (실시간)")
    print("4. 특정 파일 로드")
    
    choice = input("\n선택 (1-4, 기본값 1): ").strip() or "1"
    
    if choice == "1":
        # 전체 로드
        print("\n[LOAD] Loading entire directory...")
        results = await loader.load_directory()
        
        print("\n[RESULT] Load results:")
        for filename, count in results.items():
            print(f"   {filename}: {count} items")
            
    elif choice == "2":
        # 수정된 파일만
        print("\n[RELOAD] Reloading modified files...")
        results = await loader.reload_modified()
        
        if results:
            print("\n[RESULT] Reload results:")
            for filename, count in results.items():
                print(f"   {filename}: {count} items")
        else:
            print("수정된 파일이 없습니다.")
            
    elif choice == "3":
        # 파일 감시 모드
        print("\n[WATCH] Starting file watch mode...")
        print("(종료하려면 Ctrl+C를 누르세요)")
        
        # 초기 로드
        await loader.load_directory()
        
        # 감시자 시작
        observer = start_file_watcher(loader)
        
        try:
            # 무한 대기
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\n감시 모드 종료")
        
        observer.join()
        
    elif choice == "4":
        # 특정 파일
        files = list(knowledge_dir.glob('*.json'))
        
        if not files:
            print("JSON 파일이 없습니다.")
            return
        
        print("\n파일 목록:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file.name}")
        
        file_num = input(f"\n파일 번호 선택 (1-{len(files)}): ").strip()
        
        try:
            selected_file = files[int(file_num) - 1]
            print(f"\n[LOAD] Loading file: {selected_file.name}")
            
            items = await loader.load_json_file(str(selected_file))
            if items:
                saved = await loader.load_to_database(items, selected_file.name)
                print(f"[OK] Load complete: {saved} items")
            else:
                print("로드할 항목이 없습니다.")
                
        except (ValueError, IndexError):
            print("잘못된 선택입니다.")
    
    else:
        print("잘못된 선택입니다.")
    
    print("\n" + "=" * 60)
    print("작업 완료")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n작업이 취소되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()