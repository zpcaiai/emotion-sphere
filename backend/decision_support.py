#!/usr/bin/env python3
"""
决策支持系统 (Decision Support System - DSS)
帮助用户做出符合内心智慧的决策
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import hashlib

# Database imports
from contextlib import contextmanager

# FastAPI imports
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sfds", tags=["decision_support"])

# ==================== ENUMS ====================

# ==================== 现代生活决策类别（21类，覆盖人生主要领域）====================
class DecisionCategory(str, Enum):
    # 职业与发展
    CAREER = "career"                    # 职业/工作
    EDUCATION = "education"              # 教育/学习
    CALLING = "calling"                  # 人生目标/使命
    
    # 人际关系
    RELATIONSHIP = "relationship"        # 人际关系
    FAMILY = "family"                    # 家庭/亲子
    COMMUNITY = "community"              # 社群/圈子
    
    # 资源管理
    FINANCIAL = "financial"              # 财务/金钱
    HOUSING = "housing"                  # 居住/房产
    POSSESSIONS = "possessions"          # 物品/消费
    
    # 身心健康
    HEALTH = "health"                    # 健康/身体
    MENTAL = "mental"                    # 心理/情绪
    
    # 内在成长与道德
    TEMPTATION = "temptation"            # 诱惑/考验
    SPIRITUAL = "spiritual"              # 心灵成长/修养
    MINISTRY = "ministry"                # 服务/志愿
    
    # 时间与生活方式
    TIME = "time"                        # 时间/节奏
    LIFESTYLE = "lifestyle"              # 生活方式
    BOUNDARY = "boundary"                # 边界/拒绝
    
    # 危机与转变
    CRISIS = "crisis"                    # 危机/急难
    TRANSITION = "transition"            # 转变/过渡
    LOSS = "loss"                        # 失落/哀伤
    
    # 社会与文化
    ETHICS = "ethics"                    # 伦理/正义
    MEDIA = "media"                      # 媒体/信息
    OTHER = "other"                      # 其他/独特

class MotiveType(str, Enum):
    FEAR = "fear"
    PRIDE = "pride"
    LOVE = "love"
    DESIRE = "desire"
    DUTY = "duty"
    AMBITION = "ambition"

class DiscernmentSource(str, Enum):
    INNER_WISDOM = "inner_wisdom"        # 内在智慧/本心
    CONSCIENCE = "conscience"            # 良心/理性
    FEAR_RESPONSE = "fear_response"      # 恐惧反应
    PRIDE_RESPONSE = "pride_response"    # 骄傲反应
    TRAUMA_RESPONSE = "trauma_response" # 创伤反应
    SOCIAL_PRESSURE = "social_pressure"  # 社会压力
    IMPULSE = "impulse"                  # 冲动/欲望
    UNCERTAIN = "uncertain"              # 不确定

class GuidancePriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

# ==================== PYDANTIC MODELS ====================

# ==================== 扩展状态快照（12维度，覆盖身心灵社智财道）====================
class StateSnapshot(BaseModel):
    """用户状态快照 — 12维度现代生活完整画像"""
    # 基础5维度（身心灵核心）
    stress_level: int = Field(ge=0, le=10, default=5, description="压力水平 0-10：外部要求与内部资源的差距")
    anxiety_level: int = Field(ge=0, le=10, default=5, description="焦虑水平 0-10：对未来不确定的担忧程度")
    fatigue_level: int = Field(ge=0, le=10, default=5, description="疲劳水平 0-10：身心能量耗竭的感受")
    spiritual_dryness: int = Field(ge=0, le=10, default=5, description="内心枯竭 0-10：与内在自我连接的感受减弱")
    emotional_stability: int = Field(ge=0, le=10, default=5, description="情绪稳定性 0-10：情绪波动的可控程度")
    
    # 扩展7维度（现代生活全景）
    physical_health: int = Field(ge=0, le=10, default=5, description="身体健康 0-10：身体状况与精力水平")
    sleep_quality: int = Field(ge=0, le=10, default=5, description="睡眠质量 0-10：休息恢复与睡眠满意度")
    social_connection: int = Field(ge=0, le=10, default=5, description="社交连接 0-10：关系网络与支持系统")
    financial_pressure: int = Field(ge=0, le=10, default=5, description="财务压力 0-10：经济焦虑与资源担忧")
    cognitive_clarity: int = Field(ge=0, le=10, default=5, description="认知清晰 0-10：思维清晰度与专注力")
    identity_confusion: int = Field(ge=0, le=10, default=5, description="身份困惑 0-10：自我认知与定位迷茫")
    moral_tension: int = Field(ge=0, le=10, default=5, description="道德张力 0-10：价值观冲突与良心挣扎")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class EmotionLog(BaseModel):
    """情绪记录"""
    emotion_type: str
    intensity: int = Field(ge=0, le=10)
    trigger: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MotiveAnalysis(BaseModel):
    """动机分析"""
    fear_driven_score: float = Field(ge=0, le=1, description="恐惧驱动程度")
    pride_driven_score: float = Field(ge=0, le=1, description="骄傲驱动程度")
    love_driven_score: float = Field(ge=0, le=1, description="爱驱动程度")
    desire_driven_score: float = Field(ge=0, le=1, description="欲望驱动程度")
    dominant_motive: MotiveType
    secondary_motive: Optional[MotiveType] = None
    analysis_notes: Optional[str] = None

class DiscernmentResult(BaseModel):
    """辨识结果"""
    primary_source: DiscernmentSource
    secondary_source: Optional[DiscernmentSource] = None
    confidence: float = Field(ge=0, le=1, description="置信度")
    explanation: str
    alignment_score: float = Field(ge=0, le=1)
    long_term_fruit_score: float = Field(ge=-1, le=1, description="长期结果预测 -1负面到1正面")

class GuidanceOutput(BaseModel):
    """指导输出"""
    structured_advice: str
    risks: List[str]
    alternative_interpretations: List[str]
    recommended_actions: List[str]
    priority: GuidancePriority
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DecisionEventCreate(BaseModel):
    """创建决策事件"""
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category: DecisionCategory
    urgency: int = Field(ge=1, le=5, description="紧急程度 1-5")
    importance: int = Field(ge=1, le=5, description="重要程度 1-5")
    state_snapshot: StateSnapshot
    emotion_logs: List[EmotionLog] = []
    context_factors: Optional[Dict[str, Any]] = None

class DecisionEventResponse(BaseModel):
    """决策事件响应"""
    id: str
    title: str
    description: Optional[str]
    category: DecisionCategory
    urgency: int
    importance: int
    state_snapshot: StateSnapshot
    emotion_logs: List[EmotionLog]
    motive_analysis: Optional[MotiveAnalysis]
    discernment_result: Optional[DiscernmentResult]
    guidance: Optional[GuidanceOutput]
    created_at: datetime
    updated_at: datetime
    status: str

class ReviewLogCreate(BaseModel):
    """回顾记录创建"""
    decision_id: str
    outcome_description: str
    peace_level: int = Field(ge=-5, le=5, description="内心平静感 -5后悔到5极大平静")
    regret_level: int = Field(ge=0, le=10)
    lessons_learned: Optional[str] = None
    growth_impact: Optional[str] = None  # renamed from character_impact

class WisdomPrinciple(BaseModel):
    """智慧原则"""
    id: str
    principle_text: str
    reference: Optional[str]
    category: str
    embedding: Optional[List[float]] = None

# ==================== WISDOM PRINCIPLES DATA ====================

DEFAULT_WISDOM_PRINCIPLES = [
    {"id": "1", "principle_text": "凡事察验，善美的要持守", "reference": "智慧格言", "category": "discernment"},
    {"id": "2", "principle_text": "你要保守你心，胜过保守一切", "reference": "内心守护", "category": "heart_guarding"},
    {"id": "3", "principle_text": "不要恐惧，因为我与你同在", "reference": "勇气支持", "category": "fear"},
    {"id": "4", "principle_text": "看别人比自己强", "reference": "谦逊智慧", "category": "humility"},
    {"id": "5", "principle_text": "凭果子认出他们来", "reference": "结果验证", "category": "fruit"},
    {"id": "6", "principle_text": "爱比成功更高", "reference": "爱的优先", "category": "love"},
    {"id": "7", "principle_text": "真理比舒适更重要", "reference": "真实勇气", "category": "truth"},
    {"id": "8", "principle_text": "谦卑在智慧以先", "reference": "谦逊智慧", "category": "wisdom"},
    {"id": "9", "principle_text": "安息是内在操练", "reference": "休息重要", "category": "rest"},
    {"id": "10", "principle_text": "听从良知，不随波逐流", "reference": "独立判断", "category": "obedience"},
    {"id": "11", "principle_text": "愿意受苦而不愿违背良知", "reference": "坚守原则", "category": "sacrifice"},
    {"id": "12", "principle_text": "患难生忍耐，忍耐生老练", "reference": "成长历练", "category": "patience"},
    {"id": "13", "principle_text": "不可为恶所胜，反要以善胜恶", "reference": "善胜恶", "category": "victory"},
    {"id": "14", "principle_text": "在压力中保持平静", "reference": "内在平静", "category": "peace"},
    {"id": "15", "principle_text": "不为明天忧虑", "reference": "活在当下", "category": "anxiety"},
]

# ==================== CORE DISCERNMENT ENGINE ====================

class DiscernmentEngine:
    """辨识引擎 - 核心决策分析逻辑"""
    
    @staticmethod
    def analyze_motives(state: StateSnapshot, emotions: List[EmotionLog], context: Dict) -> MotiveAnalysis:
        """分析动机 - 恐惧、骄傲、爱、欲望的比例"""
        
        # 基于状态快照计算
        fear_score = min(1.0, (state.anxiety_level + state.stress_level) / 15)
        pride_score = 0.3  # 基础值，需要更多上下文判断
        love_score = 0.5  # 基础值
        desire_score = 0.4  # 基础值
        
        # 基于情绪调整 — 覆盖 MVFE 提取的全部情绪类型
        for emotion in emotions:
            if emotion.emotion_type in ["fear", "anxiety", "worry", "panic"]:
                fear_score = min(1.0, fear_score + emotion.intensity / 10)
            elif emotion.emotion_type in ["anger", "frustration", "irritation", "disgust"]:
                pride_score = min(1.0, pride_score + emotion.intensity / 15)
            elif emotion.emotion_type in ["joy", "peace", "love", "gratitude", "hope"]:
                love_score = min(1.0, love_score + emotion.intensity / 10)
            elif emotion.emotion_type in ["desire", "longing", "craving", "lust", "envy"]:
                desire_score = min(1.0, desire_score + emotion.intensity / 10)
            elif emotion.emotion_type in ["shame", "guilt"]:
                fear_score = min(1.0, fear_score + emotion.intensity / 12)
                desire_score = min(1.0, desire_score + emotion.intensity / 20)
            elif emotion.emotion_type in ["sadness", "loneliness"]:
                fear_score = min(1.0, fear_score + emotion.intensity / 15)
                love_score = max(0.0, love_score - emotion.intensity / 20)
            elif emotion.emotion_type == "confusion":
                fear_score = min(1.0, fear_score + emotion.intensity / 20)
            elif emotion.emotion_type == "surprise":
                pass  # 惊讶是中性的，不单独影响动机
        
        # 确定主导动机
        scores = {
            MotiveType.FEAR: fear_score,
            MotiveType.PRIDE: pride_score,
            MotiveType.LOVE: love_score,
            MotiveType.DESIRE: desire_score,
        }
        
        dominant = max(scores, key=scores.get)
        secondary = None
        
        # 找第二高的
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_scores) > 1 and sorted_scores[1][1] > 0.3:
            secondary = sorted_scores[1][0]
        
        return MotiveAnalysis(
            fear_driven_score=fear_score,
            pride_driven_score=pride_score,
            love_driven_score=love_score,
            desire_driven_score=desire_score,
            dominant_motive=dominant,
            secondary_motive=secondary,
            analysis_notes=f"主导动机: {dominant.value}, 恐惧指数: {fear_score:.2f}"
        )
    
    @staticmethod
    def discern_source(motive: MotiveAnalysis, state: StateSnapshot) -> DiscernmentResult:
        """辨识来源 - 内在智慧、创伤、恐惧、骄傲等"""
        
        # 规则引擎
        if motive.fear_driven_score > 0.6:
            source = DiscernmentSource.FEAR_RESPONSE
            confidence = motive.fear_driven_score
            explanation = "决策明显受恐惧驱动。恐惧驱动的决定往往导致逃避或过度控制，而非信心。"
            long_term_fruit = -0.4
            
        elif motive.pride_driven_score > 0.6:
            source = DiscernmentSource.PRIDE_RESPONSE
            confidence = motive.pride_driven_score
            explanation = "决策明显受骄傲驱动。骄傲驱动的决定往往追求外在认可而非内在平静。"
            long_term_fruit = -0.3
            
        elif motive.love_driven_score > 0.7 and motive.fear_driven_score < 0.3:
            source = DiscernmentSource.INNER_WISDOM
            confidence = motive.love_driven_score * 0.8
            explanation = "决策由爱与平静驱动，与内在智慧相符。决策包含为他人益处考虑。"
            long_term_fruit = 0.7
            
        elif state.spiritual_dryness > 6:
            source = DiscernmentSource.TRAUMA_RESPONSE
            confidence = min(1.0, state.spiritual_dryness / 10)
            explanation = "内心枯竭期做出的决策容易受创伤模式影响。建议先恢复心理健康。"
            long_term_fruit = -0.2
            
        elif motive.desire_driven_score > 0.6:
            source = DiscernmentSource.IMPULSE
            confidence = motive.desire_driven_score
            explanation = "决策明显受冲动驱动。这种决定往往带来短期满足但长期后悔。"
            long_term_fruit = -0.5
            
        else:
            source = DiscernmentSource.UNCERTAIN
            confidence = 0.5
            explanation = "动机混合，难以明确辨识。建议延迟决策，寻求更多静思和辅导。"
            long_term_fruit = 0.0
        
        # 根据状态稳定性调整
        if state.emotional_stability < 4:
            confidence *= 0.7
            explanation += " 情绪不稳定期，决策质量可能受影响。"
            long_term_fruit -= 0.2
        
        return DiscernmentResult(
            primary_source=source,
            confidence=round(confidence, 2),
            explanation=explanation,
            alignment_score=0.6 if source == DiscernmentSource.INNER_WISDOM else 0.3,
            long_term_fruit_score=round(long_term_fruit, 2)
        )
    
    @staticmethod
    def generate_guidance(
        decision: DecisionEventCreate,
        motive: MotiveAnalysis,
        discernment: DiscernmentResult,
        principles: List[WisdomPrinciple]
    ) -> GuidanceOutput:
        """生成指导建议"""
        
        risks = []
        alternatives = []
        actions = []
        priority = GuidancePriority.MEDIUM
        
        # 根据辨识结果生成建议
        if discernment.primary_source == DiscernmentSource.FEAR_RESPONSE:
            risks = [
                "逃避可能使问题恶化",
                "恐惧中的决定往往过度保守",
                "可能错过成长机会"
            ]
            alternatives = [
                "这可能是勇气的试炼而非危险信号",
                "恐惧往往放大风险，实际后果可能没那么严重",
                "考虑如果完全不怕，你会如何选择"
            ]
            actions = [
                "暂停24-48小时，等情绪平复",
                "与信任的朋友或导师讨论",
                "写下最坏的后果，评估是否可承受"
            ]
            priority = GuidancePriority.HIGH
            
        elif discernment.primary_source == DiscernmentSource.PRIDE_RESPONSE:
            risks = [
                "为维护面子而坚持错误决定",
                "忽视他人合理建议",
                "成功后骄傲更加膨胀"
            ]
            alternatives = [
                "放下需要被认可的渴望",
                "考虑如果无人知晓你的选择，你会怎么做",
                "内在平静比外在成就更重要"
            ]
            actions = [
                "寻求你最尊重的人的诚实反馈",
                "练习说出'我不知道'",
                "反思谦逊的榜样"
            ]
            priority = GuidancePriority.HIGH
            
        elif discernment.primary_source == DiscernmentSource.INNER_WISDOM:
            risks = [
                "即使内心平静也要验证实际可行性",
                "注意区分内在智慧与自我兴奋",
                "内心冲动也需要智慧执行"
            ]
            alternatives = [
                "这是方向确认而非细节的命令",
                "保持开放，可能会有调整",
                "内在智慧通常伴随平静而非焦虑"
            ]
            actions = [
                "记录这次感受，便于日后回顾",
                "与导师分享寻求印证",
                "制定实际可行的步骤计划",
                "预备面对可能的反对"
            ]
            priority = GuidancePriority.MEDIUM
            
        else:  # 不确定或其他
            risks = [
                "匆忙决定可能带来后悔",
                "混杂动机导致复杂后果",
                "当下最优可能非长期最优"
            ]
            alternatives = [
                "延迟决定直到获得更清晰的确信",
                "考虑咨询专业人士或导师",
                "从智慧经典中寻找类似处境的启发"
            ]
            actions = [
                "为自己设定决策截止日期",
                "收集更多信息",
                "列出赞成与反对的理由",
                "寻求来自不同视角的建议"
            ]
        
        # 根据紧急度调整
        if decision.urgency >= 4:
            priority = GuidancePriority.HIGH
            actions.insert(0, "⚠️ 紧急决策：在有限时间内尽力寻求支持")
        
        advice = f"""
基于当前状态分析：
- 主导动机：{motive.dominant_motive.value}
- 决策来源：{discernment.primary_source.value}
- 长期结果预测：{discernment.long_term_fruit_score:+.1f}（负值表示可能带来问题）

{discernment.explanation}
""".strip()
        
        return GuidanceOutput(
            structured_advice=advice,
            risks=risks,
            alternative_interpretations=alternatives,
            recommended_actions=actions,
            priority=priority
        )

# ==================== DATABASE FUNCTIONS ====================

class DSSStorage:
    """数据库存储层 (psycopg2 ThreadedConnectionPool)"""

    def __init__(self, db_pool):
        self.db = db_pool

    def _getconn(self):
        conn = self.db.getconn()
        if conn.closed:
            self.db.putconn(conn, close=True)
            conn = self.db.getconn()
        return conn

    def _putconn(self, conn):
        if conn and not conn.closed:
            try:
                conn.rollback()
            except Exception:
                pass
            self.db.putconn(conn)

    # ── sync helpers (run via asyncio.to_thread from async endpoints) ──

    def _create_decision_event_sync(self, user_id: str, decision: DecisionEventCreate) -> str:
        decision_id = str(uuid.uuid4())
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO dss_decision_events
                    (id, user_id, title, description, category, urgency, importance,
                     stress_level, anxiety_level, fatigue_level, spiritual_dryness, emotional_stability,
                     physical_health, sleep_quality, social_connection, financial_pressure,
                     cognitive_clarity, identity_confusion, moral_tension,
                     emotion_logs, context_factors, status, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, NOW())
                """, (
                    decision_id, user_id, decision.title, decision.description,
                    decision.category.value, decision.urgency, decision.importance,
                    decision.state_snapshot.stress_level,
                    decision.state_snapshot.anxiety_level,
                    decision.state_snapshot.fatigue_level,
                    decision.state_snapshot.spiritual_dryness,
                    decision.state_snapshot.emotional_stability,
                    decision.state_snapshot.physical_health,
                    decision.state_snapshot.sleep_quality,
                    decision.state_snapshot.social_connection,
                    decision.state_snapshot.financial_pressure,
                    decision.state_snapshot.cognitive_clarity,
                    decision.state_snapshot.identity_confusion,
                    decision.state_snapshot.moral_tension,
                    json.dumps([e.dict() for e in decision.emotion_logs], default=str),
                    json.dumps(decision.context_factors, default=str) if decision.context_factors else None,
                    "analyzing",
                ))
                conn.commit()
        finally:
            self._putconn(conn)
        return decision_id

    def _update_motive_analysis_sync(self, decision_id: str, analysis: MotiveAnalysis):
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE dss_decision_events
                    SET motive_analysis = %s, updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(analysis.dict(), default=str), decision_id))
                conn.commit()
        finally:
            self._putconn(conn)

    def _update_discernment_result_sync(self, decision_id: str, result: DiscernmentResult):
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE dss_decision_events
                    SET discernment_result = %s, updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(result.dict(), default=str), decision_id))
                conn.commit()
        finally:
            self._putconn(conn)

    def _update_guidance_sync(self, decision_id: str, guidance: GuidanceOutput):
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE dss_decision_events
                    SET guidance = %s, status = 'guided', updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(guidance.dict(), default=str), decision_id))
                conn.commit()
        finally:
            self._putconn(conn)

    def _get_user_decisions_sync(self, user_id: str, limit: int = 20) -> List[Dict]:
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM dss_decision_events
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                if not cur.description:
                    return []
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._putconn(conn)

    def _get_decision_by_id_sync(self, decision_id: str) -> Optional[Dict]:
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM dss_decision_events WHERE id = %s", (decision_id,))
                row = cur.fetchone()
                if not row:
                    return None
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
        finally:
            self._putconn(conn)

    def _create_review_log_sync(self, user_id: str, review: ReviewLogCreate) -> str:
        review_id = str(uuid.uuid4())
        conn = self._getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO dss_review_logs
                    (id, user_id, decision_id, outcome_description, peace_level,
                     regret_level, lessons_learned, growth_impact, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())
                """, (
                    review_id, user_id, review.decision_id, review.outcome_description,
                    review.peace_level, review.regret_level, review.lessons_learned,
                    review.growth_impact,
                ))
                cur.execute("""
                    UPDATE dss_decision_events
                    SET status = 'reviewed', updated_at = NOW()
                    WHERE id = %s
                """, (review.decision_id,))
                conn.commit()
        finally:
            self._putconn(conn)
        return review_id

    # ── async wrappers ──

    async def create_decision_event(self, user_id: str, decision: DecisionEventCreate) -> str:
        return await asyncio.to_thread(self._create_decision_event_sync, user_id, decision)

    async def update_motive_analysis(self, decision_id: str, analysis: MotiveAnalysis):
        await asyncio.to_thread(self._update_motive_analysis_sync, decision_id, analysis)

    async def update_discernment_result(self, decision_id: str, result: DiscernmentResult):
        await asyncio.to_thread(self._update_discernment_result_sync, decision_id, result)

    async def update_guidance(self, decision_id: str, guidance: GuidanceOutput):
        await asyncio.to_thread(self._update_guidance_sync, decision_id, guidance)

    async def get_user_decisions(self, user_id: str, limit: int = 20) -> List[Dict]:
        return await asyncio.to_thread(self._get_user_decisions_sync, user_id, limit)

    async def get_decision_by_id(self, decision_id: str) -> Optional[Dict]:
        return await asyncio.to_thread(self._get_decision_by_id_sync, decision_id)

    async def create_review_log(self, user_id: str, review: ReviewLogCreate):
        return await asyncio.to_thread(self._create_review_log_sync, user_id, review)

# ==================== API ENDPOINTS ====================

# 全局存储实例（需要在main.py中初始化）
dss_storage: Optional[DSSStorage] = None
discernment_engine = DiscernmentEngine()

def init_dss_storage(db_pool):
    """初始化存储"""
    global dss_storage
    dss_storage = DSSStorage(db_pool)

@router.post("/decisions", response_model=Dict[str, str])
async def create_decision(
    decision: DecisionEventCreate,
    background_tasks: BackgroundTasks,
    user_id: str = "current_user"  # 实际应从token获取
):
    """创建新的决策事件并进行分析"""
    if not dss_storage:
        raise HTTPException(status_code=500, detail="DSS storage not initialized")
    
    try:
        # 创建决策记录
        decision_id = await dss_storage.create_decision_event(user_id, decision)
    except Exception as exc:
        print(f'[DSS] create_decision_event failed: {exc}', flush=True)
        raise HTTPException(status_code=500, detail=f"决策创建失败: {exc}")
    
    # 同步执行分析（计算量小，无需后台任务）
    try:
        await analyze_decision_background(decision_id, decision, user_id)
    except Exception as exc:
        print(f'[DSS] analyze_decision inline failed: {exc}', flush=True)
    
    return {"id": decision_id, "status": "analyzing", "message": "决策分析进行中，请稍后查看结果"}

async def analyze_decision_background(decision_id: str, decision: DecisionEventCreate, user_id: str = "current_user"):
    """后台分析决策"""
    try:
        # 1. 动机分析
        motive = discernment_engine.analyze_motives(
            decision.state_snapshot,
            decision.emotion_logs,
            decision.context_factors or {}
        )
        await dss_storage.update_motive_analysis(decision_id, motive)
        
        # 2. 来源辨识
        discernment = discernment_engine.discern_source(
            motive,
            decision.state_snapshot
        )
        await dss_storage.update_discernment_result(decision_id, discernment)
        
        # 3. 生成指导（简化版，实际应使用向量检索）
        principles = [WisdomPrinciple(**p) for p in DEFAULT_WISDOM_PRINCIPLES]
        guidance = discernment_engine.generate_guidance(
            decision,
            motive,
            discernment,
            principles
        )
        await dss_storage.update_guidance(decision_id, guidance)

    except Exception as e:
        logger.error(f"[DSS] Analysis failed for decision {decision_id}: {e}")

@router.get("/decisions")
async def list_decisions(user_id: str = "current_user", limit: int = 20):
    """获取用户的决策历史"""
    if not dss_storage:
        raise HTTPException(status_code=500, detail="DSS storage not initialized")
    
    decisions = await dss_storage.get_user_decisions(user_id, limit)
    return decisions

@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str, user_id: str = "current_user"):
    """获取单个决策详情"""
    if not dss_storage:
        raise HTTPException(status_code=500, detail="DSS storage not initialized")
    
    decision = await dss_storage.get_decision_by_id(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="决策不存在")
    
    return decision

@router.post("/reviews")
async def create_review(review: ReviewLogCreate, user_id: str = "current_user"):
    """创建回顾记录"""
    if not dss_storage:
        raise HTTPException(status_code=500, detail="DSS storage not initialized")
    
    review_id = await dss_storage.create_review_log(user_id, review)
    return {"id": review_id, "status": "created"}
