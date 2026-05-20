"""
persona_tag_engine.py — 用户人格画像标签系统
标签抽取、存储、聚合引擎
"""
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# ── 预定义标签库（系统标签）──────────────────────────────────

SYSTEM_TAG_LIBRARY = [
    # 情绪标签
    {"name": "焦虑", "category": "emotion", "keywords": ["焦虑", "紧张", "担心", "不安", "惶恐", "恐慌", "烦躁", "忐忑", "坐卧不安", "心神不宁"], "description": "对未来不确定性的过度担忧"},
    {"name": "平静", "category": "emotion", "keywords": ["平静", "安宁", "平和", "宁静", "安详", "淡定", "从容", "放松", "安稳", "内心安定"], "description": "情绪稳定和内心安宁"},
    {"name": "愤怒", "category": "emotion", "keywords": ["愤怒", "生气", "恼火", "暴怒", "气愤", "愤慨", "怒气", "怨恨", "恼怒", "火大"], "description": "对威胁或不公正的强烈反应"},
    {"name": "喜悦", "category": "emotion", "keywords": ["开心", "高兴", "快乐", "喜悦", "兴奋", "愉快", "满足", "幸福", "欣喜", "欢欣"], "description": "积极愉悦的情绪体验"},
    {"name": "悲伤", "category": "emotion", "keywords": ["悲伤", "难过", "失落", "沮丧", "抑郁", "绝望", "痛苦", "伤心", "哀伤", "难过"], "description": "失去或失望的低落情绪"},
    {"name": "恐惧", "category": "emotion", "keywords": ["害怕", "恐惧", "畏惧", "惊恐", "惧怕", "怯懦", "战战兢兢", "害怕", "恐惧", "担忧"], "description": "对危险或威胁的回避反应"},
    {"name": "孤独", "category": "emotion", "keywords": ["孤独", "寂寞", "孤单", "被抛弃", "无人理解", "隔绝", "疏离", "空虚", "无依无靠"], "description": "社交连接缺失的感受"},
    {"name": "希望", "category": "emotion", "keywords": ["希望", "期待", "盼望", "憧憬", "向往", "渴望", "期待", "憧憬", "信心", "乐观"], "description": "对未来的积极期待"},
    {"name": "感恩", "category": "emotion", "keywords": ["感恩", "感激", "感谢", "珍惜", "知足", "欣慰", "感恩", "感动", "感激", "谢恩"], "description": "对他人或生活的感谢与珍惜"},
    {"name": "内疚", "category": "emotion", "keywords": ["内疚", "自责", "后悔", "愧疚", "惭愧", "负罪感", "懊悔", "对不起", "抱歉", "自责"], "description": "认为自己做错事的自我批评"},

    # 行为标签
    {"name": "拖延", "category": "behavior", "keywords": ["拖延", "拖延症", "逃避", "推迟", "磨蹭", "懒散", "逃避", "畏难", "不想做", "拖到最后"], "description": "明知应做却推迟行动的行为模式"},
    {"name": "专注", "category": "behavior", "keywords": ["专注", "集中", "沉浸", "心流", "全神贯注", "投入", "聚焦", "专心致志", "一心一意"], "description": "高度集中注意力于当前任务"},
    {"name": "逃避", "category": "behavior", "keywords": ["逃避", "回避", "退缩", "躲闪", "逃离", "不想面对", "躲着", "回避", "绕开", "避开"], "description": "面对困难时的回避反应"},
    {"name": "冲动", "category": "behavior", "keywords": ["冲动", "冲动行为", "不经思考", "鲁莽", "急躁", "突然", "情绪化", "一时冲动", "控制不住"], "description": "缺乏事前思考的行为反应"},
    {"name": "坚持", "category": "behavior", "keywords": ["坚持", "持之以恒", "毅力", "不放弃", "坚韧", "持续", "坚守", "锲而不舍", "咬牙"], "description": "持续努力不轻易放弃"},
    {"name": "完美主义", "category": "behavior", "keywords": ["完美主义", "苛求", "高标准", "挑剔", "精益求精", "吹毛求疵", "不能容忍", "尽善尽美"], "description": "对自我和他人设定过高标准"},
    {"name": "自我批评", "category": "behavior", "keywords": ["自我批评", "自我否定", "自我怀疑", "自卑", "看不起自己", "贬低自己", "觉得自己差", "不够好"], "description": "过度负面的自我评价"},
    {"name": "过度思考", "category": "behavior", "keywords": ["过度思考", "想太多", "反复想", "纠结", "钻牛角尖", "反复分析", "不停想", "控制不住想"], "description": "对问题反复思考难以停止"},
    {"name": "冲动消费", "category": "behavior", "keywords": ["冲动消费", "乱买", "控制不住买", "剁手", "购物狂", "想买就买", "控制不住花钱"], "description": "缺乏节制的消费行为"},

    # 性格标签
    {"name": "内向", "category": "personality", "keywords": ["内向", "害羞", "安静", "独处", "不善言辞", "沉默", "不喜欢社交", "宅", "安静"], "description": "倾向于从独处中获得能量"},
    {"name": "外向", "category": "personality", "keywords": ["外向", "开朗", "活泼", "健谈", "喜欢社交", "热情", "活跃", "合群", "爱交际"], "description": "倾向于从社交中获得能量"},
    {"name": "敏感", "category": "personality", "keywords": ["敏感", "细腻", "多愁善感", "脆弱", "玻璃心", "在意", "容易受伤", "敏感脆弱"], "description": "对外界刺激和他人评价高度敏感"},
    {"name": "坚韧", "category": "personality", "keywords": ["坚韧", "坚强", "抗压", "不屈不挠", "顽强", "刚毅", "百折不挠", "勇敢", "坚强"], "description": "面对逆境的恢复力和持久力"},
    {"name": "乐观", "category": "personality", "keywords": ["乐观", "积极向上", "阳光", "正能量", "豁达", "看开", "积极", "阳光", "开朗"], "description": "对事物持积极正面的态度"},
    {"name": "悲观", "category": "personality", "keywords": ["悲观", "消极", "看坏", "负面", "失望", "绝望", "不抱希望", "消极", "消极"], "description": "对事物持消极负面的态度"},
    {"name": "责任心强", "category": "personality", "keywords": ["负责", "担当", "可靠", "尽职", "认真负责", "使命感", "尽责", "守信用", "靠谱"], "description": "对责任和承诺的高度重视"},
    {"name": "随和", "category": "personality", "keywords": ["随和", "好相处", "包容", "宽厚", "平易近人", "温和", "友善", "容易相处"], "description": "容易相处且包容他人的性格"},
    {"name": "控制欲", "category": "personality", "keywords": ["控制欲", "掌控", "支配", "强势", "说了算", "必须听", "掌控一切", "控制"], "description": "对环境和他人过度控制的倾向"},

    # 认知标签
    {"name": "灾难化", "category": "cognition", "keywords": ["灾难化", "最坏结果", "完了", "完蛋", "不堪设想", "不堪设想", "最坏的打算", "不敢想"], "description": "倾向于预测最坏结果"},
    {"name": "非黑即白", "category": "cognition", "keywords": ["非黑即白", "要么好要么坏", "极端", "全盘否定", "绝对", "彻底", "完全", "绝对化"], "description": "用二元对立的方式看待事物"},
    {"name": "读心术", "category": "cognition", "keywords": ["读心术", "他知道", "一定觉得", "肯定想", "猜", "以为", "肯定", "一定"], "description": "假设知道他人想法而无证据"},
    {"name": "情绪化推理", "category": "cognition", "keywords": ["我感觉", "所以", "一定是", "感觉说明", "我感觉得到", "感觉如此"], "description": "将感受当作事实证据"},
    {"name": "应该陈述", "category": "cognition", "keywords": ["应该", "必须", "一定要", "不得不", "理应", "本该", "应当", "必须要"], "description": "用 rigid 规则要求自我或他人"},
    {"name": "标签化", "category": "cognition", "keywords": ["我是个", "我就是", "永远", "总是", "注定", "天生", "一辈子", "改不了"], "description": "用标签定义自己或他人"},

    # 关系标签
    {"name": "社交回避", "category": "relationship", "keywords": ["社交回避", "不想见人", "躲着人", "社恐", "社交恐惧", "害怕社交", "不想出门", "孤立"], "description": "回避社交互动的倾向"},
    {"name": "边界不清", "category": "relationship", "keywords": ["边界", "过度付出", "讨好", "讨好型", "不会拒绝", "委屈自己", "成全别人", "迁就"], "description": "个人边界感薄弱"},
    {"name": "依赖", "category": "relationship", "keywords": ["依赖", "离不开", "需要", "依靠", "依附", "依赖别人", "没有主见", "听别人的"], "description": "过度依赖他人决策和支持"},
    {"name": "独立", "category": "relationship", "keywords": ["独立", "自主", "自立", "靠自己", "不依赖", "独当一面", "自我独立", "独来独往"], "description": "独立解决问题和做决策"},
    {"name": "冲突回避", "category": "relationship", "keywords": ["冲突回避", "不想吵架", "忍", "息事宁人", "和稀泥", "不敢反驳", "委曲求全", "忍气吞声"], "description": "回避人际冲突的倾向"},

    # 习惯标签
    {"name": "早起", "category": "habit", "keywords": ["早起", "晨间", "早上", "闹钟", "起床", "清晨", "晨光", "早起习惯", "早起打卡"], "description": "保持早起的生活节奏"},
    {"name": "运动", "category": "habit", "keywords": ["运动", "锻炼", "健身", "跑步", "瑜伽", "游泳", "打球", "训练", "体能", "锻炼"], "description": "定期进行体育锻炼"},
    {"name": "阅读", "category": "habit", "keywords": ["阅读", "读书", "看书", "学习", "知识", "充电", "读书打卡", "看书学习"], "description": "保持阅读学习的习惯"},
    {"name": "冥想", "category": "habit", "keywords": ["冥想", "正念", "打坐", "静思", "呼吸", "觉察", "当下", "冥想练习", "静坐"], "description": "通过冥想训练注意力和觉察"},
    {"name": "健康饮食", "category": "habit", "keywords": ["健康饮食", "节食", "减肥", "营养", "控糖", "清淡", "少吃", "饮食控制", "轻食"], "description": "注重饮食健康和营养平衡"},
    {"name": "熬夜", "category": "habit", "keywords": ["熬夜", "晚睡", "失眠", "睡不着", "夜猫子", "通宵", "深夜", "凌晨", "睡不着"], "description": "晚睡或睡眠不足的习惯"},
    {"name": "刷手机", "category": "habit", "keywords": ["刷手机", "玩手机", "短视频", "抖音", "刷视频", "停不下来", "沉迷", "手机依赖"], "description": "过度使用手机"},

    # 价值观标签
    {"name": "追求成长", "category": "value", "keywords": ["成长", "进步", "变得更好", "突破", "超越", "提升", "蜕变", "自我提升", "精进"], "description": "注重个人成长和自我完善"},
    {"name": "追求安稳", "category": "value", "keywords": ["安稳", "稳定", "安全感", "踏实", "安稳", "平平淡淡", "平平淡淡", "平凡", "安定"], "description": "重视生活的稳定和安全"},
    {"name": "追求自由", "category": "value", "keywords": ["自由", "不受约束", "自在", "随心所欲", "不受限制", "无拘无束", "洒脱", "随性"], "description": "重视自主选择和自由空间"},
    {"name": "追求认可", "category": "value", "keywords": ["认可", "肯定", "表扬", "被看见", "被接纳", "需要认可", "需要被肯定", "渴望认可"], "description": "重视他人的认可和评价"},
    {"name": "追求意义", "category": "value", "keywords": ["意义", "价值", "使命感", "为什么", "目的", "值得", "意义感", "有价值", "有意义"], "description": "重视生活的意义和价值感"},
]

# ── 标签抽取引擎 ─────────────────────────────────────────────

class PersonaTagEngine:
    """用户人格画像标签抽取引擎"""

    def __init__(self, db_pool=None):
        self._db_pool = db_pool
        self._tag_map: Dict[str, Dict[str, Any]] = {}  # {category: {name: tag_info}}
        self._keyword_index: Dict[str, List[Tuple[str, str, float]]] = {}  # {keyword: [(cat, name, weight)]}
        self._init_system_tags()

    def _init_system_tags(self):
        """初始化系统标签索引"""
        for tag in SYSTEM_TAG_LIBRARY:
            cat = tag["category"]
            name = tag["name"]
            if cat not in self._tag_map:
                self._tag_map[cat] = {}
            self._tag_map[cat][name] = tag
            for kw in tag.get("keywords", []):
                if kw not in self._keyword_index:
                    self._keyword_index[kw] = []
                self._keyword_index[kw].append((cat, name, tag.get("weight_default", 1.0)))

    # ── 规则引擎 ───────────────────────────────────────────

    def extract_tags_from_text(self, text: str, context: str = "general") -> List[Dict[str, Any]]:
        """从文本中基于规则抽取标签"""
        if not text or not isinstance(text, str):
            return []

        text_lower = text.lower()
        matched_tags: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for keyword, tag_refs in self._keyword_index.items():
            if keyword in text_lower:
                for cat, name, weight in tag_refs:
                    key = (cat, name)
                    if key not in matched_tags:
                        matched_tags[key] = {
                            "tag_name": name,
                            "tag_category": cat,
                            "confidence": 0.0,
                            "matched_keywords": [],
                            "weight": weight,
                        }
                    matched_tags[key]["matched_keywords"].append(keyword)
                    matched_tags[key]["confidence"] = min(
                        0.95, matched_tags[key]["confidence"] + 0.25
                    )

        # 计算最终权重：关键词命中次数 + 基础权重
        result = []
        for key, tag_info in matched_tags.items():
            freq_bonus = len(tag_info["matched_keywords"]) * 0.5
            tag_info["weight"] = min(10.0, tag_info["weight"] + freq_bonus)
            tag_info["confidence"] = min(1.0, tag_info["confidence"] + 0.05)
            result.append(tag_info)

        # 按置信度排序
        result.sort(key=lambda x: x["confidence"], reverse=True)
        return result

    def extract_tags_from_analysis_result(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从心理学分析结果中抽取标签"""
        tags = []

        # L0: 人格驱动因子
        l0 = analysis.get("layers", {}).get("L0_causal", {}).get("personality_driver", {})
        driver_cat = l0.get("driver_category", "")
        core_belief = l0.get("core_belief", "")
        if driver_cat:
            tags.extend(self.extract_tags_from_text(driver_cat, "l0_driver"))
        if core_belief:
            tags.extend(self.extract_tags_from_text(core_belief, "l0_belief"))

        # L1: 认知图式
        l1_schema = analysis.get("layers", {}).get("L1_regulation", {}).get("cognitive_schema", {})
        distortion = l1_schema.get("distortion_type", "")
        if distortion:
            tags.extend(self.extract_tags_from_text(distortion, "l1_schema"))

        # L2: 执行状态
        l2 = analysis.get("layers", {}).get("L2_execution", {}).get("current_state", {})
        state_name = l2.get("state_name", "")
        if state_name:
            tags.extend(self.extract_tags_from_text(state_name, "l2_state"))

        # L3: 身份叙事
        l3 = analysis.get("layers", {}).get("L3_identity", {}).get("identity_narrative", {})
        narrative_type = l3.get("narrative_type", "")
        if narrative_type:
            tags.extend(self.extract_tags_from_text(narrative_type, "l3_identity"))

        # 合并去重，取最高置信度和权重
        merged: Dict[str, Dict[str, Any]] = {}
        for t in tags:
            name = t["tag_name"]
            if name not in merged:
                merged[name] = t
            else:
                merged[name]["confidence"] = max(merged[name]["confidence"], t["confidence"])
                merged[name]["weight"] = max(merged[name]["weight"], t["weight"])
                merged[name]["matched_keywords"] = list(set(
                    merged[name].get("matched_keywords", []) + t.get("matched_keywords", [])
                ))

        return list(merged.values())

    # ── 数据库操作 ───────────────────────────────────────────

    def ensure_system_tags_in_db(self, conn):
        """确保系统标签存在于数据库中"""
        with conn.cursor() as cur:
            for tag in SYSTEM_TAG_LIBRARY:
                cur.execute(
                    '''INSERT INTO persona_tags (tag_name, tag_category, tag_type, description, keywords, weight_default)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (tag_name, tag_category) DO NOTHING
                       RETURNING id''',
                    (tag["name"], tag["category"], "system", tag.get("description", ""),
                     tag.get("keywords", []), tag.get("weight_default", 1.0))
                )

    def store_user_tags(self, conn, user_id: int, tags: List[Dict[str, Any]],
                        source_type: str = "auto", source_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """将抽取的标签存储到用户标签关联表"""
        stored = []
        with conn.cursor() as cur:
            for tag in tags:
                tag_name = tag["tag_name"]
                tag_category = tag["tag_category"]
                weight = tag.get("weight", 1.0)
                confidence = tag.get("confidence", 0.8)

                # 获取或创建标签
                cur.execute(
                    '''SELECT id FROM persona_tags WHERE tag_name = %s AND tag_category = %s''',
                    (tag_name, tag_category)
                )
                row = cur.fetchone()
                if row:
                    tag_id = row[0]
                else:
                    cur.execute(
                        '''INSERT INTO persona_tags (tag_name, tag_category, tag_type, keywords, weight_default)
                           VALUES (%s, %s, %s, %s, %s) RETURNING id''',
                        (tag_name, tag_category, "auto", tag.get("matched_keywords", []), weight)
                    )
                    tag_id = cur.fetchone()[0]

                # 插入/更新用户标签关联
                cur.execute(
                    '''INSERT INTO user_persona_tags
                       (user_id, tag_id, weight, frequency, source_type, source_id, confidence, last_seen_at)
                       VALUES (%s, %s, %s, 1, %s, %s, %s, NOW())
                       ON CONFLICT (user_id, tag_id, source_type) DO UPDATE SET
                           weight = GREATEST(EXCLUDED.weight, user_persona_tags.weight + 0.2),
                           frequency = user_persona_tags.frequency + 1,
                           last_seen_at = NOW(),
                           confidence = GREATEST(EXCLUDED.confidence, user_persona_tags.confidence)
                       RETURNING weight, frequency''',
                    (user_id, tag_id, weight, source_type, source_id, confidence)
                )
                wf = cur.fetchone()
                stored.append({
                    "tag_name": tag_name,
                    "tag_category": tag_category,
                    "weight": wf[0] if wf else weight,
                    "frequency": wf[1] if wf else 1,
                    "confidence": confidence,
                })
        conn.commit()
        return stored

    def get_user_tags(self, conn, user_id: int, category: Optional[str] = None,
                      limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户的标签列表"""
        with conn.cursor() as cur:
            if category:
                cur.execute(
                    '''SELECT pt.tag_name, pt.tag_category, upt.weight, upt.frequency,
                              upt.confidence, upt.first_seen_at, upt.last_seen_at
                       FROM user_persona_tags upt
                       JOIN persona_tags pt ON upt.tag_id = pt.id
                       WHERE upt.user_id = %s AND pt.tag_category = %s
                       ORDER BY upt.weight DESC, upt.frequency DESC
                       LIMIT %s''',
                    (user_id, category, limit)
                )
            else:
                cur.execute(
                    '''SELECT pt.tag_name, pt.tag_category, upt.weight, upt.frequency,
                              upt.confidence, upt.first_seen_at, upt.last_seen_at
                       FROM user_persona_tags upt
                       JOIN persona_tags pt ON upt.tag_id = pt.id
                       WHERE upt.user_id = %s
                       ORDER BY upt.weight DESC, upt.frequency DESC
                       LIMIT %s''',
                    (user_id, limit)
                )
            rows = cur.fetchall()
            return [{
                "tag_name": r[0],
                "tag_category": r[1],
                "weight": r[2],
                "frequency": r[3],
                "confidence": r[4],
                "first_seen_at": r[5].isoformat() if r[5] else None,
                "last_seen_at": r[6].isoformat() if r[6] else None,
            } for r in rows]

    def compute_user_profile(self, conn, user_id: int) -> Dict[str, Any]:
        """计算用户人格画像"""
        with conn.cursor() as cur:
            # 获取所有标签
            cur.execute(
                '''SELECT pt.tag_name, pt.tag_category, SUM(upt.weight * upt.frequency) as total_score,
                          COUNT(*) as freq, AVG(upt.confidence) as avg_conf
                   FROM user_persona_tags upt
                   JOIN persona_tags pt ON upt.tag_id = pt.id
                   WHERE upt.user_id = %s
                   GROUP BY pt.tag_name, pt.tag_category
                   ORDER BY total_score DESC''',
                (user_id,)
            )
            tag_rows = cur.fetchall()

            tag_cloud = {}
            emotion_dominance = {}
            behavior_patterns = {}
            habit_strength = {}
            personality_vector = {}

            for r in tag_rows:
                name, cat, score, freq, conf = r
                tag_cloud[name] = {"weight": round(float(score), 2), "frequency": freq,
                                     "category": cat, "confidence": round(float(conf), 2)}
                if cat == "emotion":
                    emotion_dominance[name] = round(float(score), 2)
                elif cat == "behavior":
                    behavior_patterns[name] = round(float(score), 2)
                elif cat == "habit":
                    habit_strength[name] = round(float(score), 2)
                elif cat == "personality":
                    personality_vector[name] = round(float(score), 2)

            # 计算稳定性（情绪标签的方差越小越稳定）
            emotion_weights = [v for k, v in emotion_dominance.items()]
            stability_score = 7.0
            if len(emotion_weights) > 1:
                avg = sum(emotion_weights) / len(emotion_weights)
                variance = sum((w - avg) ** 2 for w in emotion_weights) / len(emotion_weights)
                stability_score = max(1.0, 10.0 - min(9.0, variance))

            # 计算韧性（坚韧标签权重 + 坚持行为权重）
            resilience_score = 5.0
            if "坚韧" in personality_vector:
                resilience_score += personality_vector["坚韧"] * 0.3
            if "坚持" in behavior_patterns:
                resilience_score += behavior_patterns["坚持"] * 0.3
            resilience_score = min(10.0, resilience_score)

            # 风险等级
            risk_tags = sum(1 for t in tag_rows if t[1] in ("emotion", "behavior", "cognition")
                           and t[3] > 3 and t[2] > 5)
            risk_level = "low" if risk_tags < 3 else ("moderate" if risk_tags < 6 else "high")

            # 成长趋势（基于最近30天 vs 之前30天的标签变化）
            cur.execute(
                '''SELECT COUNT(*) FROM user_persona_tags
                   WHERE user_id = %s AND last_seen_at > NOW() - INTERVAL '30 days' ''',
                (user_id,)
            )
            recent_count = cur.fetchone()[0] or 0

            cur.execute(
                '''SELECT COUNT(*) FROM user_persona_tags
                   WHERE user_id = %s AND last_seen_at BETWEEN NOW() - INTERVAL '60 days' AND NOW() - INTERVAL '30 days' ''',
                (user_id,)
            )
            prev_count = cur.fetchone()[0] or 1

            growth_ratio = recent_count / max(1, prev_count)
            growth_trend = "improving" if growth_ratio > 1.2 else ("declining" if growth_ratio < 0.8 else "stable")

            profile = {
                "user_id": user_id,
                "tag_cloud": tag_cloud,
                "emotion_dominance": emotion_dominance,
                "behavior_patterns": behavior_patterns,
                "habit_strength": habit_strength,
                "personality_vector": personality_vector,
                "stability_score": round(stability_score, 1),
                "resilience_score": round(resilience_score, 1),
                "growth_trend": growth_trend,
                "risk_level": risk_level,
                "total_tags": len(tag_rows),
                "computed_at": datetime.now().isoformat(),
            }

            # 保存/更新画像
            cur.execute(
                '''INSERT INTO user_persona_profiles
                   (user_id, tag_cloud, emotion_dominance, behavior_patterns,
                    habit_strength, personality_vector, stability_score,
                    resilience_score, growth_trend, risk_level, profile_version, computed_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, NOW())
                   ON CONFLICT (user_id) DO UPDATE SET
                       tag_cloud = EXCLUDED.tag_cloud,
                       emotion_dominance = EXCLUDED.emotion_dominance,
                       behavior_patterns = EXCLUDED.behavior_patterns,
                       habit_strength = EXCLUDED.habit_strength,
                       personality_vector = EXCLUDED.personality_vector,
                       stability_score = EXCLUDED.stability_score,
                       resilience_score = EXCLUDED.resilience_score,
                       growth_trend = EXCLUDED.growth_trend,
                       risk_level = EXCLUDED.risk_level,
                       profile_version = user_persona_profiles.profile_version + 1,
                       computed_at = NOW()''',
                (user_id, json.dumps(tag_cloud), json.dumps(emotion_dominance),
                 json.dumps(behavior_patterns), json.dumps(habit_strength),
                 json.dumps(personality_vector), stability_score,
                 resilience_score, growth_trend, risk_level)
            )
            conn.commit()
            return profile

    # ── 自动抽取并存储（便捷方法）────────────────────────────

    def auto_extract_and_store(self, conn, user_id: int, text: str,
                                source_type: str, source_id: Optional[str] = None,
                                analysis_result: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """自动从文本和分析结果中抽取标签并存储"""
        tags = self.extract_tags_from_text(text, source_type)

        if analysis_result:
            analysis_tags = self.extract_tags_from_analysis_result(analysis_result)
            # 合并
            merged = {t["tag_name"]: t for t in tags}
            for t in analysis_tags:
                if t["tag_name"] in merged:
                    merged[t["tag_name"]]["confidence"] = max(
                        merged[t["tag_name"]]["confidence"], t["confidence"]
                    )
                    merged[t["tag_name"]]["weight"] = max(
                        merged[t["tag_name"]]["weight"], t["weight"]
                    )
                else:
                    merged[t["tag_name"]] = t
            tags = list(merged.values())

        if tags:
            self.ensure_system_tags_in_db(conn)
            return self.store_user_tags(conn, user_id, tags, source_type, source_id)
        return []


# ── 全局实例 ─────────────────────────────────────────────────

_tag_engine: Optional[PersonaTagEngine] = None


def get_tag_engine(db_pool=None) -> PersonaTagEngine:
    global _tag_engine
    if _tag_engine is None:
        _tag_engine = PersonaTagEngine(db_pool=db_pool)
    return _tag_engine
