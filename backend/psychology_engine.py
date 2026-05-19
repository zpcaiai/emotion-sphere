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
