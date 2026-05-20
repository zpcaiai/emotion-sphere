#!/usr/bin/env python3
"""
Discernment Engine Module - DSS
Acts as an "inner mirror" rather than an oracle.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from datetime import datetime
import random


class SourceType(Enum):
    INNER_WISDOM = "inner_wisdom"    # 内在智慧/本心
    CONSCIENCE = "conscience"        # 良心/理性
    FEAR = "fear"                    # 恐惧反应
    PRIDE = "pride"                  # 骄傲反应
    TRAUMA = "trauma"                # 创伤反应
    SOCIAL_PRESSURE = "social_pressure"  # 社会压力
    IMPULSE = "impulse"              # 冲动/欲望
    MIXED = "mixed"                  # 混合动机
    UNCERTAIN = "uncertain"          # 方向不明


class ConfidenceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"


@dataclass
class EmotionalState:
    emotions: List[Dict[str, Any]]
    stress_level: int
    anxiety_level: int
    fatigue_level: int
    spiritual_dryness: int  # kept for compatibility but renamed in UI to "inner_depletion"
    emotional_stability: int


@dataclass
class MotiveProfile:
    fear_driven_score: float
    pride_driven_score: float
    love_driven_score: float
    desire_driven_score: float
    duty_driven_score: float = 0.0
    ambition_driven_score: float = 0.0


@dataclass
class WisdomPrinciple:
    id: str
    principle_text: str
    reference: str
    category: str
    relevance_score: float


@dataclass
class DecisionEvent:
    id: str
    user_id: str
    title: str
    description: str
    category: str
    urgency_level: int
    importance_level: int
    created_at: datetime


@dataclass
class DiscernmentResult:
    primary_source: SourceType
    secondary_source: Optional[SourceType]
    confidence_level: ConfidenceLevel
    confidence_score: float
    primary_explanation: str
    alternative_interpretations: List[str]
    humility_statement: str
    risk_level: RiskLevel
    risk_factors: List[Dict[str, str]]
    recommended_reflections: List[str]
    suggested_questions: List[str]
    suggested_timeline: str
    supporting_principles: List[WisdomPrinciple]
    analysis_version: str = "1.0.0"
    generated_at: datetime = field(default_factory=datetime.utcnow)
    disclaimer: str = "本分析仅供参考，不构成权威指导。"


class DiscernmentEngine:
    """Inner discernment engine - acts as a mirror, not an oracle."""
    
    def __init__(self, version: str = "1.0.0"):
        self.version = version
    
    def discern(
        self,
        decision: DecisionEvent,
        emotional_state: EmotionalState,
        motive_profile: MotiveProfile,
        wisdom_principles: List[WisdomPrinciple],
        past_cases: Optional[List] = None,
    ) -> DiscernmentResult:
        """Main discernment method."""
        
        # Calculate source scores
        scores = self._calculate_scores(emotional_state, motive_profile)
        
        # Determine sources
        primary, secondary, confidence = self._determine_sources(scores, emotional_state)
        
        # Map confidence
        conf_level = self._map_confidence(confidence)
        
        # Generate outputs
        explanation = self._generate_explanation(primary, secondary, motive_profile)
        alternatives = self._generate_alternatives(primary)
        humility = self._generate_humility(conf_level)
        risk_level, risks = self._assess_risks(emotional_state, primary, decision)
        reflections, questions, timeline = self._generate_steps(primary, risk_level)
        
        return DiscernmentResult(
            primary_source=primary,
            secondary_source=secondary,
            confidence_level=conf_level,
            confidence_score=confidence,
            primary_explanation=explanation,
            alternative_interpretations=alternatives,
            humility_statement=humility,
            risk_level=risk_level,
            risk_factors=risks,
            recommended_reflections=reflections,
            suggested_questions=questions,
            suggested_timeline=timeline,
            supporting_principles=wisdom_principles[:5],
        )
    
    def _calculate_scores(self, state: EmotionalState, motive: MotiveProfile) -> Dict[SourceType, float]:
        """Calculate alignment scores for each source type."""
        scores = {}
        
        # Inner Wisdom: love, peace, stability
        iw_score = (
            motive.love_driven_score * 0.8 +
            (state.emotional_stability / 10) * 0.4 +
            (1 - state.anxiety_level / 10) * 0.3
        )
        scores[SourceType.INNER_WISDOM] = min(1.0, iw_score)
        
        # Fear: fear motive + anxiety + stress
        fear_score = (
            motive.fear_driven_score * 0.9 +
            (state.anxiety_level / 10) * 0.8 +
            (state.stress_level / 10) * 0.6
        )
        scores[SourceType.FEAR] = min(1.0, fear_score)
        
        # Pride: pride motive + instability
        pride_score = (
            motive.pride_driven_score * 0.9 +
            (1 - state.emotional_stability / 10) * 0.4
        )
        scores[SourceType.PRIDE] = min(1.0, pride_score)
        
        # Trauma: fear + inner depletion + instability
        trauma_score = (
            motive.fear_driven_score * 0.5 +
            (state.spiritual_dryness / 10) * 0.7 +
            (1 - state.emotional_stability / 10) * 0.6
        )
        scores[SourceType.TRAUMA] = min(1.0, trauma_score)
        
        # Social pressure: desire + ambition
        social_score = (
            motive.desire_driven_score * 0.7 +
            motive.ambition_driven_score * 0.6
        )
        scores[SourceType.SOCIAL_PRESSURE] = min(1.0, social_score)
        
        # Impulse: desire + fatigue
        impulse_score = (
            motive.desire_driven_score * 0.8 +
            (state.fatigue_level / 10) * 0.4
        )
        scores[SourceType.IMPULSE] = min(1.0, impulse_score)
        
        # Conscience: duty + stability
        conscience_score = (
            motive.duty_driven_score * 0.7 +
            (state.emotional_stability / 10) * 0.4
        )
        scores[SourceType.CONSCIENCE] = min(1.0, conscience_score)
        
        return scores
    
    def _determine_sources(
        self,
        scores: Dict[SourceType, float],
        state: EmotionalState
    ) -> Tuple[SourceType, Optional[SourceType], float]:
        """Determine primary and secondary sources."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        primary = sorted_scores[0][0]
        primary_score = sorted_scores[0][1]
        
        secondary = None
        if len(sorted_scores) >= 2:
            gap = primary_score - sorted_scores[1][1]
            if gap < 0.15:
                secondary = sorted_scores[1][0]
        
        # Low score = uncertain
        if primary_score < 0.3:
            return SourceType.UNCERTAIN, None, primary_score
        
        # Mixed signals
        if primary_score < 0.5 and secondary and sorted_scores[1][1] > 0.35:
            return SourceType.MIXED, None, primary_score
        
        # Adjust for stability
        stability_factor = state.emotional_stability / 10.0
        adjusted = primary_score * (0.7 + 0.3 * stability_factor)
        
        return primary, secondary, min(1.0, adjusted)
    
    def _map_confidence(self, score: float) -> ConfidenceLevel:
        if score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW
    
    def _generate_explanation(
        self,
        primary: SourceType,
        secondary: Optional[SourceType],
        motive: MotiveProfile
    ) -> str:
        """Generate reflective explanation."""
        
        explanations = {
            SourceType.INNER_WISDOM: [
                "从动机分析来看，决策展现出较高的爱与平静导向。情绪相对稳定，这与内在智慧的特征相符。但这仍需你在静思中亲自确认。",
                "这个方向似乎与爱的原则一致，长期结果预测积极。不过，任何感受都需要在时间、行动和反馈中验证。",
            ],
            SourceType.FEAR: [
                f"动机分析显示，恐惧因素占有较大比重（{motive.fear_driven_score:.0%}）。这很常见，人在不确定时自然寻求安全。",
                '这个决定很大程度上受"避免损失"的心理驱动。这种动机本身并非错误，但可能限制看见其他可能性的视野。',
                "情绪状态显示焦虑较高，这可能影响判断清晰度。或许值得先处理焦虑，再看这个决定是否依然合适。",
            ],
            SourceType.PRIDE: [
                "动机分析显示出对外在认可的一定需求。这是很普遍的人性弱点，无需自责，但值得觉察。",
                "这个决定似乎与维护某种形象有关。这种动机往往带来短期满足，但长期可能导致疲惫。",
                '坦诚面对"被人如何看待"的影响，或许能帮助您做出更真实的选择。',
            ],
            SourceType.TRAUMA: [
                "内心状态显示一定程度的枯竭，情绪也较为波动。这种状态下做出的决定，可能受过去未愈伤痛的影响。",
                "情绪反应强度似乎与当下情境不完全匹配。这可能是过往经历被触发的信号。",
            ],
            SourceType.SOCIAL_PRESSURE: [
                "决策似乎较多考虑社会标准或物质回报。这些考量很实际，但可能掩盖更深层的价值。",
                "问问自己：这是你内心真正想要的，还是社会告诉你应该想要的？",
            ],
            SourceType.IMPULSE: [
                "决策与即时满足或欲望有较强关联。冲动的声音往往很急迫，但不代表正确。",
                "问问自己：如果没有任何舒适考量，我会怎么选？",
            ],
            SourceType.CONSCIENCE: [
                "这个决定似乎基于责任感或道德考虑。这是一种成熟的价值导向。",
                "但也要注意：过度的责任驱动可能导致自我牺牲，失去平衡。",
            ],
            SourceType.MIXED: [
                "动机分析显示出复杂的混合——既有值得肯定的面向，也有需要警觉的因素。这种复杂性是人性常态。",
                "没有单一主导动机，这种情况更需要谨慎和时间的检验。",
            ],
            SourceType.UNCERTAIN: [
                "基于当前信息，难以对来源做出有信心的判断。这并非坏事，不确定性本身就是分辨过程的一部分。",
                '不确定性邀请更深的寻求。与其匆忙结论，不如拥抱"尚未清楚"的状态。',
            ],
        }
        
        exp = random.choice(explanations.get(primary, ["分析正在进行..."]))
        
        if secondary:
            secondary_names = {
                SourceType.FEAR: "恐惧因素",
                SourceType.PRIDE: "骄傲因素",
                SourceType.INNER_WISDOM: "内在智慧",
                SourceType.SOCIAL_PRESSURE: "社会压力",
                SourceType.TRAUMA: "创伤反应",
                SourceType.IMPULSE: "冲动欲望",
                SourceType.CONSCIENCE: "良心/理性",
            }
            sec_name = secondary_names.get(secondary, secondary.value)
            exp += f"\n\n同时，{sec_name}也可能在影响这个决定。"
        
        return exp
    
    def _generate_alternatives(self, primary: SourceType) -> List[str]:
        """Generate alternative interpretations."""
        alts = {
            SourceType.FEAR: [
                "另一种可能：这不是危险信号，而是成长的邀请。恐惧可能是需要跨越的边界。",
                "也值得考虑：如果完全不怕，您会如何选择？恐惧有时是价值重估的信号。",
            ],
            SourceType.PRIDE: [
                "另一种视角：对成就的追求也可能是你赋予自己的使命感和责任心。",
                '追求优秀本身并非错，关键是对"谁得荣耀"的觉察。',
            ],
            SourceType.INNER_WISDOM: [
                '但也要小心：有时"爱"的动机可能掩盖了边界问题。',
                "另一个角度：爱驱动的决定也需要智慧执行，否则可能好心办坏事。",
            ],
            SourceType.TRAUMA: [
                "但也可以理解为：过往经历给了您独特的洞察力。",
                "另一个可能：这次情况与过去不同，您的警觉可能过度了。",
            ],
            SourceType.SOCIAL_PRESSURE: [
                "另一种视角：考虑社会因素是成熟的表现，平衡个人与社会需求。",
                "也值得考虑：如果完全不在乎他人看法，这个决定是否依然成立？",
            ],
            SourceType.IMPULSE: [
                "另一个角度：直觉有时比理性更快捕捉真实需求。",
                "但也要小心：冲动的决定往往带来短期满足，长期后悔。",
            ],
            SourceType.CONSCIENCE: [
                '但也要觉察："良心"有时被内疚感或应该思维污染。',
                "另一个视角：听从内心的同时，也要考虑现实后果。",
            ],
        }
        
        general = [
            "从另一角度看：这个决定的时机是否合适？或许需要更多准备。",
            '也可以理解为：这不是"对vs错"，而是"好vs更好"的排序。',
            "值得考虑：如果5年后回头看，现在的顾虑还重要吗？",
            "另一个视角：重要的是你如何做决定，而非决定本身。",
        ]
        
        result = alts.get(primary, [])
        result.extend(random.sample(general, 2))
        return result[:3]
    
    def _generate_humility(self, confidence: ConfidenceLevel) -> str:
        humility = {
            ConfidenceLevel.HIGH: [
                "分析显示了相对清晰的方向，但这只是基于有限信息的推断。真正的确据需要来自你的内在智慧、静思中的平静，以及信任群体的印证。",
            ],
            ConfidenceLevel.MEDIUM: [
                "目前的信号是混合的，没有单一来源明确主导。其他解释也合理存在，值得同等认真考虑。",
            ],
            ConfidenceLevel.LOW: [
                "基于当前信息，难以做出有信心的判断。不确定性本身就是分辨过程的一部分，等待和寻求可能比匆忙决定更明智。",
            ],
        }
        return random.choice(humility.get(confidence, humility[ConfidenceLevel.LOW]))
    
    def _assess_risks(
        self,
        state: EmotionalState,
        primary: SourceType,
        decision: DecisionEvent
    ) -> Tuple[RiskLevel, List[Dict[str, str]]]:
        """Assess decision risks."""
        risks = []
        score = 0
        
        if state.stress_level >= 7:
            risks.append({
                "factor": "高压力状态",
                "message": "当前压力水平较高，可能影响判断的客观性。",
                "recommendation": "考虑推迟重大决定，或先建立压力管理机制。",
            })
            score += 2
        
        if state.anxiety_level >= 7:
            risks.append({
                "factor": "高焦虑状态",
                "message": "焦虑水平显著升高，决策可能过度聚焦于风险规避。",
                "recommendation": "在焦虑平复前，避免做出不可逆的决定。",
            })
            score += 2
        
        if state.spiritual_dryness >= 6:
            risks.append({
                "factor": "内心枯竭",
                "message": "内在状态显示一定枯竭，可能导致依赖感觉而非平静。",
                "recommendation": "重建基本冥想/静思习惯可能比做这个决定更紧迫。",
            })
            score += 1
        
        if state.emotional_stability < 4:
            risks.append({
                "factor": "情绪不稳定",
                "message": "情绪稳定性较低，决策可能受近期情绪波动的不当影响。",
                "recommendation": "建议等待情绪平复，或寻求辅导支持。",
            })
            score += 1
        
        if primary in [SourceType.FEAR, SourceType.TRAUMA]:
            risks.append({
                "factor": "恐惧/创伤驱动",
                "message": "恐惧驱动的决定往往过度保守，可能错失成长机会。",
                "recommendation": "列出如果不害怕，您会怎么选择，比较两个选项。",
            })
            score += 1
        
        if primary == SourceType.SOCIAL_PRESSURE:
            risks.append({
                "factor": "社会压力驱动",
                "message": "过度考虑他人看法可能导致违背内心真实需求。",
                "recommendation": "区分合理的社会责任与过度在意他人评价。",
            })
            score += 1
        
        if primary == SourceType.IMPULSE:
            risks.append({
                "factor": "冲动欲望驱动",
                "message": "即时满足导向的决策往往忽视长期后果。",
                "recommendation": "设置72小时冷静期，观察欲望强度是否变化。",
            })
            score += 2
        
        if primary == SourceType.CONSCIENCE:
            risks.append({
                "factor": "过度责任驱动",
                "message": "基于道德/责任的决定可能导致自我牺牲过度。",
                "recommendation": "检查是否忽视了自己的合理需求，寻求平衡点。",
            })
        
        if primary == SourceType.INNER_WISDOM:
            risks.append({
                "factor": "确认偏误风险",
                "message": "即使是内在智慧驱动的决定，也可能存在盲点或一厢情愿。",
                "recommendation": "寻求至少一位信任的人印证，并准备面对可能的反对。",
            })
        
        if primary == SourceType.PRIDE:
            risks.append({
                "factor": "骄傲驱动风险",
                "message": "为维护形象或证明自己而做出的决定，往往忽视真实需求。",
                "recommendation": "问问自己：如果无人知道我的选择，我还会这样做吗？",
            })
            score += 1
        
        if decision.importance_level >= 4 and primary == SourceType.UNCERTAIN:
            risks.append({
                "factor": "重要但方向不明",
                "message": "这是重要决定，但目前方向尚不清晰。",
                "recommendation": "考虑推迟决定，或缩小决策范围。",
            })
            score += 1
        
        if score >= 5:
            return RiskLevel.HIGH, risks
        elif score >= 3:
            return RiskLevel.ELEVATED, risks
        elif score >= 1:
            return RiskLevel.MODERATE, risks
        return RiskLevel.LOW, risks
    
    def _generate_steps(
        self,
        primary: SourceType,
        risk: RiskLevel
    ) -> Tuple[List[str], List[str], str]:
        """Generate non-directive next steps."""
        reflections = [
            "给自己24-48小时，期间不做任何相关决定，观察内心变化。",
            "写下这个决定最好和最坏的结果，评估自己是否都能承受。",
            "与一位您最尊重的导师或朋友分享这个分析，听听他们的观察。",
            '在静思中，不是求"同意"你的决定，而是求显出你看不见的角度。',
        ]
        
        if primary == SourceType.FEAR:
            reflections.append("写下您最害怕的具体是什么。恐惧往往在真理的光中消散。")
        elif primary == SourceType.PRIDE:
            reflections.append('练习说出"我不知道"和"我需要帮助"，打破自我证明的循环。')
        elif primary == SourceType.INNER_WISDOM:
            reflections.append("记录这个感受的来源和特征，便于日后回顾验证。")
            reflections.append("与一位你信任的导师或朋友分享，寻求外在的印证。")
        elif primary == SourceType.UNCERTAIN:
            reflections.append('不要急于"制造"确定性。拥抱"尚未清楚"也是一种智慧。')
        elif primary == SourceType.SOCIAL_PRESSURE:
            reflections.append("列出做这个决定的3个真正内在动机，与外在认可无关的。")
        elif primary == SourceType.IMPULSE:
            reflections.append("给自己72小时冷静期，观察欲望是否依然强烈。")
        elif primary == SourceType.CONSCIENCE:
            reflections.append("检查是否过度牺牲自己的需求，健康的责任需要平衡。")
        elif primary == SourceType.TRAUMA:
            reflections.append("寻求专业支持或与信任的人分享，创伤反应需要被倾听。")
        
        if risk in [RiskLevel.ELEVATED, RiskLevel.HIGH]:
            reflections.append("由于当前风险因素，建议优先考虑情绪/心理健康，而非急于做决定。")
        
        questions = [
            "如果10年后的自己回看今天，会希望现在的我怎么选择？",
            "我能否完全坦诚这个决定的动机？",
            "如果我完全不需要考虑他人怎么看，我会怎么选？",
            "这个决定会让我的心更平静，还是更焦虑？",
        ]
        
        if risk == RiskLevel.HIGH or primary in [SourceType.FEAR, SourceType.TRAUMA]:
            timeline = "强烈建议等待24-72小时，待情绪平复后再重新评估。"
        else:
            timeline = "可以较快决定，但仍建议与至少一位信任的人分享您的想法。"
        
        return reflections[:3], questions, timeline


def format_result(result: DiscernmentResult) -> Dict[str, Any]:
    """Format for API response."""
    names = {
        SourceType.INNER_WISDOM: "内在智慧",
        SourceType.CONSCIENCE: "良心/理性",
        SourceType.FEAR: "恐惧反应",
        SourceType.PRIDE: "骄傲反应",
        SourceType.TRAUMA: "创伤反应",
        SourceType.SOCIAL_PRESSURE: "社会压力",
        SourceType.IMPULSE: "冲动欲望",
        SourceType.MIXED: "混合动机",
        SourceType.UNCERTAIN: "方向不明",
    }
    
    return {
        "source": {
            "primary": {"type": result.primary_source.value, "name": names.get(result.primary_source)},
            "secondary": {"type": result.secondary_source.value, "name": names.get(result.secondary_source)} if result.secondary_source else None,
            "confidence": result.confidence_level.value,
            "score": round(result.confidence_score, 2),
        },
        "explanation": result.primary_explanation,
        "alternatives": result.alternative_interpretations,
        "humility": result.humility_statement,
        "risk": {
            "level": result.risk_level.value,
            "factors": result.risk_factors,
        },
        "next_steps": {
            "reflections": result.recommended_reflections,
            "questions": result.suggested_questions,
            "timeline": result.suggested_timeline,
        },
        "principles": [
            {"text": p.principle_text, "reference": p.reference}
            for p in result.supporting_principles
        ],
        "disclaimer": result.disclaimer,
    }
