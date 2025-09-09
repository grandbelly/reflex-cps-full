from dagster import asset, AssetExecutionContext
import numpy as np
from datetime import datetime
import json

@asset
def generate_training_data(context: AssetExecutionContext):
    """ML 모델 훈련을 위한 가상 데이터 생성"""
    context.log.info("훈련 데이터 생성 시작...")
    
    # 가상 시계열 데이터 생성 (1년치)
    dates = np.arange('2024-01-01', '2025-01-01', dtype='datetime64[D]')
    np.random.seed(42)  # 재현 가능성을 위한 시드 설정
    
    # 트렌드 + 계절성 + 노이즈
    trend = np.linspace(100, 150, len(dates))
    seasonality = 20 * np.sin(2 * np.pi * np.arange(len(dates)) / 365)
    noise = np.random.normal(0, 5, len(dates))
    
    values = trend + seasonality + noise
    
    training_data = {
        "dates": [str(date) for date in dates],
        "values": values.tolist(),
        "metadata": {
            "data_points": len(dates),
            "start_date": str(dates[0]),
            "end_date": str(dates[-1]),
            "generated_at": datetime.now().isoformat()
        }
    }
    
    context.log.info(f"훈련 데이터 생성 완료: {len(dates)}개 데이터 포인트")
    return training_data

@asset
def train_ml_model(context: AssetExecutionContext, generate_training_data):
    """간단한 ML 모델 훈련 (선형 회귀)"""
    context.log.info("ML 모델 훈련 시작...")
    
    # 간단한 선형 회귀 모델 (실제로는 PyTorch/TensorFlow 사용)
    dates = generate_training_data["dates"]
    values = generate_training_data["values"]
    
    # 날짜를 숫자로 변환 (2024-01-01 = 0, 2024-01-02 = 1, ...)
    x = np.arange(len(dates))
    y = np.array(values)
    
    # 선형 회귀 계산
    n = len(x)
    slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
    intercept = np.mean(y) - slope * np.mean(x)
    
    # 예측값 계산
    predictions = slope * x + intercept
    
    model_info = {
        "model_type": "Linear Regression",
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(1 - np.sum((y - predictions)**2) / np.sum((y - np.mean(y))**2)),
        "training_data_size": len(dates),
        "trained_at": datetime.now().isoformat()
    }
    
    context.log.info(f"ML 모델 훈련 완료: R² = {model_info['r_squared']:.4f}")
    return model_info

@asset
def make_predictions(context: AssetExecutionContext, train_ml_model, generate_training_data):
    """훈련된 모델로 미래 예측"""
    context.log.info("미래 예측 시작...")
    
    slope = train_ml_model["slope"]
    intercept = train_ml_model["intercept"]
    
    # 미래 30일 예측
    future_days = np.arange(len(generate_training_data["dates"]), len(generate_training_data["dates"]) + 30)
    future_predictions = slope * future_days + intercept
    
    # 미래 날짜 생성
    last_date = np.datetime64(generate_training_data["dates"][-1])
    future_dates = [str(last_date + np.timedelta64(i, 'D')) for i in range(1, 31)]
    
    predictions = {
        "future_dates": future_dates,
        "predicted_values": future_predictions.tolist(),
        "model_info": train_ml_model,
        "prediction_metadata": {
            "prediction_horizon": 30,
            "predicted_at": datetime.now().isoformat(),
            "confidence_interval": "95%"
        }
    }
    
    context.log.info(f"미래 예측 완료: 30일 예측값 생성")
    return predictions

@asset
def save_to_database(context: AssetExecutionContext, make_predictions):
    """예측 결과를 데이터베이스에 저장 (시뮬레이션)"""
    context.log.info("데이터베이스 저장 시작...")
    
    # 실제로는 TimescaleDB에 저장
    # 여기서는 시뮬레이션
    db_record = {
        "table_name": "ml_predictions",
        "inserted_records": len(make_predictions["future_dates"]),
        "timestamp": datetime.now().isoformat(),
        "data_sample": {
            "first_prediction": {
                "date": make_predictions["future_dates"][0],
                "value": make_predictions["predicted_values"][0]
            },
            "last_prediction": {
                "date": make_predictions["future_dates"][-1],
                "value": make_predictions["predicted_values"][-1]
            }
        }
    }
    
    context.log.info(f"데이터베이스 저장 완료: {db_record['inserted_records']}개 레코드")
    return db_record
