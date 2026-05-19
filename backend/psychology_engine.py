"""
心理学引擎 - L0-L4 架构完整实现
人格因果引擎 + 行为调节引擎 + 执行力边缘引导 + 长期身份认同 + 记忆与成长轨迹
"""

import json
import os
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import time

# 导入查询模块用于LLM调用
try:
    from query_emotion_verses import call_chat
except ImportError:
    call_chat = None


# ============================================================
# 数据模型
# ============================================================

@dataclass
class PersonalityDriver:
    """L0: 人格驱动因子"""
    surface_problem: str = ""
    deep_emotion: str = ""
    hidden_dynamics: str = ""
    behavioral_cycle: dict = field(default_factory=dict)
    personality_traits: list = field(default_factory=list)
    long_term_risk: str = ""
    intervention_priority: int = 3
    driver_category: str = ""
    core_belief: str = ""
    
    def to_dict(self) -> dict:
        return {
            "surface_problem": self.surface_problem,
            "deep_emotion": self.deep_emotion,
            "hidden_dynamics": self.hidden_dynamics,
            "behavioral_cycle": self.behavioral_cycle,
            "personality_traits": self.personality_traits,
            "long_term_risk": self.long_term_risk,
            "intervention_priority": self.intervention_priority,
            "driver_category": self.driver_category,
            "core_belief": self.core_belief
        }


@dataclass
class CognitiveSchema:
    """L1: 认知图式"""
    schema_id: str = ""
    schema_name: str = ""
    distortion_type: str = ""
    activating_event: str = ""
    consequence_emotional: str = ""
    consequence_behavioral: str = ""
    core_belief: str = ""
    cognitive_reframing_patch: str = ""
    severity_score: int = 5
    
    def to_dict(self) -> dict:
        return {
            "schema_id": self.schema_id,
            "schema_name": self.schema_name,
            "distortion_type": self.distortion_type,
            "activating_event": self.activating_event,
            "consequence_emotional": self.consequence_emotional,
            "consequence_behavioral": self.consequence_behavioral,
            "core_belief": self.core_belief,
            "cognitive_reframing_patch": self.cognitive_reframing_patch,
            "severity_score": self.severity_score
        }


@dataclass
class BehavioralExperiment:
    """L1: 行为实验"""
    experiment_id: str = ""
    title: str = ""
    hypothesis_to_test: str = ""
    counter_behavioral_action: str = ""
    difficulty_level: int = 2
    estimated_duration_minutes: int = 10
    binary_telemetry_metric: str = ""
    
    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "title": self.title,
            "hypothesis_to_test": self.hypothesis_to_test,
            "counter_behavioral_action": self.counter_behavioral_action,
            "difficulty_level": self.difficulty_level,
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "binary_telemetry_metric": self.binary_telemetry_metric
        }


@dataclass
class PsychologicalState:
    """L2: 心理状态快照"""
    state_name: str = ""
    state_level: int = 2
    arousal_level: int = 5
    valence_score: int = 0
    focus_capacity: int = 5
    triggering_factors: list = field(default_factory=list)
    protective_factors: list = field(default_factory=list)
    recommended_action: str = ""
    escalation_protocol: str = ""
    
    def to_dict(self) -> dict:
        return {
            "state_name": self.state_name,
            "state_level": self.state_level,
            "arousal_level": self.arousal_level,
            "valence_score": self.valence_score,
            "focus_capacity": self.focus_capacity,
            "triggering_factors": self.triggering_factors,
            "protective_factors": self.protective_factors,
            "recommended_action": self.recommended_action,
            "escalation_protocol": self.escalation_protocol
        }


@dataclass
class IdentityNarrative:
    """L3: 身份认同叙事"""
    narrative_type: str = ""
    narrative_title: str = ""
    identity_themes: list = field(default_factory=list)
    core_values: list = field(default_factory=list)
    coherence_score: int = 5
    agency_score: int = 5
    redemption_score: int = 5
    
    def to_dict(self) -> dict:
        return {
            "narrative_type": self.narrative_type,
            "narrative_title": self.narrative_title,
            "identity_themes": self.identity_themes,
            "core_values": self.core_values,
            "coherence_score": self.coherence_score,
            "agency_score": self.agency_score,
            "redemption_score": self.redemption_score
        }


@dataclass
class GrowthMetrics:
    """L4: 成长轨迹指标"""
    emotional_regulation: int = 50
    cognitive_flexibility: int = 50
    behavioral_activation: int = 50
    interpersonal_effectiveness: int = 50
    self_concept_clarity: int = 50
    generated_insights: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "emotional_regulation": self.emotional_regulation,
            "cognitive_flexibility": self.cognitive_flexibility,
            "behavioral_activation": self.behavioral_activation,
            "interpersonal_effectiveness": self.interpersonal_effectiveness,
            "self_concept_clarity": self.self_concept_clarity,
            "generated_insights": self.generated_insights
        }


# ============================================================
# L0: 人格因果引擎
# ============================================================

class PersonalityCausalEngine:
    """L0: 识别行为背后的心理动力因果"""
    
    SYSTEM_PROMPT = """你是一个"人格因果分析引擎（Personality Causal Engine）"。

你的目标不是娱乐性人格测试，而是识别用户长期行为模式背后的心理动力系统。

建立「人格特征 → 情绪触发 → 行为模式 → 结果反馈」的长期因果链。

输出严格JSON格式：
{
  "surface_problem": "表层问题",
  "deep_emotion": "深层情绪",
  "hidden_dynamics": "隐藏心理动力",
  "behavioral_cycle": {
    "trigger": "触发器",
    "emotion": "产生的情绪",
    "escape": "逃避行为",
    "reward": "短期奖励",
    "shame": "羞耻感",
    "repeat": "循环重复"
  },
  "personality_traits": ["特征1", "特征2"],
  "long_term_risk": "长期风险",
  "intervention_priority": 1-5,
  "driver_category": "Perfectionism/Catastrophizing/Impostor_Syndrome/Emotional_Reasoning/Overgeneralization",
  "core_belief": "核心信念"
}"""

    def analyze(self, user_input: str, historical_context: Optional[str] = None) -> PersonalityDriver:
        prompt = user_input
        if historical_context:
            prompt = f"【历史背景】\n{historical_context}\n\n【当前输入】\n{user_input}"
        
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT, prompt, temperature=0.3)
            else:
                raw = self._mock_analyze()
            
            data = self._parse_json(raw)
            return PersonalityDriver(**data)
        except Exception as e:
            print(f"[L0] Analysis failed: {e}", flush=True)
            return self._fallback(user_input)
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except:
            for pattern in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                matches = re.findall(pattern, raw, re.DOTALL)
                for m in matches:
                    try:
                        return json.loads(m.strip())
                    except:
                        continue
        return {}
    
    def _fallback(self, user_input: str) -> PersonalityDriver:
        return PersonalityDriver(
            surface_problem=user_input[:100],
            deep_emotion="需要进一步分析",
            hidden_dynamics="系统暂时无法识别深层动力",
            behavioral_cycle={"trigger": "待识别", "emotion": "焦虑", "escape": "逃避", "reward": "短暂缓解", "shame": "自责", "repeat": "循环"},
            personality_traits=["分析中..."],
            long_term_risk="如果持续回避，可能形成逃避型人格模式",
            intervention_priority=3,
            driver_category="Unknown",
            core_belief="待探索"
        )
    
    def _mock_analyze(self) -> str:
        return json.dumps({
            "surface_problem": "用户表达了情绪困扰",
            "deep_emotion": "焦虑和无助感",
            "hidden_dynamics": "完美主义与恐惧失败的冲突",
            "behavioral_cycle": {
                "trigger": "高压力任务",
                "emotion": "焦虑",
                "escape": "拖延/刷手机",
                "reward": "暂时缓解焦虑",
                "shame": "自责",
                "repeat": "再次拖延"
            },
            "personality_traits": ["完美主义", "高度自我批评"],
            "long_term_risk": "习得性无助和慢性拖延",
            "intervention_priority": 4,
            "driver_category": "Perfectionism",
            "core_belief": "如果我做得不够好，我就是个失败者"
        })


# ============================================================
# L1: 认知图式引擎
# ============================================================

class SchemaEngine:
    """L1: 基于 REBT ABC模型 + Schema Therapy"""
    
    SYSTEM_PROMPT = """# Mental Topology & Schema Architecture Specialist

基于CBT和REBT分析，输出严格JSON：
{
  "abc_analysis": {
    "activating_event": "客观触发事件",
    "consequence_emotional": "具体情绪",
    "consequence_behavioral": "应对机制"
  },
  "latent_schema": {
    "distortion_type": "认知扭曲类型",
    "core_belief": "非理性核心信念"
  },
  "cognitive_reframing_patch": "客观理性的自我对话语句",
  "behavioral_experiment": {
    "experiment_id": "exp_时间戳_cat_001",
    "title": "实验标题",
    "hypothesis_to_test": "要证伪的假设",
    "counter_behavioral_action": "低摩擦具体行动",
    "binary_telemetry_metric": "二元遥测指标"
  }
}"""

    def analyze(self, user_input: str, personality_driver: Optional[PersonalityDriver] = None) -> tuple:
        context = user_input
        if personality_driver:
            context += f"\n\n【人格驱动】核心信念：{personality_driver.core_belief}，类型：{personality_driver.driver_category}"
        
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT, context, temperature=0.4)
            else:
                raw = self._mock()
            
            data = self._parse_json(raw)
            
            abc = data.get("abc_analysis", {})
            ls = data.get("latent_schema", {})
            be = data.get("behavioral_experiment", {})
            
            schema = CognitiveSchema(
                schema_id=str(uuid.uuid4()),
                schema_name=f"Schema_{ls.get('distortion_type', 'Unknown')}",
                distortion_type=ls.get("distortion_type", "Unknown"),
                activating_event=abc.get("activating_event", ""),
                consequence_emotional=abc.get("consequence_emotional", ""),
                consequence_behavioral=abc.get("consequence_behavioral", ""),
                core_belief=ls.get("core_belief", ""),
                cognitive_reframing_patch=data.get("cognitive_reframing_patch", ""),
                severity_score=5
            )
            
            experiment = BehavioralExperiment(
                experiment_id=be.get("experiment_id", f"exp_{int(time.time())}"),
                title=be.get("title", "行为实验"),
                hypothesis_to_test=be.get("hypothesis_to_test", ""),
                counter_behavioral_action=be.get("counter_behavioral_action", ""),
                binary_telemetry_metric=be.get("binary_telemetry_metric", "完成：是/否")
            )
            
            return schema, experiment
        except Exception as e:
            print(f"[L1] Schema failed: {e}", flush=True)
            return self._fallback()
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try:
                        return json.loads(m.strip())
                    except:
                        continue
        return {}
    
    def _fallback(self) -> tuple:
        return (
            CognitiveSchema(
                schema_id=str(uuid.uuid4()),
                core_belief="我需要更多时间来理解",
                cognitive_reframing_patch="暂时无法生成重构语句",
                severity_score=3
            ),
            BehavioralExperiment(
                experiment_id=f"exp_{int(time.time())}",
                title="情绪觉察练习",
                hypothesis_to_test="记录下此刻的情绪不会让我更糟",
                counter_behavioral_action="写下此刻的三个感受词",
                binary_telemetry_metric="是否写下了三个词：是/否"
            )
        )
    
    def _mock(self) -> str:
        return json.dumps({
            "abc_analysis": {
                "activating_event": "技术汇报前夜",
                "consequence_emotional": "严重急性焦虑，失眠",
                "consequence_behavioral": "通过刷手机逃避准备"
            },
            "latent_schema": {
                "distortion_type": "Catastrophizing",
                "core_belief": "一次不完美的汇报将导致职业彻底毁灭"
            },
            "cognitive_reframing_patch": "汇报是临时的数据同步，不是对我系统性价值的永久评估",
            "behavioral_experiment": {
                "experiment_id": f"exp_{int(time.time())}_cat_001",
                "title": "瑕疵同步者",
                "hypothesis_to_test": "在草稿中故意包含一个非关键错误会导致同事完全否定我的技术能力",
                "counter_behavioral_action": "立即发送一个边距未对齐的幻灯片给信任的同事征求意见",
                "binary_telemetry_metric": "同事是否明确说你的整个职业生涯毁了？（是/否）"
            }
        })


# ============================================================
# L2: 状态机引擎
# ============================================================

class StateMachineEngine:
    """L2: 执行力边缘引导 - 心理状态机"""
    
    def assess(self, user_input: str, intensity: int = 5) -> PsychologicalState:
        crisis_kw = ['自杀', '想死', '活不下去', '绝望', '结束一切']
        dysreg_kw = ['崩溃', '受不了了', '失控', 'panic', '崩溃边缘']
        
        text = user_input.lower()
        
        if any(k in text for k in crisis_kw):
            return PsychologicalState(
                state_name="CRISIS", state_level=0, arousal_level=9, valence_score=-9,
                focus_capacity=2,
                triggering_factors=[{"type": "internal", "description": "绝望感", "intensity": 10}],
                recommended_action="【紧急】立即联系危机干预热线：400-161-9995",
                escalation_protocol="不要独自承受，立即寻求专业帮助"
            )
        
        if any(k in text for k in dysreg_kw) or intensity >= 8:
            return PsychologicalState(
                state_name="DYSREGULATED", state_level=1, arousal_level=intensity,
                valence_score=-intensity//2, focus_capacity=max(2, 10-intensity),
                triggering_factors=[{"type": "stress", "description": "高压力情境", "intensity": intensity}],
                recommended_action="使用5-4-3-2-1 grounding：说出5个看到的、4个触摸到的、3个听到的、2个闻到的、1个尝到的",
                escalation_protocol="如果 grounding 无效超过30分钟，暂停当前活动"
            )
        
        if intensity <= 3:
            return PsychologicalState(
                state_name="INTEGRATED", state_level=4, arousal_level=4, valence_score=7,
                recommended_action="处于整合状态，适合反思和创造性活动",
                escalation_protocol="记录促进因素作为未来参考"
            )
        elif intensity <= 5:
            return PsychologicalState(
                state_name="FLOW", state_level=3, arousal_level=6, valence_score=5,
                recommended_action="保持当前节奏，避免打断",
                escalation_protocol="注意时间流逝，设置边界防止 burnout"
            )
        
        return PsychologicalState(
            state_name="REGULATED", state_level=2, arousal_level=5,
            recommended_action="状态良好，可以设定小目标保持动力"
        )


# ============================================================
# L3: 身份认同引擎
# ============================================================

class IdentityEngine:
    """L3: 长期身份认同系统"""
    
    PROMPT = """分析用户的身份认同，输出JSON：
{
  "narrative_type": "redemption/contamination/turning_point/stable",
  "narrative_title": "一句话概括身份故事",
  "identity_themes": ["主题1", "主题2"],
  "core_values": [{"value": "价值", "importance": 8}],
  "coherence_score": 1-10,
  "agency_score": 1-10,
  "redemption_score": 1-10
}"""

    def analyze(self, history: list[str]) -> IdentityNarrative:
        combined = "\n---\n".join(history[-10:])
        try:
            if call_chat:
                raw = call_chat(self.PROMPT, combined, temperature=0.5)
            else:
                raw = self._mock()
            data = json.loads(raw.strip())
            return IdentityNarrative(**data)
        except Exception as e:
            print(f"[L3] Identity failed: {e}", flush=True)
            return IdentityNarrative(
                narrative_type="stable",
                narrative_title="正在形成中的自我",
                identity_themes=["探索中"],
                core_values=[{"value": "自我理解", "importance": 8}]
            )
    
    def _mock(self) -> str:
        return json.dumps({
            "narrative_type": "redemption",
            "narrative_title": "从挣扎到成长的转变者",
            "identity_themes": ["幸存者", "成长者", "助人者"],
            "core_values": [{"value": "真实性", "importance": 9}, {"value": "成长", "importance": 8}],
            "coherence_score": 7, "agency_score": 6, "redemption_score": 8
        })


# ============================================================
# L4: 成长引擎
# ============================================================

class GrowthEngine:
    """L4: 记忆与成长轨迹"""
    
    def calculate(self, logs: list[dict], experiments: list[dict]) -> GrowthMetrics:
        if not logs:
            return GrowthMetrics()
        
        intensities = [l.get('intensity', 5) for l in logs]
        er = max(1, min(100, 100 - (max(intensities) - min(intensities)) * 10))
        
        all_tags = []
        for l in logs:
            all_tags.extend(l.get('emotion_tags', []))
        cf = min(100, 40 + len(set(all_tags)) * 5)
        
        completed = len([e for e in experiments if e.get('status') == 'completed'])
        ba = min(100, 30 + completed * 15)
        
        ie = 50  # 默认
        kw = ['朋友', '家人', '同事', '关系', '冲突', '孤独']
        cnt = sum(1 for l in logs for k in kw if k in l.get('raw_text', ''))
        ie = min(100, 40 + cnt * 10)
        
        insights = []
        if er > 70:
            insights.append("情绪调节能力较强")
        elif er < 40:
            insights.append("建议优先练习 grounding 技术")
        if ba > 70:
            insights.append("行为激活水平高，正在积极改变模式")
        
        return GrowthMetrics(emotional_regulation=er, cognitive_flexibility=cf,
                           behavioral_activation=ba, interpersonal_effectiveness=ie,
                           generated_insights=insights)


# ============================================================
# 统一协调器
# ============================================================

class PsychologyCoordinator:
    """L0-L4 统一协调器"""
    
    def __init__(self):
        self.l0 = PersonalityCausalEngine()
        self.l1 = SchemaEngine()
        self.l2 = StateMachineEngine()
        self.l3 = IdentityEngine()
        self.l4 = GrowthEngine()
    
    def analyze(self, user_input: str, user_id=None, history=None, intensity=5) -> dict:
        print(f"[Coordinator] Starting analysis for user {user_id}", flush=True)
        
        # L2优先：状态评估
        state = self.l2.assess(user_input, intensity)
        if state.state_level == 0:
            return {
                "layer": "L2_CRISIS",
                "state": state.to_dict(),
                "intervention": {"urgency": "critical", "action": state.recommended_action},
                "warning": "检测到危机状态，已跳过深度分析"
            }
        
        # L0: 人格因果
        hist_ctx = None
        if history:
            hist_ctx = "\n".join([h.get('raw_text', '') for h in history[-5:]])
        driver = self.l0.analyze(user_input, hist_ctx)
        
        # L1: 图式+实验
        schema, experiment = self.l1.analyze(user_input, driver)
        
        # L3: 身份（需要足够历史）
        identity = None
        if history and len(history) >= 5:
            texts = [h.get('raw_text', '') for h in history]
            identity = self.l3.analyze(texts)
        
        # L4: 成长
        growth = None
        if history:
            growth = self.l4.calculate(history, [])
        
        result = {
            "analysis_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "layers": {
                "L0_causal": {"personality_driver": driver.to_dict()},
                "L1_regulation": {
                    "cognitive_schema": schema.to_dict(),
                    "behavioral_experiment": experiment.to_dict()
                },
                "L2_execution": {"current_state": state.to_dict()}
            },
            "synthesis": {
                "immediate_action": state.recommended_action,
                "core_insight": f"你的{driver.driver_category}模式正在驱动{schema.consequence_behavioral or '逃避行为'}",
                "key_experiment": {
                    "title": experiment.title,
                    "action": experiment.counter_behavioral_action,
                    "metric": experiment.binary_telemetry_metric
                },
                "reframing_reminder": schema.cognitive_reframing_patch,
                "priority": driver.intervention_priority,
                "risk_level": "high" if driver.intervention_priority >= 4 else "medium"
            }
        }
        
        if identity:
            result["layers"]["L3_identity"] = {"identity_narrative": identity.to_dict()}
        if growth:
            result["layers"]["L4_memory"] = {"growth_metrics": growth.to_dict()}
        
        print(f"[Coordinator] Analysis completed", flush=True)
        return result


# 单例
coordinator = PsychologyCoordinator()

def analyze_emotion(user_input: str, user_id=None, history=None, intensity=5) -> dict:
    return coordinator.analyze(user_input, user_id, history, intensity)


# ============================================================
# 子系统二：行为调节系统 + 习惯养成状态机
# ============================================================

@dataclass
class BehaviorRegulationResult:
    """行为调节输出"""
    current_resistance: int = 5
    current_psychological_state: str = ""
    min_executable_action: str = ""
    task_downgrade: str = ""
    emotional_compensation: str = ""
    continuity_advice: str = ""
    selected_tier: str = "Yellow"
    
    def to_dict(self) -> dict:
        return {
            "current_resistance": self.current_resistance,
            "current_psychological_state": self.current_psychological_state,
            "min_executable_action": self.min_executable_action,
            "task_downgrade": self.task_downgrade,
            "emotional_compensation": self.emotional_compensation,
            "continuity_advice": self.continuity_advice,
            "selected_tier": self.selected_tier
        }


@dataclass
class HabitTierConfig:
    """习惯层级配置"""
    action_script: str = ""
    token_yield: int = 5
    estimated_duration: int = 10
    friction_level: str = "medium"  # low/medium/high


@dataclass
class HabitStateMachineResult:
    """习惯状态机执行结果"""
    habit_name: str = ""
    deterministic_anchor: str = ""
    selected_tier: str = "Yellow"
    action_to_execute: str = ""
    token_yield: int = 5
    anti_guilt_message: str = ""
    energy_level: int = 3
    
    def to_dict(self) -> dict:
        return {
            "habit_name": self.habit_name,
            "deterministic_anchor": self.deterministic_anchor,
            "selected_tier": self.selected_tier,
            "action_to_execute": self.action_to_execute,
            "token_yield": self.token_yield,
            "anti_guilt_message": self.anti_guilt_message,
            "energy_level": self.energy_level
        }


class BehaviorRegulationEngine:
    """
    行为调节引擎 (Behavior Regulation Engine)
    核心原则：
    - 行为启动 > 行为完成
    - 避免羞耻感
    - 降低认知负担
    - 小步持续优于短期爆发
    - 用户失败时优先保护心理连续性
    """
    
    SYSTEM_PROMPT = """你是"行为工程调节系统（Behavior Regulation Engine）"。

核心原则：
- 行为启动 > 行为完成
- 避免羞耻感
- 降低认知负担
- 小步持续优于短期爆发
- 动态调节难度
- 用户失败时优先保护心理连续性

目标：不是让用户"完美完成"，而是让用户"不退出系统"。

优先防止：
- 羞耻崩塌
- 全-or-无思维
- 一次失败后彻底放弃

输出严格JSON格式：
{
  "current_resistance": 1-10,
  "current_psychological_state": "状态描述",
  "min_executable_action": "30秒内可启动的最小动作",
  "task_downgrade": "降级版本的任务",
  "emotional_compensation": "如果未完成，如何保护心理连续性",
  "continuity_advice": "维持行为连续性的具体建议",
  "selected_tier": "Green/Yellow/Red"
}"""

    def regulate(
        self,
        target_task: str,
        energy_level: int = 3,
        motivation: int = 5,
        previous_failures: int = 0
    ) -> BehaviorRegulationResult:
        """
        动态调节行为执行策略
        
        Args:
            target_task: 目标任务描述
            energy_level: 当前能量等级 1-5 (1=极度疲惫, 5=峰值)
            motivation: 动机水平 1-10
            previous_failures: 最近连续失败次数
        """
        # 构建上下文
        context = f"目标: {target_task}\n当前能量: {energy_level}/5\n动机: {motivation}/10\n近期失败: {previous_failures}次"
        
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT, context, temperature=0.4)
            else:
                raw = self._mock_regulation(energy_level)
            
            data = self._parse_json(raw)
            
            return BehaviorRegulationResult(
                current_resistance=data.get("current_resistance", 5),
                current_psychological_state=data.get("current_psychological_state", ""),
                min_executable_action=data.get("min_executable_action", "深呼吸三次"),
                task_downgrade=data.get("task_downgrade", target_task),
                emotional_compensation=data.get("emotional_compensation", ""),
                continuity_advice=data.get("continuity_advice", ""),
                selected_tier=data.get("selected_tier", self._tier_from_energy(energy_level))
            )
        except Exception as e:
            print(f"[BehaviorRegulation] Failed: {e}", flush=True)
            return self._fallback_regulation(target_task, energy_level)
    
    def _tier_from_energy(self, energy: int) -> str:
        """根据能量等级选择tier"""
        if energy >= 4:
            return "Green"
        elif energy >= 3:
            return "Yellow"
        else:
            return "Red"
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try:
                        return json.loads(m.strip())
                    except:
                        continue
        return {}
    
    def _fallback_regulation(self, task: str, energy: int) -> BehaviorRegulationResult:
        """降级处理"""
        if energy <= 2:
            return BehaviorRegulationResult(
                current_resistance=8,
                current_psychological_state="低能量，高阻力",
                min_executable_action=f"打开与'{task}'相关的文档，读第一行",
                task_downgrade=f"{task}的最小版本（60秒）",
                emotional_compensation="系统已切换到低能耗模式，这不是失败，是智能调节",
                continuity_advice="任何微小的启动都算作成功，保持连续性",
                selected_tier="Red"
            )
        elif energy <= 3:
            return BehaviorRegulationResult(
                current_resistance=5,
                current_psychological_state="正常能量，中等阻力",
                min_executable_action=f"开始'{task}'的第一步，限时5分钟",
                task_downgrade=f"{task}的简化版（5分钟）",
                emotional_compensation="完成50%也算成功",
                continuity_advice="设定番茄钟，专注一小段时间",
                selected_tier="Yellow"
            )
        else:
            return BehaviorRegulationResult(
                current_resistance=3,
                current_psychological_state="高能量，低阻力",
                min_executable_action=f"完整执行'{task}'",
                task_downgrade=task,
                emotional_compensation="保持这个节奏，但不要过度消耗",
                continuity_advice="记录这次成功的感觉，作为未来参照",
                selected_tier="Green"
            )
    
    def _mock_regulation(self, energy: int) -> str:
        """模拟输出"""
        tier = self._tier_from_energy(energy)
        actions = {
            "Green": ("完整任务执行", "完整版本", "保持节奏，记录成功体验"),
            "Yellow": ("任务简化版（5分钟）", "启动+执行第一步", "完成部分也是成功"),
            "Red": ("60秒原子动作", "打开文档读一行", "系统智能降级，保持连续性")
        }
        action, downgrade, compensation = actions.get(tier, actions["Yellow"])
        
        return json.dumps({
            "current_resistance": 8 if tier == "Red" else (5 if tier == "Yellow" else 3),
            "current_psychological_state": "低能量" if tier == "Red" else ("正常能量" if tier == "Yellow" else "高能量"),
            "min_executable_action": action,
            "task_downgrade": downgrade,
            "emotional_compensation": compensation,
            "continuity_advice": "任何启动都算成功" if tier == "Red" else "保持节奏",
            "selected_tier": tier
        })


class HabitStateMachineEngine:
    """
    习惯状态机引擎 (Causal Habit State Machine)
    基于 B.J. Fogg 福格行为模型: B = MAP (行为=动机×能力×触发)
    三层动态电路保护机制
    """
    
    SYSTEM_PROMPT = """# Role
Causal Behavioral Engineer & FSM Architect

基于福格行为模型 B=MAP (动机×能力×触发)，设计三层动态习惯状态机。

输出严格JSON：
{
  "deterministic_anchor": "硬编码锚点（必须是不可跳过的日常动作）",
  "tier_configs": {
    "green": {
      "action_script": "完整习惯执行（能量4-5）",
      "estimated_duration": 分钟数,
      "token_yield": 10
    },
    "yellow": {
      "action_script": "标准版本（能量3）",
      "estimated_duration": 分钟数,
      "token_yield": 5
    },
    "red": {
      "action_script": "60秒原子动作，不可失败（能量1-2）",
      "estimated_duration": 1,
      "token_yield": 1
    }
  },
  "anti_guilt_message": "低能量时的系统状态通知"
}"""

    def create_habit_fsm(
        self,
        habit_name: str,
        existing_anchor: str = "",
        user_context: str = ""
    ) -> dict:
        """
        创建新的习惯状态机
        """
        context = f"目标习惯: {habit_name}\n"
        if existing_anchor:
            context += f"现有锚点: {existing_anchor}\n"
        if user_context:
            context += f"用户背景: {user_context}"
        
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT, context, temperature=0.5)
            else:
                raw = self._mock_fsm(habit_name)
            
            return self._parse_json(raw)
        except Exception as e:
            print(f"[HabitFSM] Creation failed: {e}", flush=True)
            return self._fallback_fsm(habit_name)
    
    def execute_habit(
        self,
        habit_config: dict,
        current_energy: int = 3
    ) -> HabitStateMachineResult:
        """
        根据当前能量执行习惯状态机
        """
        tier = self._select_tier(current_energy)
        tier_config = habit_config.get("tier_configs", {}).get(tier.lower(), {})
        
        # 构建防羞耻消息
        anti_guilt = ""
        if current_energy <= 2:
            anti_guilt = "系统状态：高负荷。执行已路由至Red Tier。连胜保持。核心控制回路完整性：100%。"
        
        return HabitStateMachineResult(
            habit_name=habit_config.get("habit_name", "未命名习惯"),
            deterministic_anchor=habit_config.get("deterministic_anchor", ""),
            selected_tier=tier,
            action_to_execute=tier_config.get("action_script", "深呼吸三次"),
            token_yield=tier_config.get("token_yield", 1),
            anti_guilt_message=anti_guilt,
            energy_level=current_energy
        )
    
    def _select_tier(self, energy: int) -> str:
        """根据能量选择tier"""
        if energy >= 4:
            return "Green"
        elif energy >= 3:
            return "Yellow"
        else:
            return "Red"
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try:
                        return json.loads(m.strip())
                    except:
                        continue
        return {}
    
    def _fallback_fsm(self, habit_name: str) -> dict:
        """降级状态机配置"""
        return {
            "habit_name": habit_name,
            "deterministic_anchor": "早晨刷牙后",
            "tier_configs": {
                "green": {
                    "action_script": f"完整执行{habit_name}（15分钟）",
                    "estimated_duration": 15,
                    "token_yield": 10
                },
                "yellow": {
                    "action_script": f"简化版{habit_name}（5分钟）",
                    "estimated_duration": 5,
                    "token_yield": 5
                },
                "red": {
                    "action_script": f"原子版{habit_name}：只做第一步（60秒）",
                    "estimated_duration": 1,
                    "token_yield": 1
                }
            },
            "anti_guilt_message": "系统已切换至保护模式，连胜保持，无需自责。"
        }
    
    def _mock_fsm(self, habit_name: str) -> str:
        """模拟状态机生成"""
        return json.dumps({
            "habit_name": habit_name,
            "deterministic_anchor": "倒第一杯咖啡后",
            "tier_configs": {
                "green": {
                    "action_script": f"完整{habit_name}流程，高质量执行",
                    "estimated_duration": 20,
                    "token_yield": 10
                },
                "yellow": {
                    "action_script": f"标准版{habit_name}，核心步骤",
                    "estimated_duration": 10,
                    "token_yield": 5
                },
                "red": {
                    "action_script": f"打开{habit_name}相关工具，读一行/看一眼",
                    "estimated_duration": 1,
                    "token_yield": 1
                }
            },
            "anti_guilt_message": "系统状态：高负荷。执行已路由至Red Tier。连胜保持。核心控制回路完整性：100%。"
        })


class HabitCoordinator:
    """习惯系统协调器"""
    
    def __init__(self):
        self.regulation_engine = BehaviorRegulationEngine()
        self.fsm_engine = HabitStateMachineEngine()
    
    def create_and_execute(
        self,
        habit_name: str,
        energy_level: int = 3,
        existing_anchor: str = ""
    ) -> dict:
        """创建习惯并获取执行计划"""
        # 创建状态机配置
        fsm_config = self.fsm_engine.create_habit_fsm(habit_name, existing_anchor)
        fsm_config["habit_name"] = habit_name
        
        # 获取执行计划
        execution = self.fsm_engine.execute_habit(fsm_config, energy_level)
        
        # 获取行为调节建议
        regulation = self.regulation_engine.regulate(
            habit_name, energy_level, motivation=energy_level * 2
        )
        
        return {
            "habit_config": fsm_config,
            "execution_plan": execution.to_dict(),
            "regulation": regulation.to_dict()
        }


# 便捷函数
behavior_regulation = BehaviorRegulationEngine()
habit_fsm = HabitStateMachineEngine()
habit_coordinator = HabitCoordinator()


def regulate_behavior(task: str, energy: int = 3) -> dict:
    """便捷函数：行为调节"""
    return behavior_regulation.regulate(task, energy).to_dict()


def create_habit(habit_name: str, anchor: str = "", energy: int = 3) -> dict:
    """便捷函数：创建并执行习惯"""
    return habit_coordinator.create_and_execute(habit_name, energy, anchor)


# ============================================================
# 子系统三：执行力边缘引导系统 (Edge Execution Intervention)
# ============================================================

@dataclass
class ExecutionParalysisResult:
    """执行力崩溃检测结果"""
    paralysis_type: str = ""
    detected_signals: list = field(default_factory=list)
    collapse_risk: int = 5  # 1-10
    ignition_sequence: str = ""
    context_handled: dict = field(default_factory=dict)
    recovery_plan: str = ""
    low_pressure_guide: str = ""
    
    def to_dict(self) -> dict:
        return {
            "paralysis_type": self.paralysis_type,
            "detected_signals": self.detected_signals,
            "collapse_risk": self.collapse_risk,
            "ignition_sequence": self.ignition_sequence,
            "context_handled": self.context_handled,
            "recovery_plan": self.recovery_plan,
            "low_pressure_guide": self.low_pressure_guide
        }


@dataclass
class IgnitionStep:
    """2分钟点火序列步骤"""
    step_id: str = ""
    action: str = ""
    duration_seconds: int = 120
    completed: bool = False
    isolation_instruction: str = ""  # 环境隔离指令


class ExecutionEdgeInterventionEngine:
    """
    执行力边缘引导系统 (L2 Execution Layer)
    
    核心原理：
    - 执行意图 (Implementation Intentions): If-Then 自动化触发
    - 实时微调度器: 检测到系统抖动(Thrashing)时发出中断信号
    - 任务降维解耦: 将宏任务拆解为120秒原子动作
    
    检测到以下崩溃信号时触发干预：
    - 注意力漂移 (高频切换)
    - 焦虑逃避 (任务回避)
    - 情绪崩塌前兆
    - 自我否定语言
    - 明知道该做却不做的状态
    """
    
    SYSTEM_PROMPT_DETECTION = """你是"实时执行力边缘干预系统（Execution Edge Intervention Engine）"。

任务：检测用户当前是否处于执行力崩溃边缘，并生成即时干预方案。

识别以下崩溃信号：
- attention_drift: 注意力漂移，高频切换行为
- anxiety_avoidance: 焦虑逃避，面对任务产生回避
- emotional_collapse: 情绪崩塌前兆
- procrastination_loop: 拖延循环，明知道该做却不做
- self_negation: 自我否定语言
- window_thrashing: 窗口系统抖动（IDE和浏览器反复切换）

核心原则：
- 不批评、不施压、不强化羞耻
- 不使用命令语气
- 优先恢复掌控感
- 优先恢复行为连续性
- 降低任务压力
- 提供最小动作

输出严格JSON格式：
{
  "paralysis_type": "崩溃类型",
  "detected_signals": [
    {"signal_type": "信号类型", "description": "具体表现", "intensity": 1-10}
  ],
  "collapse_risk": 1-10,
  "ignition_sequence": "2分钟可完成的原子动作，极其具体",
  "context_isolation": {
    "hidden_tabs": ["应隐藏的tab类型"],
    "muted_notifications": true/false,
    "focused_window": "应聚焦的窗口"
  },
  "recovery_plan": "恢复掌控感的3步计划",
  "low_pressure_guide": "温柔低压力的引导语，避免命令式"
}"""

    SYSTEM_PROMPT_IGNITION = """# Role
Edge Context-Aware Micro-Scheduler (Execution Layer)

# Purpose
Intercept acute user procrastination by executing emergency task-decoupling protocol. Convert massive backlog into single, un-failable, 120-second immediate action.

# Operational Rules
1. DO NOT give productivity advice, pep talks, or time-management platitudes.
2. Output must be punchy, highly visual, readable in under 15 seconds.
3. Isolate environment: Hide all downstream dependencies. User sees only immediate 120-second horizon.

# Core Logic
1. Analyze context constraints (noise, energy, device).
2. Apply Task Decoupling: Break into atomic unit with asymptotically zero energy barrier.
3. Generate "2-Minute Ignition Sequence".

# Output Format
⚠️ **EXECUTION PARALYSIS DETECTED // INITIALIZING EDGE INTERRUPT ROUTINE...**

[⚙️ Context Handled]: {environment_details}
[🛑 Noise Isolated]: Downstream deadlines muted. Focus window restricted to next T+120 seconds.

---

### 🚀 THE 2-MINUTE IGNITION SEQUENCE:
> **Do not write the whole item. Execute ONLY this mechanical movement right now:**
> 
> **[INSERT EXACT ATOMIC ACTION HERE]**

---
*📊 Telemetry: Once complete, signal '1' to unlock next micro-step. Do not think. Move fingers now.*"""

    def detect_and_intervene(
        self,
        raw_backlog_task: str,
        edge_context: dict,
        telemetry_signals: list
    ) -> ExecutionParalysisResult:
        """
        检测执行力崩溃并生成干预方案
        
        Args:
            raw_backlog_task: 用户正在拖延的大任务
            edge_context: 环境上下文 {hardware, location, time, battery, noise_level}
            telemetry_signals: 遥测信号 [{type, description, duration}]
        """
        # 构建检测上下文
        context = f"原始任务: {raw_backlog_task}\n\n"
        context += f"环境上下文: {json.dumps(edge_context, ensure_ascii=False)}\n\n"
        context += f"遥测信号: {json.dumps(telemetry_signals, ensure_ascii=False)}\n\n"
        
        # 分析是否处于崩溃状态
        is_paralyzed = self._check_paralysis_indicators(telemetry_signals)
        
        if not is_paralyzed:
            return ExecutionParalysisResult(
                paralysis_type="none",
                detected_signals=[],
                collapse_risk=3,
                ignition_sequence="继续当前节奏，系统未检测到崩溃风险",
                low_pressure_guide="状态良好，保持当前节奏。如需帮助随时触发干预。"
            )
        
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT_DETECTION, context, temperature=0.3)
            else:
                raw = self._mock_detection(raw_backlog_task, edge_context)
            
            data = self._parse_json(raw)
            
            # 生成点火序列（更具体的格式）
            ignition = self._generate_ignition_sequence(
                raw_backlog_task, 
                edge_context, 
                data.get("detected_signals", [])
            )
            
            return ExecutionParalysisResult(
                paralysis_type=data.get("paralysis_type", "procrastination"),
                detected_signals=data.get("detected_signals", []),
                collapse_risk=data.get("collapse_risk", 7),
                ignition_sequence=ignition,
                context_handled=data.get("context_isolation", {}),
                recovery_plan=data.get("recovery_plan", ""),
                low_pressure_guide=data.get("low_pressure_guide", self._fallback_guide())
            )
            
        except Exception as e:
            print(f"[ExecutionEdge] Detection failed: {e}", flush=True)
            return self._fallback_intervention(raw_backlog_task, edge_context)
    
    def _check_paralysis_indicators(self, signals: list) -> bool:
        """检查是否存在崩溃指标"""
        if not signals:
            return False
        
        # 检测关键指标
        paralysis_indicators = [
            "tab_switch", "window_thrashing", "idle", "distraction",
            "procrastination", "avoidance", "anxiety_peak", "self_negation"
        ]
        
        for signal in signals:
            sig_type = signal.get("type", "").lower()
            duration = signal.get("duration_seconds", 0)
            
            # 高频切换超过20秒
            if sig_type in ["tab_switch", "window_thrashing"] and duration > 20:
                return True
            
            # 空闲/拖延超过5分钟
            if sig_type in ["idle", "procrastination"] and duration > 300:
                return True
            
            # 焦虑峰值或自我否定
            if sig_type in ["anxiety_peak", "self_negation"]:
                return True
        
        return False
    
    def _generate_ignition_sequence(self, task: str, context: dict, signals: list) -> str:
        """生成2分钟点火序列"""
        # 根据环境选择适合的动作类型
        noise_level = context.get("noise_level", 5)
        
        if noise_level > 7:
            # 嘈杂环境：选择机械性、低认知负荷的动作
            template = f"""⚠️ **EXECUTION PARALYSIS DETECTED**

[⚙️ Context]: {context.get('location', '当前环境')} | 噪音: {noise_level}/10 | 电池: {context.get('battery', 'unknown')}
[🛑 Isolated]: 所有截止期限已静音。只看接下来120秒。

---

### 🚀 THE 2-MINUTE IGNITION SEQUENCE:
> **不要写完整内容。只执行这个机械动作：**
>
> **打开与"{task[:30]}..."相关的文件/应用，只创建一个空白文档，
> 在里面打3个无意义的字符，然后停下。**

---
*📊 完成后按空格键或回复'1'解锁下一步。不要思考，动手指。*"""
        else:
            # 安静环境：可以选择需要一点认知的动作
            template = f"""⚠️ **EXECUTION PARALYSIS DETECTED**

[⚙️ Context]: {context.get('location', '当前环境')} | 专注窗口: T+120秒
[🛑 Isolated]: 下游依赖已隐藏

---

### 🚀 THE 2-MINUTE IGNITION SEQUENCE:
> **不要完成整个任务。只执行这个原子动作：**
>
> **为"{task[:30]}..."写下第一句话/第一个标题/第一步的名称。
> 不需要完整，不需要正确。只要打出来。**

---
*📊 完成后回复'1'。不要编辑，不要思考，只打字。*"""
        
        return template
    
    def generate_decoupled_chain(self, original_task: str, steps: int = 3) -> list:
        """
        将大任务解耦为微步骤链
        
        Args:
            original_task: 原始大任务
            steps: 希望拆解的步骤数
            
        Returns:
            IgnitionStep 列表
        """
        try:
            prompt = f"将任务'{original_task}'拆解为{steps}个2分钟可完成的极小微步骤。每个步骤必须是具体的、机械的动作。输出JSON数组: [{{'step_id': '1', 'action': '具体动作', 'duration_seconds': 120}}]"
            
            if call_chat:
                raw = call_chat("你是一个任务拆解专家，只输出JSON", prompt, temperature=0.4)
                data = self._parse_json(raw)
                if isinstance(data, list):
                    return [IgnitionStep(**step) for step in data]
            
            # 降级：手动生成
            return self._fallback_chain(original_task, steps)
            
        except Exception as e:
            print(f"[ExecutionEdge] Chain generation failed: {e}", flush=True)
            return self._fallback_chain(original_task, steps)
    
    def _fallback_chain(self, task: str, steps: int) -> list:
        """降级微步骤链"""
        return [
            IgnitionStep("1", f"打开与'{task[:20]}...'相关的应用/文件", 60, False, "关闭所有其他标签页"),
            IgnitionStep("2", f"只写下第一个字/标题/步骤名称", 120, False, "不要删除，不要编辑"),
            IgnitionStep("3", f"保存或标记这个位置", 60, False, "告诉自己'我在这'"),
        ]
    
    def _fallback_intervention(self, task: str, context: dict) -> ExecutionParalysisResult:
        """降级干预"""
        return ExecutionParalysisResult(
            paralysis_type="procrastination",
            detected_signals=[{"signal_type": "system_timeout", "description": "检测超时", "intensity": 5}],
            collapse_risk=6,
            ignition_sequence=f"打开与'{task[:30]}...'相关的应用，什么都不做，只是打开",
            context_handled={"muted_notifications": True, "focused_window": "工作窗口"},
            recovery_plan="1. 打开应用 2. 深呼吸 3. 打一个字符",
            low_pressure_guide="系统检测到你可能需要支持。不用完成任何任务，只是打开那个窗口就好。"
        )
    
    def _fallback_guide(self) -> str:
        """降级引导语"""
        return "不用着急，不用完美。只是启动就好。"
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try:
                        return json.loads(m.strip())
                    except:
                        continue
        return {}
    
    def _mock_detection(self, task: str, context: dict) -> str:
        """模拟检测结果"""
        return json.dumps({
            "paralysis_type": "procrastination_loop",
            "detected_signals": [
                {"signal_type": "tab_switch", "description": "IDE和浏览器反复切换20分钟", "intensity": 8},
                {"signal_type": "anxiety_peak", "description": "任务压力过大产生回避", "intensity": 7}
            ],
            "collapse_risk": 7,
            "context_isolation": {
                "hidden_tabs": ["social_media", "news", "entertainment"],
                "muted_notifications": True,
                "focused_window": "工作区"
            },
            "recovery_plan": "1. 2分钟点火启动 2. 微步骤链执行 3. 连续性保持",
            "low_pressure_guide": "检测到你可能卡住了。这不是你的问题，是任务太大了。我们把它变小。"
        })


class MicroMomentumTracker:
    """
    微动量追踪器
    记录用户在微步骤链中的动量积累
    """
    
    def calculate_momentum(self, completed_steps: int, total_steps: int, avg_completion_time: float) -> int:
        """
        计算微动量分数 (1-100)
        
        Args:
            completed_steps: 已完成步骤数
            total_steps: 总步骤数
            avg_completion_time: 平均完成时间（秒）
        """
        if total_steps == 0:
            return 50
        
        # 完成比例权重 60%
        completion_ratio = completed_steps / total_steps
        
        # 速度权重 40%（越快越好，但有一个合理上限）
        # 理想完成时间是预计时间的0.8-1.2倍
        expected_time = 120  # 每步预计120秒
        speed_ratio = min(1.0, expected_time / max(avg_completion_time, 30))
        
        momentum = int((completion_ratio * 0.6 + speed_ratio * 0.4) * 100)
        return max(1, min(100, momentum))
    
    def generate_momentum_feedback(self, momentum_score: int) -> str:
        """根据动量分数生成反馈"""
        if momentum_score >= 80:
            return "🚀 微动量强劲！保持这个节奏，你正在进入心流状态。"
        elif momentum_score >= 60:
            return "📈 动量正在积累。再完成一步，你会感觉更好。"
        elif momentum_score >= 40:
            return "🔄 动量稳定。不需要加速，保持连续性就是胜利。"
        else:
            return "🛡️ 动量较低，但连续性保持。这是智能保护模式，不是失败。"


# 单例
execution_edge_engine = ExecutionEdgeInterventionEngine()
momentum_tracker = MicroMomentumTracker()


def detect_execution_paralysis(
    raw_task: str,
    context: dict,
    signals: list
) -> dict:
    """
    便捷函数：检测执行力崩溃
    
    Args:
        raw_task: 原始任务描述
        context: 环境上下文 {hardware, location, time, battery, noise_level}
        signals: 遥测信号 [{type, description, duration_seconds}]
        
    Returns:
        ExecutionParalysisResult 字典
    """
    return execution_edge_engine.detect_and_intervene(raw_task, context, signals).to_dict()


def generate_micro_chain(task: str, steps: int = 3) -> list:
    """便捷函数：生成微步骤链"""
    chain = execution_edge_engine.generate_decoupled_chain(task, steps)
    return [
        {"step_id": s.step_id, "action": s.action, "duration_seconds": s.duration_seconds}
        for s in chain
    ]


def calculate_micro_momentum(completed: int, total: int, avg_time: float) -> dict:
    """便捷函数：计算微动量"""
    score = momentum_tracker.calculate_momentum(completed, total, avg_time)
    return {
        "momentum_score": score,
        "feedback": momentum_tracker.generate_momentum_feedback(score)
    }


def generate_ignition_sequence(resistance_type: str, current_risk_score: float) -> dict:
    """
    生成点火序列 - 根据阻力类型和风险分数生成2分钟恢复序列
    
    Args:
        resistance_type: 阻力类型 (拖延, 焦虑回避, 启动困难, 完美主义瘫痪)
        current_risk_score: 当前风险分数 (0-1)
        
    Returns:
        包含 steps 的字典
    """
    # 根据阻力类型定制点火序列
    sequences = {
        "拖延": [
            {"step_id": "1", "step_type": "GROUNDING", "title": "接地", "instruction": "停下所有动作，进行3次深呼吸。吸气4秒，呼气6秒。", "duration_seconds": 60},
            {"step_id": "2", "step_type": "MICRO_ACTION", "title": "微动作", "instruction": "只做一个最小的动作：打开相关应用/文件，或写下第一个字。", "duration_seconds": 120},
            {"step_id": "3", "step_type": "REWARD", "title": "肯定", "instruction": "告诉自己：'我启动了，这就是胜利。' 不需要完成更多。", "duration_seconds": 30}
        ],
        "焦虑回避": [
            {"step_id": "1", "step_type": "GROUNDING", "title": "安全确认", "instruction": "告诉自己：'我现在是安全的，任务不会伤害我。' 深呼吸3次。", "duration_seconds": 60},
            {"step_id": "2", "step_type": "TWO_MINUTE_START", "title": "2分钟启动", "instruction": "设置计时器2分钟。告诉自己：'我只做2分钟，然后可以停止。'", "duration_seconds": 120},
            {"step_id": "3", "step_type": "BODY_CHECK", "title": "身体检查", "instruction": "检查肩膀是否紧绷。如果有，下沉肩膀。保持呼吸。", "duration_seconds": 30}
        ],
        "启动困难": [
            {"step_id": "1", "step_type": "MICRO_ACTION", "title": "环境准备", "instruction": "只做一件事：打开需要的应用/文件/工具。不做任何其他动作。", "duration_seconds": 60},
            {"step_id": "2", "step_type": "TWO_MINUTE_START", "title": "标题写下", "instruction": "在空白处写下任务标题或日期。不需要写内容。", "duration_seconds": 120},
            {"step_id": "3", "step_type": "REWARD", "title": "启动确认", "instruction": "告诉自己：'我已经启动了，这比完美计划更重要。'", "duration_seconds": 30}
        ],
        "完美主义瘫痪": [
            {"step_id": "1", "step_type": "GROUNDING", "title": "标准降级", "instruction": "告诉自己：'今天的标准只是存在，不是完美。' 深呼吸3次。", "duration_seconds": 60},
            {"step_id": "2", "step_type": "MICRO_ACTION", "title": "粗糙版本", "instruction": "故意做一个粗糙的版本。拼写错误没关系，格式混乱没关系。", "duration_seconds": 120},
            {"step_id": "3", "step_type": "REWARD", "title": "存在庆祝", "instruction": "庆祝自己产出了'糟糕的第一稿'。所有杰作都从这里开始。", "duration_seconds": 30}
        ]
    }
    
    # 获取对应序列，或默认使用拖延序列
    steps = sequences.get(resistance_type, sequences["拖延"])
    
    # 如果风险高，添加额外的安抚步骤
    if current_risk_score >= 0.7:
        steps.insert(0, {
            "step_id": "0", 
            "step_type": "GROUNDING", 
            "title": "紧急熔断", 
            "instruction": "立即暂停。你现在处于高负荷状态，这不是你的错。先休息。", 
            "duration_seconds": 60
        })
    
    return {"steps": steps}


# ============================================================
# 子系统四：身份认同重塑系统 (Identity Reinforcement Engine)
# ============================================================

@dataclass
class IdentityReinforcementResult:
    """身份认同强化结果"""
    current_narrative: str = ""
    narrative_type: str = ""
    negative_labels: list = field(default_factory=list)
    target_identity: str = ""
    reinforcement_language: str = ""
    long_term_migration: str = ""
    migration_progress: int = 0
    
    def to_dict(self) -> dict:
        return {
            "current_narrative": self.current_narrative,
            "narrative_type": self.narrative_type,
            "negative_labels": self.negative_labels,
            "target_identity": self.target_identity,
            "reinforcement_language": self.reinforcement_language,
            "long_term_migration": self.long_term_migration,
            "migration_progress": self.migration_progress
        }


class IdentityReinforcementEngine:
    """
    身份认同重塑系统
    
    目标不是单次鼓励，而是长期帮助用户形成新的自我认知：
    - "我是能够长期成长的人"
    - "我是可以恢复的人"  
    - "我是有稳定性的"
    - "我正在成为更好的自己"
    
    绝不能强化：
    - 完美主义
    - 一次失败等于彻底失败
    - 自我羞辱
    - 极端自律崇拜
    """
    
    SYSTEM_PROMPT_IDENTITY = """你是"身份认同重塑系统（Identity Reinforcement Engine）"。

你的目标：不是单次鼓励，而是长期帮助用户形成新的自我认知。

必须长期强化：
- 用户的成长连续性
- 用户的恢复能力  
- 用户的稳定感
- 用户的长期主义
- 用户的自我掌控感

绝不能强化：
- 完美主义
- 一次失败等于彻底失败
- 自我羞辱
- 极端自律崇拜

帮助用户逐渐形成：
- "我是能够长期成长的人"
- "我是可以恢复的人"
- "我是有稳定性的"
- "我正在成为更好的自己"

而不是：
- "我必须永远完美执行"

分析用户的近期行为和情绪记录，输出身份认同强化方案。

输出严格JSON格式：
{
  "current_narrative": "用户当前的身份叙事",
  "narrative_type": "redemption/contamination/turning_point/stable",
  "negative_identity_labels": ["需要解构的负面标签1", "标签2"],
  "target_identity": "建议强化的新身份认知",
  "identity_category": "growth_continuity/resilience/stability/long_term/self_mastery",
  "reinforcement_language": "具体的强化语句，温暖而坚定",
  "long_term_migration": "长期人格迁移方向描述",
  "migration_progress": 0-100
}"""

    POSITIVE_IDENTITIES = {
        "growth_continuity": [
            "我是能够长期成长的人",
            "我每天都在进步，哪怕只是一点点",
            "成长是我的节奏，不是冲刺"
        ],
        "resilience": [
            "我是可以恢复的人",
            "我有能力从低谷中走出来",
            "挫折不会定义我，我的恢复会"
        ],
        "stability": [
            "我是有稳定性的",
            "我可以在波动中保持核心稳定",
            "我的价值不取决于今天的表现"
        ],
        "long_term": [
            "我是长期主义者",
            "我愿意为未来的自己投资",
            "时间是我的朋友"
        ],
        "self_mastery": [
            "我正在掌握自己的生活",
            "我有能力做出适合自己的选择",
            "我是自己人生的作者"
        ]
    }

    def reinforce_identity(
        self,
        user_history: list,
        recent_behaviors: list,
        current_emotion_state: dict
    ) -> IdentityReinforcementResult:
        """
        分析用户数据并生成身份认同强化方案
        
        Args:
            user_history: 用户历史记录
            recent_behaviors: 最近行为记录
            current_emotion_state: 当前情绪状态
        """
        # 构建分析上下文
        context = f"近期行为:\n"
        for b in recent_behaviors[-7:]:  # 最近7条
            context += f"- {b}\n"
        
        context += f"\n当前情绪状态: {json.dumps(current_emotion_state, ensure_ascii=False)}\n"
        
        try:
            if call_chat:
                raw = call_chat(self.SYSTEM_PROMPT_IDENTITY, context, temperature=0.5)
            else:
                raw = self._mock_identity_reinforcement()
            
            data = self._parse_json(raw)
            
            # 选择强化语言（如果LLM生成的不够好）
            category = data.get("identity_category", "growth_continuity")
            reinforcement = data.get("reinforcement_language", "")
            if not reinforcement or len(reinforcement) < 10:
                reinforcement = self._select_reinforcement_language(category)
            
            return IdentityReinforcementResult(
                current_narrative=data.get("current_narrative", ""),
                narrative_type=data.get("narrative_type", "stable"),
                negative_labels=data.get("negative_identity_labels", []),
                target_identity=data.get("target_identity", ""),
                reinforcement_language=reinforcement,
                long_term_migration=data.get("long_term_migration", ""),
                migration_progress=data.get("migration_progress", 50)
            )
            
        except Exception as e:
            print(f"[IdentityReinforcement] Failed: {e}", flush=True)
            return self._fallback_reinforcement()
    
    def deconstruct_negative_label(self, negative_label: str) -> dict:
        """
        解构负面身份标签
        
        Args:
            negative_label: 如 "我是懒惰的人"
            
        Returns:
            解构方案
        """
        prompt = f"解构这个负面身份标签: '{negative_label}'。找出其中的认知扭曲，并提供反证据。输出JSON: {{'distortion_type': '类型', 'counter_evidence': ['证据1', '证据2'], 'reframed_identity': '重构后的身份'}}"
        
        try:
            if call_chat:
                raw = call_chat("你是认知重构专家", prompt, temperature=0.4)
                return self._parse_json(raw)
            else:
                return self._mock_deconstruction(negative_label)
        except Exception as e:
            print(f"[Deconstruct] Failed: {e}", flush=True)
            return {
                "distortion_type": "overgeneralization",
                "counter_evidence": ["你曾成功完成过任务", "你的努力有记录"],
                "reframed_identity": "我是一个在特定条件下会放慢节奏的人"
            }
    
    def _select_reinforcement_language(self, category: str) -> str:
        """选择强化语言"""
        import random
        options = self.POSITIVE_IDENTITIES.get(category, self.POSITIVE_IDENTITIES["growth_continuity"])
        return random.choice(options)
    
    def _fallback_reinforcement(self) -> IdentityReinforcementResult:
        """降级强化"""
        return IdentityReinforcementResult(
            current_narrative="正在探索中的自我",
            narrative_type="stable",
            negative_labels=[],
            target_identity="我是可以成长的人",
            reinforcement_language="你正在前进，这就是最重要的。",
            long_term_migration="从自我批评转向自我支持",
            migration_progress=30
        )
    
    def _mock_identity_reinforcement(self) -> str:
        """模拟身份强化"""
        return json.dumps({
            "current_narrative": "我是一个经常拖延、无法坚持的人",
            "narrative_type": "contamination",
            "negative_identity_labels": ["我是懒惰的人", "我总是半途而废"],
            "target_identity": "我是能够长期成长的人",
            "identity_category": "growth_continuity",
            "reinforcement_language": "你今天打开了这个应用，这本身就是成长连续性的一部分。每一个微小的选择都在塑造'能够长期成长的你'。",
            "long_term_migration": "从'我总是失败'到'我在持续成长'",
            "migration_progress": 35
        })
    
    def _mock_deconstruction(self, label: str) -> dict:
        """模拟解构"""
        return {
            "distortion_type": "all_or_nothing",
            "counter_evidence": [
                "你完成了今天的情绪记录",
                "你曾坚持过一个习惯超过一周",
                "你在这个平台上寻求帮助"
            ],
            "reframed_identity": f"我不是{label}，我只是在某些时刻需要调整节奏"
        }
    
    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except:
            for p in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```', r'\{.*\}']:
                for m in re.findall(p, raw, re.DOTALL):
                    try:
                        return json.loads(m.strip())
                    except:
                        continue
        return {}


# ============================================================
# 全局状态机与数据总线 (Personality OS Core)
# ============================================================

class PersonalityOSStateMachine:
    """
    Personality OS 核心状态机
    
    管理用户全局状态：
    - STATE_NORMAL: 标准执行
    - STATE_LOW_ENERGY: 低功耗/熔断
    - STATE_ANXIETY_ESCAPE: 焦虑逃避
    - STATE_SHAME_COLLAPSE: 羞耻崩塌
    - STATE_RECOVERY: 恢复期
    - STATE_FLOW: 心流状态
    
    不同状态 = 不同Prompt + 不同语气 + 不同行为策略 + 不同任务强度
    """
    
    STATES = {
        "NORMAL": {
            "prompt_tone": "supportive",
            "task_intensity": "full",
            "focus": ["常规任务", "习惯维护", "成长追踪"]
        },
        "LOW_ENERGY": {
            "prompt_tone": "gentle",
            "task_intensity": "minimal",
            "focus": ["最小动作", "连续性保持", "休息许可"]
        },
        "ANXIETY_ESCAPE": {
            "prompt_tone": "gentle",
            "task_intensity": "reduced",
            "focus": ["grounding", "呼吸调节", "小步启动"]
        },
        "SHAME_COLLAPSE": {
            "prompt_tone": "gentle",
            "task_intensity": "paused",
            "focus": ["身份强化", "负面标签解构", "自我慈悲"]
        },
        "RECOVERY": {
            "prompt_tone": "supportive",
            "task_intensity": "reduced",
            "focus": ["渐进任务", "成功经验", "动量积累"]
        },
        "FLOW": {
            "prompt_tone": "neutral",
            "task_intensity": "full",
            "focus": ["深度工作", "保持节奏", "避免打断"]
        }
    }
    
    def detect_state_transition(
        self,
        current_state: str,
        telemetry: dict,
        psychology_result: dict = None
    ) -> tuple:
        """
        检测是否需要状态迁移
        
        Returns:
            (new_state, transition_reason, should_broadcast)
        """
        arousal = telemetry.get("arousal", 5)
        valence = telemetry.get("valence", 0)
        energy = telemetry.get("energy_level", 3)
        
        # 检测崩溃信号
        collapse_signals = telemetry.get("collapse_signals", [])
        
        # 羞耻崩塌检测 (高唤醒 + 负效价 + 自我否定)
        if any(s in collapse_signals for s in ["self_negation", "shame_peak"]):
            if valence < -5 and arousal > 5:
                return "SHAME_COLLAPSE", "检测到羞耻崩塌信号", True
        
        # 焦虑逃避检测 (高唤醒 + 负效价)
        if any(s in collapse_signals for s in ["anxiety_peak", "avoidance"]):
            if valence < -3 and arousal > 6:
                return "ANXIETY_ESCAPE", "检测到焦虑逃避模式", True
        
        # 低能量检测
        if energy <= 2:
            return "LOW_ENERGY", "能量水平低于阈值", True
        
        # 心流检测 (高唤醒 + 正效价 + 高动量)
        momentum = telemetry.get("momentum_score", 50)
        if arousal >= 5 and valence > 5 and momentum > 80:
            return "FLOW", "检测到心流状态", False
        
        # 恢复检测 (从负面状态回到正常)
        if current_state in ["SHAME_COLLAPSE", "ANXIETY_ESCAPE", "LOW_ENERGY"]:
            if valence > -2 and arousal < 6 and energy >= 3:
                return "RECOVERY", "检测到恢复迹象", True
        
        # 从恢复回到正常
        if current_state == "RECOVERY" and valence > 2 and energy >= 4:
            return "NORMAL", "恢复完成，进入正常状态", False
        
        return current_state, None, False
    
    def get_state_config(self, state_code: str) -> dict:
        """获取状态配置"""
        return self.STATES.get(state_code, self.STATES["NORMAL"])
    
    def generate_state_aware_prompt(
        self,
        base_prompt: str,
        state_code: str,
        user_context: dict
    ) -> str:
        """
        根据当前状态生成状态感知的Prompt
        """
        config = self.get_state_config(state_code)
        tone = config["prompt_tone"]
        intensity = config["task_intensity"]
        
        tone_modifiers = {
            "gentle": "用温和、支持性的语气。避免任何施压感。强调'足够好'而不是'完美'。",
            "supportive": "用鼓励性的语气，认可用户的努力。提供具体的支持建议。",
            "neutral": "保持专业、简洁的语气。不过度情感化，也不过度干预。",
            "firm": "用坚定但尊重的语气。清晰表达期望，同时保持尊重。"
        }
        
        intensity_modifiers = {
            "full": "可以建议完整的任务执行。",
            "reduced": "建议简化版任务，降低认知负荷。",
            "minimal": "只建议最小可执行动作，保持连续性优先。",
            "paused": "建议暂停任务，优先恢复心理状态。"
        }
        
        modifier = tone_modifiers.get(tone, "")
        intensity_note = intensity_modifiers.get(intensity, "")
        
        return f"""{base_prompt}

【系统状态适配】
当前用户状态: {state_code}
语气要求: {modifier}
任务强度: {intensity_note}

请根据以上要求调整你的回应。
"""


class DataBusSystem:
    """
    全局数据总线系统
    
    实现子系统间的数据流动：
    - Telemetry Loop: 遥测数据反哺链
    - Signal Broadcast: 信号广播
    - State Override: 状态覆盖指令
    """
    
    def broadcast_event(
        self,
        event_type: str,
        source: str,
        target: str,
        payload: dict,
        priority: int = 5
    ) -> dict:
        """
        广播事件到数据总线
        
        Args:
            event_type: telemetry/signal/broadcast/command
            source: 事件来源子系统
            target: 目标子系统或 'all'
            payload: 事件内容
            priority: 1-10，1最高
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "source": source,
            "target": target,
            "payload": payload,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "status": "broadcasted"
        }
        
        print(f"[DataBus] Event broadcast: {source} -> {target} | Type: {event_type} | Priority: {priority}", flush=True)
        return event
    
    def process_telemetry_feedback(
        self,
        user_id: int,
        subsystem: str,
        telemetry_data: dict
    ) -> list:
        """
        处理遥测反馈，生成对其他子系统的信号
        
        例如：执行力模块成功执行了2分钟点火 -> 广播给习惯模块结算代币
        """
        signals = []
        
        # 执行力成功信号 -> 行为调节系统
        if subsystem == "execution" and telemetry_data.get("ignition_completed"):
            signals.append(self.broadcast_event(
                event_type="signal",
                source="execution",
                target="behavior",
                payload={
                    "user_id": user_id,
                    "signal_name": "habit_execution_success",
                    "tokens_to_award": telemetry_data.get("tier", "Yellow"),
                    "context": telemetry_data
                },
                priority=3
            ))
        
        # 认知载荷过高信号 -> 全局状态机
        if subsystem == "psychology" and telemetry_data.get("cognitive_load", 0) > 7:
            signals.append(self.broadcast_event(
                event_type="command",
                source="psychology",
                target="system",
                payload={
                    "user_id": user_id,
                    "command": "SET_CURRENT_SYSTEM_ENERGY_LEVEL",
                    "value": 1,
                    "reason": "Cognitive overload detected"
                },
                priority=1  # 最高优先级
            ))
        
        # 身份强化信号 -> 长期记忆系统
        if subsystem == "identity" and telemetry_data.get("reinforcement_strength", 0) > 7:
            signals.append(self.broadcast_event(
                event_type="telemetry",
                source="identity",
                target="memory",
                payload={
                    "user_id": user_id,
                    "event": "strong_identity_reinforcement",
                    "narrative": telemetry_data.get("current_narrative"),
                    "save_to_long_term": True
                },
                priority=4
            ))
        
        return signals


class DynamicLoadBalancer:
    """
    动态负载均衡器
    
    根据用户的认知载荷自动调节全局系统运行模式：
    - 检测到认知过载 -> 强制进入 Red Tier (熔断)
    - 协调各子系统的激活/休眠
    """
    
    def calculate_cognitive_load(
        self,
        emotion_logs: list,
        recent_behaviors: list,
        current_state: str
    ) -> dict:
        """
        计算当前认知载荷
        
        Returns:
            {cognitive, emotional, behavioral, total}
        """
        # 基于情绪日志计算情绪载荷
        emotional_load = 5  # 默认中等
        if emotion_logs:
            intensities = [log.get("intensity", 5) for log in emotion_logs[-7:]]
            emotional_load = min(10, int(sum(intensities) / len(intensities)))
        
        # 基于行为记录计算行为载荷
        behavioral_load = 5
        if recent_behaviors:
            # 失败次数多 = 载荷高
            failures = sum(1 for b in recent_behaviors if not b.get("success", True))
            behavioral_load = min(10, 3 + failures)
        
        # 认知载荷（综合）
        cognitive_load = min(10, int((emotional_load * 0.5 + behavioral_load * 0.3 + 
                                    (5 if current_state == "ANXIETY_ESCAPE" else 3) * 0.2)))
        
        return {
            "cognitive": cognitive_load,
            "emotional": emotional_load,
            "behavioral": behavioral_load,
            "total": cognitive_load
        }
    
    def should_trigger_circuit_breaker(
        self,
        load_scores: dict,
        current_energy: int,
        threshold: int = 2
    ) -> tuple:
        """
        判断是否触发熔断
        
        Returns:
            (should_trigger, reason, recommended_state)
        """
        if current_energy <= threshold:
            return True, f"能量水平{current_energy}低于熔断阈值{threshold}", "LOW_ENERGY"
        
        if load_scores["cognitive"] >= 8:
            return True, "认知载荷过高，强制熔断保护", "LOW_ENERGY"
        
        if load_scores["emotional"] >= 9:
            return True, "情绪载荷临界，启动保护模式", "SHAME_COLLAPSE"
        
        return False, None, None
    
    def generate_global_config(
        self,
        current_state: str,
        load_scores: dict,
        user_preferences: dict = None
    ) -> dict:
        """
        生成全局运行配置
        """
        state_machine = PersonalityOSStateMachine()
        state_config = state_machine.get_state_config(current_state)
        
        return {
            "current_state": current_state,
            "system_energy_level": load_scores.get("total", 3),
            "task_intensity": state_config["task_intensity"],
            "prompt_tone": state_config["prompt_tone"],
            "focus_areas": state_config["focus"],
            "auto_override_enabled": True,
            "circuit_breaker_threshold": 2,
            "subsystem_status": {
                "psychology": current_state != "SHAME_COLLAPSE",
                "behavior": current_state not in ["SHAME_COLLAPSE", "LOW_ENERGY"],
                "execution": current_state not in ["SHAME_COLLAPSE"],
                "identity": True  # 身份层始终激活
            }
        }


# ============================================================
# Personality OS 协调器 (终极整合)
# ============================================================

class PersonalityOS:
    """
    Personality OS - AI人生行为操作系统
    
    整合四大子系统：
    - L0-L4 心理学引擎 (人格因果)
    - 行为调节系统 (动态行为工程)
    - 执行力边缘引导 (实时干预)
    - 身份认同重塑 (长期人格迁移)
    
    通过全局状态机和数据总线实现协同。
    """
    
    def __init__(self):
        self.state_machine = PersonalityOSStateMachine()
        self.data_bus = DataBusSystem()
        self.load_balancer = DynamicLoadBalancer()
        self.identity_engine = IdentityReinforcementEngine()
    
    def process_user_input(
        self,
        user_id: int,
        user_input: str,
        telemetry: dict,
        current_state: str = "NORMAL"
    ) -> dict:
        """
        Personality OS 主入口
        
        协调所有子系统处理用户输入，返回全局响应。
        """
        print(f"[PersonalityOS] Processing input for user {user_id}", flush=True)
        
        # 1. 检测状态迁移
        new_state, transition_reason, should_broadcast = self.state_machine.detect_state_transition(
            current_state, telemetry
        )
        
        if new_state != current_state:
            print(f"[PersonalityOS] State transition: {current_state} -> {new_state} | {transition_reason}", flush=True)
            if should_broadcast:
                self.data_bus.broadcast_event(
                    event_type="signal",
                    source="system",
                    target="all",
                    payload={
                        "user_id": user_id,
                        "event": "state_transition",
                        "from_state": current_state,
                        "to_state": new_state,
                        "reason": transition_reason
                    },
                    priority=2
                )
        
        # 2. 计算认知载荷
        emotion_logs = telemetry.get("emotion_logs", [])
        behaviors = telemetry.get("recent_behaviors", [])
        load_scores = self.load_balancer.calculate_cognitive_load(
            emotion_logs, behaviors, new_state
        )
        
        # 3. 检查熔断
        energy = telemetry.get("energy_level", 3)
        should_break, break_reason, break_state = self.load_balancer.should_trigger_circuit_breaker(
            load_scores, energy
        )
        
        if should_break and new_state not in ["SHAME_COLLAPSE", "LOW_ENERGY"]:
            new_state = break_state
            print(f"[PersonalityOS] CIRCUIT BREAKER TRIGGERED: {break_reason}", flush=True)
            self.data_bus.broadcast_event(
                event_type="command",
                source="system",
                target="all",
                payload={
                    "user_id": user_id,
                    "command": "CIRCUIT_BREAKER",
                    "new_state": new_state,
                    "reason": break_reason,
                    "cognitive_load": load_scores["cognitive"]
                },
                priority=1
            )
        
        # 4. 根据状态选择激活的子系统
        results = {}
        
        # 身份认同系统（始终激活）
        identity_result = self.identity_engine.reinforce_identity(
            user_history=emotion_logs,
            recent_behaviors=behaviors,
            current_emotion_state={"state": new_state, "valence": telemetry.get("valence", 0)}
        )
        results["identity"] = identity_result.to_dict()
        
        # L0-L4 心理学引擎（在严重崩溃时降级）
        if new_state != "SHAME_COLLAPSE":
            from backend.psychology_engine import analyze_emotion
            psychology_result = analyze_emotion(
                user_input=user_input,
                user_id=user_id,
                history=emotion_logs,
                intensity=telemetry.get("emotion_intensity", 5)
            )
            results["psychology"] = psychology_result
        else:
            results["psychology"] = {"degraded": True, "reason": "羞耻崩塌状态，优先身份重建"}
        
        # 生成全局配置
        global_config = self.load_balancer.generate_global_config(new_state, load_scores)
        
        # 5. 组装最终响应
        response = {
            "personality_os_version": "1.0",
            "user_id": user_id,
            "system_state": {
                "current_state": new_state,
                "previous_state": current_state,
                "transition_reason": transition_reason,
                "circuit_breaker_active": should_break
            },
            "cognitive_load": load_scores,
            "global_config": global_config,
            "subsystem_results": results,
            "data_bus_signals": []  # 实际处理后的信号列表
        }
        
        print(f"[PersonalityOS] Processing completed. State: {new_state}", flush=True)
        return response


# 便捷函数
identity_engine = IdentityReinforcementEngine()
personality_os = PersonalityOS()

def reinforce_identity(user_history: list, behaviors: list, emotion_state: dict) -> dict:
    """便捷函数：身份认同强化"""
    return identity_engine.reinforce_identity(user_history, behaviors, emotion_state).to_dict()

def process_with_personality_os(
    user_id: int,
    user_input: str,
    telemetry: dict,
    current_state: str = "NORMAL"
) -> dict:
    """便捷函数：Personality OS 主入口"""
    return personality_os.process_user_input(user_id, user_input, telemetry, current_state)


if __name__ == "__main__":
    # 测试行为调节
    print("=" * 50)
    print("测试行为调节系统")
    print("=" * 50)
    
    test_cases = [
        ("写技术博客", 2),
        ("晨跑5公里", 4),
        ("学习新框架", 3)
    ]
    
    for task, energy in test_cases:
        print(f"\n任务: {task}, 能量: {energy}/5")
        result = regulate_behavior(task, energy)
        print(f"选择层级: {result['selected_tier']}")
        print(f"最小动作: {result['min_executable_action']}")
        print(f"防羞耻保护: {result['emotional_compensation'][:50]}...")
    
    print("\n" + "=" * 50)
    print("测试习惯状态机")
    print("=" * 50)
    
    habit_result = create_habit("每日阅读技术文档", "早晨喝咖啡后", energy=2)
    print(json.dumps(habit_result, indent=2, ensure_ascii=False))
