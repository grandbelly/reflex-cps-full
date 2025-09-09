"""
Test communication success rate queries
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Windows에서 asyncio 이벤트 루프 정책 설정
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ksys_app.queries.communication import (
    communication_hourly_stats,
    communication_daily_summary,
    get_available_tags,
    communication_heatmap_data
)


async def test_communication():
    """Test communication monitoring functions"""
    
    print("\n" + "="*60)
    print("Communication Success Rate Test")
    print("="*60)
    
    # 1. Get available tags
    print("\n[1] Available Tags:")
    tags = await get_available_tags()
    print(f"   Found {len(tags)} tags: {tags[:5]}...")
    
    if not tags:
        print("   No tags found!")
        return
    
    test_tag = tags[0]
    print(f"\n   Using tag: {test_tag}")
    
    # 2. Test hourly stats
    print("\n[2] Hourly Statistics (last 24 hours):")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    hourly_stats = await communication_hourly_stats(
        tag_name=test_tag,
        start_date=start_date,
        end_date=end_date
    )
    
    if hourly_stats:
        print(f"   Found {len(hourly_stats)} hourly records")
        for stat in hourly_stats[:3]:  # Show first 3
            print(f"   - {stat['timestamp']}: {stat['record_count']}/{stat['expected_count']} = {stat['success_rate']}% ({stat['status']})")
    else:
        print("   No hourly data found")
    
    # 3. Test daily summary
    print("\n[3] Daily Summary (last 7 days):")
    summary = await communication_daily_summary(
        start_date=end_date - timedelta(days=7),
        end_date=end_date
    )
    
    if summary:
        # Filter for test tag
        tag_summary = [s for s in summary if s['tag_name'] == test_tag]
        print(f"   Found {len(tag_summary)} daily records for {test_tag}")
        for s in tag_summary[:3]:
            print(f"   - {s['date']}: {s['success_rate']}% ({s['status']})")
    else:
        print("   No daily summary found")
    
    # 4. Test heatmap data
    print("\n[4] Heatmap Data (last 3 days):")
    heatmap = await communication_heatmap_data(
        tag_name=test_tag,
        days=3
    )
    
    if heatmap and heatmap['data']:
        print(f"   Tag: {heatmap['tag_name']}")
        print(f"   Period: {heatmap['period']}")
        print(f"   Dates: {heatmap['dates']}")
        
        # Show sample data
        for date in heatmap['dates'][:2]:
            if date in heatmap['data']:
                hourly_data = heatmap['data'][date]
                avg_rate = sum(hourly_data) / len(hourly_data) if hourly_data else 0
                print(f"   - {date}: Avg success rate = {avg_rate:.1f}%")
    else:
        print("   No heatmap data found")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # PostgreSQL 연결 정보 설정
    os.environ['TS_DSN'] = os.getenv(
        'TS_DSN',
        'postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable'
    )
    
    asyncio.run(test_communication())