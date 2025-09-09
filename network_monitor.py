#!/usr/bin/env python3
"""
네트워크 성능 모니터링 도구
윈도우-라즈베리파이 간 DB 연결 성능 측정
"""

import asyncio
import time
import psycopg
from datetime import datetime
import statistics

class NetworkMonitor:
    def __init__(self, connection_string):
        self.conn_str = connection_string
        self.metrics = []
        
    async def test_latency(self, iterations=10):
        """DB 연결 레이턴시 테스트"""
        latencies = []
        
        for i in range(iterations):
            start = time.perf_counter()
            try:
                async with await psycopg.AsyncConnection.connect(self.conn_str) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("SELECT 1")
                        await cur.fetchone()
                end = time.perf_counter()
                latency = (end - start) * 1000  # ms
                latencies.append(latency)
                print(f"  [{i+1}/{iterations}] Latency: {latency:.2f}ms")
            except Exception as e:
                print(f"  [ERROR] Connection failed: {e}")
                
        if latencies:
            print(f"\n[STATISTICS]")
            print(f"  Average: {statistics.mean(latencies):.2f}ms")
            print(f"  Min: {min(latencies):.2f}ms")
            print(f"  Max: {max(latencies):.2f}ms")
            print(f"  Std Dev: {statistics.stdev(latencies):.2f}ms" if len(latencies) > 1 else "")
            
        return latencies
    
    async def test_throughput(self, query="SELECT * FROM influx_latest LIMIT 1000"):
        """데이터 처리량 테스트"""
        print(f"\n[THROUGHPUT TEST]")
        print(f"  Query: {query}")
        
        start = time.perf_counter()
        rows_fetched = 0
        
        try:
            async with await psycopg.AsyncConnection.connect(self.conn_str) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query)
                    rows = await cur.fetchall()
                    rows_fetched = len(rows)
                    
            end = time.perf_counter()
            duration = end - start
            throughput = rows_fetched / duration if duration > 0 else 0
            
            print(f"  Rows fetched: {rows_fetched}")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Throughput: {throughput:.0f} rows/sec")
            
            return throughput
            
        except Exception as e:
            print(f"  [ERROR] Query failed: {e}")
            return 0
    
    async def monitor_continuous(self, interval=60):
        """지속적인 모니터링"""
        print(f"\n[CONTINUOUS MONITORING - Every {interval}s]")
        
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n--- {timestamp} ---")
            
            # 레이턴시 테스트
            await self.test_latency(5)
            
            # 처리량 테스트
            await self.test_throughput()
            
            # 대기
            await asyncio.sleep(interval)

async def main():
    # 네트워크 환경별 연결 문자열
    connections = {
        "local": "postgresql://postgres:admin@192.168.100.29:5432/EcoAnP?sslmode=disable",
        "remote": "postgresql://postgres:admin@192.168.1.80:5432/EcoAnP?sslmode=disable"
    }
    
    print("[NETWORK PERFORMANCE MONITOR]")
    print("1. Test Local (192.168.100.29)")
    print("2. Test Remote (192.168.1.80)")
    print("3. Compare Both")
    print("4. Continuous Monitoring")
    
    choice = input("\nSelect option: ")
    
    if choice == "1":
        monitor = NetworkMonitor(connections["local"])
        await monitor.test_latency(20)
        await monitor.test_throughput()
    elif choice == "2":
        monitor = NetworkMonitor(connections["remote"])
        await monitor.test_latency(20)
        await monitor.test_throughput()
    elif choice == "3":
        print("\n[COMPARING LOCAL vs REMOTE]")
        
        print("\n--- LOCAL NETWORK ---")
        local_monitor = NetworkMonitor(connections["local"])
        local_latencies = await local_monitor.test_latency(10)
        local_throughput = await local_monitor.test_throughput()
        
        print("\n--- REMOTE NETWORK ---")
        remote_monitor = NetworkMonitor(connections["remote"])
        remote_latencies = await remote_monitor.test_latency(10)
        remote_throughput = await remote_monitor.test_throughput()
        
        # 비교 결과
        print("\n[COMPARISON RESULTS]")
        if local_latencies and remote_latencies:
            local_avg = statistics.mean(local_latencies)
            remote_avg = statistics.mean(remote_latencies)
            improvement = ((remote_avg - local_avg) / remote_avg) * 100 if remote_avg > 0 else 0
            
            print(f"  Local Avg Latency: {local_avg:.2f}ms")
            print(f"  Remote Avg Latency: {remote_avg:.2f}ms")
            print(f"  Improvement: {improvement:.1f}%")
            
        if local_throughput and remote_throughput:
            throughput_improvement = ((local_throughput - remote_throughput) / remote_throughput) * 100 if remote_throughput > 0 else 0
            print(f"  Local Throughput: {local_throughput:.0f} rows/sec")
            print(f"  Remote Throughput: {remote_throughput:.0f} rows/sec")
            print(f"  Improvement: {throughput_improvement:.1f}%")
            
    elif choice == "4":
        env = input("Monitor which? (local/remote): ")
        interval = int(input("Interval in seconds (default 60): ") or "60")
        monitor = NetworkMonitor(connections.get(env, connections["local"]))
        await monitor.monitor_continuous(interval)

if __name__ == "__main__":
    asyncio.run(main())