from dagster import asset, AssetExecutionContext
from datetime import datetime
import json

@asset
def hello_world(context: AssetExecutionContext):
    """간단한 테스트 Asset"""
    context.log.info("Hello World Asset 실행 시작!")
    
    result = {
        "message": "Hello World from Dagster!",
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }
    
    context.log.info(f"결과: {result}")
    return result

@asset
def test_calculation(context: AssetExecutionContext):
    """간단한 계산 테스트 Asset"""
    context.log.info("계산 테스트 Asset 실행 시작!")
    
    # 간단한 계산
    numbers = list(range(1, 11))
    total = sum(numbers)
    average = total / len(numbers)
    
    result = {
        "numbers": numbers,
        "total": total,
        "average": average,
        "timestamp": datetime.now().isoformat()
    }
    
    context.log.info(f"계산 결과: {result}")
    return result

@asset(deps=[hello_world, test_calculation])
def combined_result(context: AssetExecutionContext):
    """다른 Asset들의 결과를 결합하는 Asset"""
    context.log.info("결합 Asset 실행 시작!")
    
    # 의존성 Asset들의 결과 가져오기
    hello_result = context.get_asset_value("hello_world")
    calc_result = context.get_asset_value("test_calculation")
    
    combined = {
        "hello_world": hello_result,
        "test_calculation": calc_result,
        "combined_at": datetime.now().isoformat(),
        "message": "모든 Asset이 성공적으로 실행되었습니다!"
    }
    
    context.log.info(f"결합 결과: {combined}")
    return combined
