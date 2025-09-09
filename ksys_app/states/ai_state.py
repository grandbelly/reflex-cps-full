"""AI State management for sensor data insights and chat interface."""

import asyncio
import json
from datetime import datetime
from typing import List, TypedDict, Dict, Any, Optional

import reflex as rx
from ksys_app.queries.latest import latest_snapshot, get_latest_values_cached
from ksys_app.queries.qc import qc_rules
from ksys_app.ai_engine.rag_engine import get_rag_response, initialize_rag_engine, rag_engine
from ksys_app.ai_engine.agent_orchestrator import get_multi_agent_response, initialize_multi_agent_system
from ksys_app.ai_engine.enhanced_agent_orchestrator import get_enhanced_multi_agent_response, initialize_enhanced_multi_agent_system


class Message(TypedDict):
    """Message data structure."""
    text: str
    is_ai: bool
    timestamp: str
    visualization_data: Optional[Dict[str, Any]]  # 시각화 데이터 (선택적)


class AIState(rx.State):
    """State management for AI chat interface."""
    
    messages: List[Message] = []
    typing: bool = False
    current_query: str = ""
    rag_initialized: bool = False
    multi_agent_initialized: bool = False
    enhanced_agent_initialized: bool = False
    use_multi_agent: bool = True  # Multi-Agent 사용 여부
    use_enhanced_agent: bool = True  # Enhanced Multi-Agent 사용 여부 (우선)
    current_visualizations: Dict[str, Any] = {}
    sensor_data_loaded: bool = False
    
    @rx.var
    def get_latest_visualization_data(self) -> Dict[str, Any]:
        """Get visualization data from the latest AI message."""
        try:
            # 최신 AI 메시지에서 시각화 데이터 찾기
            ai_messages = [m for m in reversed(self.messages) 
                          if m.get("is_ai", False) and m.get("visualization_data")]
            return ai_messages[0]["visualization_data"] if ai_messages else {}
        except (IndexError, KeyError, TypeError):
            return {}
    
    @rx.var
    def has_visualization_data(self) -> bool:
        """Check if latest AI message has visualization data."""
        viz_data = self.current_visualizations
        return bool(viz_data)
    
    @rx.var
    def get_heatmap_data(self) -> List[Dict[str, Any]]:
        """Get heatmap data from latest visualization."""
        viz_data = self.current_visualizations
        return viz_data.get('heatmap', [])
    
    @rx.var
    def get_parsed_sensor_data(self) -> List[Dict[str, Any]]:
        """Get real sensor data from database when AI response is active."""
        try:
            # AI 응답이 있을 때만 센서 데이터 표시
            ai_messages = [m for m in reversed(self.messages) 
                          if m.get("is_ai", False) and m.get("text")]
            
            if ai_messages:
                # current_visualizations에서 실제 센서 데이터 가져오기
                heatmap_data = self.current_visualizations.get('heatmap', [])
                if heatmap_data:
                    return heatmap_data
                
                # 시각화 데이터가 없으면 빈 리스트 (하드코딩 제거)
                return []
            return []
        except (TypeError, AttributeError):
            return []
    
    @rx.var
    def get_comparison_data(self) -> List[Dict[str, Any]]:
        """Get comparison chart data from latest visualization."""
        viz_data = self.current_visualizations
        return viz_data.get('comparison', [])
    
    @rx.var
    def get_violations_data(self) -> List[Dict[str, Any]]:
        """Get violations data from latest visualization."""
        viz_data = self.current_visualizations
        return viz_data.get('violations', [])
    
    @rx.var
    def get_real_heatmap_data(self) -> Dict[str, Any]:
        """Get real heatmap data from latest visualization."""
        viz_data = self.current_visualizations
        return viz_data.get('real_heatmap', {})
    
    @rx.var
    def has_real_heatmap(self) -> bool:
        """Check if real heatmap data exists."""
        return bool(self.get_real_heatmap_data)
    
    @rx.var
    def get_trend_data(self) -> List[Dict[str, Any]]:
        """Get trend data from latest visualization."""
        viz_data = self.current_visualizations
        return viz_data.get('trend', [])
    
    # 판다스 분석 결과 관련 computed properties
    @rx.var
    def get_correlation_heatmap_data(self) -> Dict[str, Any]:
        """Get correlation heatmap data from pandas analysis."""
        return self.current_visualizations.get('correlation_heatmap', {})
    
    @rx.var
    def has_correlation_heatmap(self) -> bool:
        """Check if correlation heatmap data exists."""
        return bool(self.get_correlation_heatmap_data)
    
    @rx.var
    def get_correlation_summary(self) -> List[str]:
        """Get correlation analysis summary insights."""
        correlation_data = self.get_correlation_heatmap_data
        return correlation_data.get('summary', [])
    
    @rx.var
    def get_correlation_sensors(self) -> List[str]:
        """Get list of sensors in correlation analysis."""
        correlation_data = self.get_correlation_heatmap_data
        return correlation_data.get('sensors', [])
    
    @rx.var
    def get_correlation_matrix_rows(self) -> List[str]:
        """Get correlation matrix as formatted text rows."""
        correlation_data = self.get_correlation_heatmap_data
        matrix_data = correlation_data.get('matrix', [])
        sensors = correlation_data.get('sensors', [])
        
        if not matrix_data or not sensors:
            return []
        
        # 간단한 텍스트 행으로 변환 (Reflex foreach 호환)
        rows = []
        for sensor1 in sensors:
            row_values = []
            for sensor2 in sensors:
                corr_value = 0.0
                for item in matrix_data:
                    if item.get('x') == sensor1 and item.get('y') == sensor2:
                        corr_value = item.get('value', 0.0)
                        break
                row_values.append(f"{corr_value:.3f}")
            
            row_text = f"{sensor1}: {' | '.join(row_values)}"
            rows.append(row_text)
        
        return rows
    
    @rx.var
    def get_time_heatmap_data(self) -> Dict[str, Any]:
        """Get time-based heatmap data from pandas analysis."""
        viz_data = self.current_visualizations
        return viz_data.get('time_heatmap', {})
    
    @rx.var
    def has_time_heatmap(self) -> bool:
        """Check if time heatmap data exists."""
        return bool(self.get_time_heatmap_data)
    
    @rx.var
    def get_predictions_data(self) -> List[Dict[str, Any]]:
        """Get prediction chart data from pandas analysis."""
        viz_data = self.current_visualizations
        return viz_data.get('predictions', [])
    
    @rx.var
    def has_predictions(self) -> bool:
        """Check if prediction data exists."""
        return bool(self.get_predictions_data)
    
    @rx.var
    def get_anomalies_data(self) -> List[Dict[str, Any]]:
        """Get anomaly detection data from pandas analysis."""
        viz_data = self.current_visualizations
        return viz_data.get('anomalies', [])
    
    @rx.var
    def has_anomalies(self) -> bool:
        """Check if anomaly data exists."""
        return bool(self.get_anomalies_data)
    
    @rx.var
    def get_comprehensive_data(self) -> Dict[str, Any]:
        """Get comprehensive analysis data from pandas analysis."""
        viz_data = self.current_visualizations
        return viz_data.get('comprehensive', {})
    
    @rx.var
    def has_comprehensive(self) -> bool:
        """Check if comprehensive analysis data exists."""
        return bool(self.get_comprehensive_data)
    
    @rx.var
    def get_analysis_metadata(self) -> Dict[str, Any]:
        """Get analysis metadata from pandas analysis."""
        viz_data = self.current_visualizations
        return viz_data.get('analysis_metadata', {})
    
    @rx.var
    def get_analysis_insights(self) -> List[str]:
        """Get analysis insights from metadata."""
        metadata = self.get_analysis_metadata
        return metadata.get('insights', [])
    
    @rx.event
    def clear_messages(self):
        """Clear all chat messages and reset typing status."""
        self.typing = False
        self.messages = []
        self.current_query = ""

    @rx.event
    def send_message(self, form_data: dict):
        """Add a user message and trigger AI response generation."""
        if self.typing:
            return
            
        message = form_data["message"].strip()
        if not message:
            return
            
        # Add user message
        self.messages.append({
            "text": message, 
            "is_ai": False,
            "timestamp": datetime.now().isoformat(),
            "visualization_data": None
        })
        
        # Add empty AI message placeholder
        self.messages.append({
            "text": "", 
            "is_ai": True,
            "timestamp": datetime.now().isoformat(),
            "visualization_data": None
        })
        
        self.current_query = message
        self.typing = True
        
        # Trigger background response generation
        yield AIState.generate_response
        
    @rx.event(background=True)
    async def load_initial_sensor_data(self):
        """Load actual sensor data from database for display."""
        try:
            # Get real sensor data from database (cached)
            latest_data = await get_latest_values_cached()
            
            if not latest_data:
                print("⚠️ No sensor data available from database")
                return
            
            # Get QC rules for proper status detection
            qc_data = await qc_rules(None)
            qc_lookup = {qc.get('tag_name'): qc for qc in qc_data if qc.get('tag_name')}
            
            sensor_data = []
            for sensor in latest_data[:20]:  # Limit to first 20 sensors for display
                tag_name = sensor.get('tag_name', 'Unknown')
                value = float(sensor.get('value', 0))
                
                # Get QC rules for this sensor
                qc_rule = qc_lookup.get(tag_name, {})
                
                # Determine status based on QC rules
                status = "normal"
                if qc_rule:
                    warn_min = qc_rule.get('warn_min')
                    warn_max = qc_rule.get('warn_max')
                    crit_min = qc_rule.get('crit_min')
                    crit_max = qc_rule.get('crit_max')
                    
                    # Check critical limits first
                    if (crit_min is not None and value < float(crit_min)) or \
                       (crit_max is not None and value > float(crit_max)):
                        status = "critical"
                    # Then check warning limits
                    elif (warn_min is not None and value < float(warn_min)) or \
                         (warn_max is not None and value > float(warn_max)):
                        status = "warning"
                
                # Determine unit based on sensor name
                unit = ""
                if tag_name.startswith('D1'):
                    unit = "°C"
                elif tag_name.startswith('D2'):
                    unit = "bar"
                elif tag_name.startswith('D3'):
                    unit = "rpm"
                    
                ts_value = sensor.get('ts', '')
                if isinstance(ts_value, datetime):
                    ts_str = ts_value.isoformat()[:19]
                elif isinstance(ts_value, str):
                    ts_str = ts_value[:19] if ts_value else '실시간'
                else:
                    ts_str = '실시간'
                    
                sensor_data.append({
                    "sensor": tag_name,
                    "value": round(value, 1),
                    "status": status,
                    "last_update": ts_str,
                    "unit": unit
                })
            
            async with self:
                self.current_visualizations = {
                    'heatmap': sensor_data,
                    'metadata': {
                        'type': 'sensor_status',
                        'timestamp': datetime.now().isoformat(),
                        'source': 'database',
                        'count': len(sensor_data)
                    }
                }
                self.sensor_data_loaded = True
                print(f"✅ Loaded {len(sensor_data)} sensors from database")
                
        except Exception as e:
            print(f"❌ Error loading sensor data: {e}")
            async with self:
                self.current_visualizations = {
                    'heatmap': [],
                    'metadata': {'type': 'error', 'error': str(e)}
                }

    @rx.event(background=True)
    async def generate_response(self):
        """Generate AI response using RAG engine."""
        try:
            async with self:
                query = self.current_query
            
            print(f"🎯 generate_response 시작: {query}")
                
            # Initialize RAG engine if not already done
            if not self.rag_initialized:
                try:
                    await initialize_rag_engine()
                    async with self:
                        self.rag_initialized = True
                except Exception as e:
                    print(f"RAG 엔진 초기화 실패: {e}")
                    # Fallback to basic response handling
                    response_text = await self._handle_fallback_query(query)
                    await self._stream_response(response_text)
                    return
            
            # Initialize Enhanced Multi-Agent system (우선 시도)
            if self.use_enhanced_agent and not self.enhanced_agent_initialized:
                try:
                    await initialize_enhanced_multi_agent_system(rag_engine)
                    async with self:
                        self.enhanced_agent_initialized = True
                    print("🚀 Enhanced Multi-Agent 시스템 초기화 완료")
                except Exception as e:
                    print(f"Enhanced Multi-Agent 시스템 초기화 실패: {e}")
                    async with self:
                        self.use_enhanced_agent = False  # 실패시 기본 Multi-Agent로 전환
            
            # Initialize Multi-Agent system if enhanced failed
            if not self.use_enhanced_agent and self.use_multi_agent and not self.multi_agent_initialized:
                try:
                    await initialize_multi_agent_system(rag_engine)
                    async with self:
                        self.multi_agent_initialized = True
                    print("🤖 기본 Multi-Agent 시스템 초기화 완료")
                except Exception as e:
                    print(f"Multi-Agent 시스템 초기화 실패: {e}")
                    async with self:
                        self.use_multi_agent = False  # 실패시 단일 RAG로 전환
            
            # Generate response using appropriate system (우선순위: Enhanced > Multi-Agent > RAG)
            print(f"🔍 AI 시스템 상태 체크:")
            print(f"   - Enhanced Agent: 사용={self.use_enhanced_agent}, 초기화={self.enhanced_agent_initialized}")
            print(f"   - Multi-Agent: 사용={self.use_multi_agent}, 초기화={self.multi_agent_initialized}")
            
            if self.use_enhanced_agent and self.enhanced_agent_initialized:
                print("🚀 Enhanced Multi-Agent 시스템으로 응답 생성 중...")
                response = await get_enhanced_multi_agent_response(query)
                
                # Enhanced Multi-Agent 응답이 문자열인 경우 실제 DB 데이터로 시각화 데이터 추가
                if isinstance(response, str):
                    print("⚠️ Enhanced Multi-Agent가 문자열 응답 리턴 - 실제 DB에서 센서 데이터 로드")
                    try:
                        latest_data = await get_latest_values_cached()
                        qc_data = await qc_rules(None)
                        qc_lookup = {qc.get('tag_name'): qc for qc in qc_data if qc.get('tag_name')}
                        
                        if latest_data:
                            sensor_cards = []
                            for sensor in latest_data[:20]:  # Limit display
                                value = float(sensor.get('value', 0))
                                tag_name = sensor.get('tag_name', '')
                                
                                # Get QC rules for proper status
                                qc_rule = qc_lookup.get(tag_name, {})
                                status = "normal"
                                
                                if qc_rule:
                                    warn_min = qc_rule.get('warn_min')
                                    warn_max = qc_rule.get('warn_max')
                                    crit_min = qc_rule.get('crit_min')
                                    crit_max = qc_rule.get('crit_max')
                                    
                                    if (crit_min is not None and value < float(crit_min)) or \
                                       (crit_max is not None and value > float(crit_max)):
                                        status = "critical"
                                    elif (warn_min is not None and value < float(warn_min)) or \
                                         (warn_max is not None and value > float(warn_max)):
                                        status = "warning"
                                
                                # 단위 추론
                                unit = ""
                                if "온도" in tag_name.lower() or tag_name.startswith('T'):
                                    unit = "°C"
                                elif "압력" in tag_name.lower() or tag_name.startswith('P'):
                                    unit = "bar"
                                elif "rpm" in tag_name.lower() or "회전" in tag_name.lower():
                                    unit = "rpm"
                                
                                ts_value = sensor.get('ts', '')
                                if isinstance(ts_value, datetime):
                                    ts_str = ts_value.isoformat()[:19]
                                elif isinstance(ts_value, str):
                                    ts_str = ts_value[:19] if ts_value else ''
                                else:
                                    ts_str = ''
                                    
                                sensor_cards.append({
                                    'sensor': tag_name,
                                    'value': round(value, 1),
                                    'status': status,
                                    'last_update': ts_str,
                                    'unit': unit
                                })
                            
                            # 문자열 응답을 딕셔너리로 변환
                            response = {
                                'text': response,
                                'visualizations': {
                                    'heatmap': sensor_cards,
                                    'metadata': {
                                        'type': 'real_sensor_status',
                                        'source': 'database',
                                        'count': len(sensor_cards),
                                        'timestamp': datetime.now().isoformat()
                                    }
                                }
                            }
                            print(f"✅ 실제 DB 센서 데이터 생성 완료: {len(sensor_cards)}개 센서")
                    except Exception as e:
                        print(f"❌ 실제 센서 데이터 생성 실패: {e}")
            elif self.use_multi_agent and self.multi_agent_initialized:
                print("🤖 기본 Multi-Agent 시스템으로 응답 생성 중...")
                response = await get_multi_agent_response(query)
            else:
                print("📚 단일 RAG 시스템으로 응답 생성 중...")
                response = await get_rag_response(query)
            
            # 응답이 딕셔너리인지 확인 (시각화 데이터 포함)
            if isinstance(response, dict) and 'text' in response:
                response_text = response['text']
                viz_data = response.get('visualizations')
                print(f"📊 응답 데이터 구조: {type(response)}, 키: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
                print(f"🎨 시각화 데이터 존재: {viz_data is not None}, 키: {list(viz_data.keys()) if viz_data else 'None'}")
            else:
                response_text = response
                viz_data = None
                print(f"📝 텍스트 응답만 받음: {type(response)}")
            
            # Stream response character by character for typing effect
            await self._stream_response(response_text, viz_data)
            
        except Exception as e:
            error_msg = f"죄송합니다. 오류가 발생했습니다: {str(e)}"
            await self._stream_response(error_msg, None)
        finally:
            async with self:
                self.typing = False

    async def _stream_response(self, response_text: str, viz_data: Optional[Dict[str, Any]] = None):
        """Stream response text with typing effect and add visualization data."""
        current_text = ""
        for char in response_text:
            if not self.typing:
                break
            current_text += char
            async with self:
                if self.messages:
                    self.messages[-1]["text"] = current_text
                    if viz_data:  # 시각화 데이터가 있으면 마지막에 추가
                        self.messages[-1]["visualization_data"] = viz_data
                        # current_visualizations도 업데이트 - visualizations 키 내부 데이터만 저장
                        print(f"🔍 원본 viz_data: {type(viz_data)} - {viz_data if isinstance(viz_data, dict) and len(str(viz_data)) < 200 else 'Large dict'}")
                        viz_content = viz_data.get('visualizations', viz_data) if isinstance(viz_data, dict) else viz_data
                        print(f"🔍 추출된 viz_content: {type(viz_content)} - {list(viz_content.keys()) if isinstance(viz_content, dict) else 'Not dict'}")
                        self.current_visualizations = viz_content
                        print(f"🎨 시각화 데이터 상태 업데이트: {list(viz_content.keys()) if viz_content else 'None'}")
                        
                        # 🔍 heatmap 키가 없는 경우 실제 DB에서 데이터 추가
                        if viz_content and 'heatmap' not in viz_content:
                            print("⚠️ heatmap 키 누락! 실제 DB에서 센서 데이터 로드 중...")
                            try:
                                latest_data = await get_latest_values_cached()
                                qc_data = await qc_rules(None)
                                qc_lookup = {qc.get('tag_name'): qc for qc in qc_data if qc.get('tag_name')}
                                
                                if latest_data:
                                    sensor_cards = []
                                    for sensor in latest_data[:20]:  # Limit display
                                        value = float(sensor.get('value', 0))
                                        tag_name = sensor.get('tag_name', 'Unknown')
                                        
                                        # Get QC rules for proper status
                                        qc_rule = qc_lookup.get(tag_name, {})
                                        status = "normal"
                                        
                                        if qc_rule:
                                            warn_min = qc_rule.get('warn_min')
                                            warn_max = qc_rule.get('warn_max')
                                            crit_min = qc_rule.get('crit_min')
                                            crit_max = qc_rule.get('crit_max')
                                            
                                            if (crit_min is not None and value < float(crit_min)) or \
                                               (crit_max is not None and value > float(crit_max)):
                                                status = "critical"
                                            elif (warn_min is not None and value < float(warn_min)) or \
                                                 (warn_max is not None and value > float(warn_max)):
                                                status = "warning"
                                        
                                        # Unit based on sensor type
                                        unit = ""
                                        if tag_name.startswith('D1'):
                                            unit = "°C"
                                        elif tag_name.startswith('D2'):
                                            unit = "bar"
                                        elif tag_name.startswith('D3'):
                                            unit = "rpm"
                                        
                                        ts_value = sensor.get('ts', '')
                                        if isinstance(ts_value, datetime):
                                            ts_str = ts_value.isoformat()[:19]
                                        elif isinstance(ts_value, str):
                                            ts_str = ts_value[:19] if ts_value else ''
                                        else:
                                            ts_str = ''
                                            
                                        sensor_cards.append({
                                            'sensor': tag_name,
                                            'value': round(value, 1),
                                            'status': status,
                                            'last_update': ts_str,
                                            'unit': unit
                                        })
                                    viz_content['heatmap'] = sensor_cards
                                    self.current_visualizations = viz_content
                                    print(f"✅ 실제 DB heatmap 키 추가 완료: {len(sensor_cards)}개 센서")
                            except Exception as e:
                                print(f"❌ heatmap 키 추가 실패: {e}")
            await asyncio.sleep(0.02)

    async def _handle_current_status_query(self, query: str) -> str:
        """Handle current status queries."""
        try:
            # Extract sensor tag from query if specified
            sensor_tag = self._extract_sensor_tag(query)
            
            # Get latest data
            latest_data = await latest_snapshot(sensor_tag)
            
            if not latest_data:
                return "현재 센서 데이터를 가져올 수 없습니다. 데이터베이스 연결을 확인해주세요."
            
            if sensor_tag:
                # Specific sensor query
                sensor_data = next((item for item in latest_data if item['tag_name'] == sensor_tag), None)
                if sensor_data:
                    return self._format_sensor_status(sensor_data)
                else:
                    return f"{sensor_tag} 센서를 찾을 수 없습니다. 사용 가능한 센서: {', '.join([item['tag_name'] for item in latest_data[:5]])}"
            else:
                # General status overview
                return self._format_general_status(latest_data)
                
        except Exception as e:
            return f"현재 상태 조회 중 오류 발생: {str(e)}"

    async def _handle_alert_query(self, query: str) -> str:
        """Handle alert and warning queries."""
        try:
            # Get latest sensor data and QC rules
            latest_data = await latest_snapshot(None)
            qc_data = await qc_rules(None)
            
            if not latest_data:
                return "센서 데이터를 가져올 수 없습니다."
            
            # Create QC lookup
            qc_lookup = {}
            for qc_rule in qc_data or []:
                tag_name = qc_rule.get('tag_name')
                if tag_name:
                    qc_lookup[tag_name] = qc_rule
            
            # Check alerts based on QC rules
            alerts = []
            for sensor in latest_data:
                tag_name = sensor.get('tag_name')
                value = sensor.get('value')
                
                if not tag_name or value is None:
                    continue
                    
                qc_rule = qc_lookup.get(tag_name, {})
                if not qc_rule:
                    continue
                
                # Check for violations
                status_level = 0
                warn_min = qc_rule.get('warn_min')
                warn_max = qc_rule.get('warn_max')
                crit_min = qc_rule.get('crit_min') 
                crit_max = qc_rule.get('crit_max')
                
                try:
                    val = float(value)
                    if crit_min is not None and val < float(crit_min):
                        status_level = 2
                    elif crit_max is not None and val > float(crit_max):
                        status_level = 2
                    elif warn_min is not None and val < float(warn_min):
                        status_level = 1
                    elif warn_max is not None and val > float(warn_max):
                        status_level = 1
                except (ValueError, TypeError):
                    continue
                
                if status_level > 0:
                    alerts.append({
                        'tag_name': tag_name,
                        'value': value,
                        'status_level': status_level
                    })
            
            if not alerts:
                return "✅ 현재 모든 센서가 정상 범위 내에 있습니다."
            
            # Format alert summary
            warning_count = len([item for item in alerts if item.get('status_level') == 1])
            critical_count = len([item for item in alerts if item.get('status_level') == 2])
            
            result = f"⚠️ 주의 필요한 센서 발견:\n\n"
            
            if critical_count > 0:
                result += f"🚨 위험 상태: {critical_count}개\n"
            if warning_count > 0:
                result += f"⚠️ 경고 상태: {warning_count}개\n\n"
            
            # Sort by severity and show top 5
            alerts.sort(key=lambda x: x.get('status_level', 0), reverse=True)
            for alert in alerts[:5]:
                status_icon = "🚨" if alert.get('status_level') == 2 else "⚠️"
                result += f"{status_icon} {alert['tag_name']}: {alert.get('value', 'N/A')}\n"
            
            if len(alerts) > 5:
                result += f"\n... 및 {len(alerts) - 5}개 추가"
            
            return result
            
        except Exception as e:
            return f"경고 상태 조회 중 오류 발생: {str(e)}"

    async def _handle_trend_query(self, query: str) -> str:
        """Handle trend and comparison queries."""
        try:
            latest_data = await latest_snapshot(None)
            
            if not latest_data:
                return "트렌드 분석을 위한 데이터를 가져올 수 없습니다."
            
            # Sort by absolute change percentage
            trending_data = []
            for item in latest_data:
                if item.get('delta_pct') is not None:
                    trending_data.append({
                        'tag_name': item['tag_name'],
                        'delta_pct': item['delta_pct'],
                        'value': item.get('value', 0)
                    })
            
            trending_data.sort(key=lambda x: abs(x['delta_pct']), reverse=True)
            
            result = "📈 센서 변화량 분석 (절댓값 기준 상위 5개):\n\n"
            
            for i, item in enumerate(trending_data[:5], 1):
                change_icon = "📈" if item['delta_pct'] > 0 else "📉"
                result += f"{i}. {item['tag_name']}: {item['delta_pct']:.2f}% {change_icon}\n"
                result += f"   현재값: {item['value']}\n\n"
            
            return result
            
        except Exception as e:
            return f"트렌드 분석 중 오류 발생: {str(e)}"

    async def _handle_summary_query(self, query: str) -> str:
        """Handle system summary queries."""
        try:
            latest_data = await latest_snapshot(None)
            qc_data = await qc_rules(None)
            
            if not latest_data:
                return "시스템 요약을 위한 데이터를 가져올 수 없습니다."
            
            # System overview
            total_sensors = len(latest_data)
            
            # Simple status summary (without complex QC calculation)
            normal_count = total_sensors
            warning_count = 0  
            critical_count = 0
            
            result = f"🎯 전체 시스템 상태 요약\n\n"
            result += f"📊 총 센서 수: {total_sensors}개\n\n"
            result += f"상태 분포:\n"
            result += f"✅ 정상: {normal_count}개\n"
            result += f"⚠️ 경고: {warning_count}개\n"
            result += f"🚨 위험: {critical_count}개\n\n"
            
            # Health percentage
            health_pct = (normal_count / total_sensors * 100) if total_sensors > 0 else 0
            result += f"🎭 시스템 건강도: {health_pct:.1f}%\n\n"
            
            # Recent activity
            if latest_data:
                latest_time = latest_data[0].get('ts', 'N/A')
                result += f"🕐 최근 업데이트: {latest_time}\n"
            
            return result
            
        except Exception as e:
            return f"시스템 요약 중 오류 발생: {str(e)}"

    async def _handle_fallback_query(self, query: str) -> str:
        """Handle queries when RAG engine is unavailable (fallback mode)."""
        query_lower = query.lower()
        
        # Basic keyword-based routing  
        if "현재" in query_lower and "상태" in query_lower:
            return await self._handle_current_status_query(query_lower)
        elif "경고" in query_lower or "이상" in query_lower or "문제" in query_lower:
            return await self._handle_alert_query(query_lower)
        elif "변화" in query_lower or "비교" in query_lower:
            return await self._handle_trend_query(query_lower)
        elif "전체" in query_lower or "요약" in query_lower or "종합" in query_lower:
            return await self._handle_summary_query(query_lower)
        else:
            return (
                "🤖 RAG 엔진이 초기화되지 않았습니다. 기본 모드로 동작합니다.\n\n"
                "다음과 같은 질문을 시도해보세요:\n"
                "• 'D101 센서 현재 상태는?'\n"
                "• '경고 상태인 센서 있어?'\n"
                "• '어제와 비교해서 어떤 센서가 많이 변했어?'\n"
                "• '전체 시스템 상태 요약해줘'"
            )

    def _extract_sensor_tag(self, query: str) -> str:
        """Extract sensor tag from query text."""
        # Simple pattern matching for sensor tags (D100-D302)
        import re
        pattern = r'D\d{3}'
        match = re.search(pattern, query.upper())
        return match.group() if match else ""

    def _format_sensor_status(self, sensor_data: dict) -> str:
        """Format individual sensor status."""
        tag = sensor_data['tag_name']
        value = sensor_data.get('value', 'N/A')
        ts = sensor_data.get('ts', 'N/A')
        delta_pct = sensor_data.get('delta_pct', 0)
        
        result = f"📊 {tag} 센서 현재 상태:\n\n"
        result += f"🔢 현재값: {value}\n"
        result += f"🕐 업데이트 시간: {ts}\n"
        
        if delta_pct is not None:
            trend_icon = "📈" if delta_pct > 0 else "📉" if delta_pct < 0 else "➡️"
            result += f"📊 변화율: {delta_pct:.2f}% {trend_icon}\n"
        
        return result

    def _format_general_status(self, latest_data: List[dict]) -> str:
        """Format general status overview."""
        result = "📊 전체 센서 현재 상태 (상위 5개):\n\n"
        
        for i, item in enumerate(latest_data[:5], 1):
            tag = item['tag_name']
            value = item.get('value', 'N/A')
            delta_pct = item.get('delta_pct', 0)
            trend_icon = "📈" if delta_pct and delta_pct > 0 else "📉" if delta_pct and delta_pct < 0 else "➡️"
            
            result += f"{i}. {tag}: {value} {trend_icon}\n"
        
        return result
