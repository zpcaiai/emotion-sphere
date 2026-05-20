-- ============================================================
-- 人格因果引擎 + 心理动力系统 - 数据库 Schema
-- L0-L4 架构完整实现
-- ============================================================

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- L0: 人格因果引擎 - 核心表
-- ============================================================

-- 1. 情绪日志表（原始输入）
CREATE TABLE IF NOT EXISTS emotion_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 原始输入
    raw_text        TEXT NOT NULL,
    emotion_tags    TEXT[],
    intensity       INTEGER CHECK (intensity BETWEEN 1 AND 10),
    
    -- 时间戳（支持回溯）
    occurred_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 元数据
    context_json    JSONB DEFAULT '{}',  -- 场景、触发事件等
    source          VARCHAR(50) DEFAULT 'web', -- web/miniprogram/wechat
    
    -- 索引
    CONSTRAINT idx_emotion_logs_user_time UNIQUE (user_id, occurred_at, id)
);

CREATE INDEX IF NOT EXISTS idx_emotion_logs_user_id ON emotion_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_emotion_logs_occurred_at ON emotion_logs(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_emotion_logs_emotion_tags ON emotion_logs USING GIN(emotion_tags);

-- 2. 人格驱动因子模型（因果分析结果）
CREATE TABLE IF NOT EXISTS personality_drivers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    log_id          UUID REFERENCES emotion_logs(id) ON DELETE CASCADE,
    
    -- L0 分析结果
    surface_problem TEXT,           -- 表层问题
    deep_emotion    TEXT,           -- 深层情绪
    hidden_dynamics TEXT,           -- 隐藏心理动力
    behavioral_cycle  JSONB,          -- 行为循环: {trigger, emotion, escape, reward, shame, repeat}
    
    -- 人格结构影响
    personality_traits JSONB,       -- 强化问题的人格特征
    long_term_risk    TEXT,         -- 长期风险
    intervention_priority INTEGER,  -- 干预优先级 1-5
    
    -- 驱动因子分类
    driver_category   VARCHAR(50),  -- perfectionism/catastrophizing/impostor/emotional_reasoning/overgeneralization
    core_belief       TEXT,         -- 核心信念: "If I fail, I am worthless"
    
    -- 心理动力学补充（基于依恋理论和防御机制）
    attachment_style  VARCHAR(20),  -- secure/anxious/avoidant/disorganized 依恋风格
    defense_mechanism VARCHAR(50), -- repression/projection/rationalization/displacement 防御机制
    emotional_regulation_strategy VARCHAR(50), -- reappraisal/suppression/acceptance/distraction 调节策略
    
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzed_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_personality_drivers_user_id ON personality_drivers(user_id);
CREATE INDEX IF NOT EXISTS idx_personality_drivers_log_id ON personality_drivers(log_id);
CREATE INDEX IF NOT EXISTS idx_personality_drivers_category ON personality_drivers(driver_category);

-- 3. 行为触发器库（Trigger Inventory）
CREATE TABLE IF NOT EXISTS behavioral_triggers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    trigger_name    VARCHAR(200) NOT NULL,
    trigger_type    VARCHAR(50),  -- situational/interpersonal/internal/memory
    trigger_pattern TEXT,         -- 描述模式
    
    -- ABC 模型
    activating_event   TEXT,      -- A
    belief_system      JSONB,     -- B: {irrational_belief, rational_alternative}
    consequence        JSONB,     -- C: {emotion, behavior}
    
    frequency_count    INTEGER DEFAULT 1,
    last_triggered_at  TIMESTAMP,
    
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_behavioral_triggers_user_id ON behavioral_triggers(user_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_triggers_type ON behavioral_triggers(trigger_type);

-- ============================================================
-- L1: 行为调节引擎 - 认知图式与干预
-- ============================================================

-- 4. 认知图式表（Schema Therapy + REBT）
CREATE TABLE IF NOT EXISTS cognitive_schemas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- ABC 分析（基于Ellis的ABC理论）
    schema_name     VARCHAR(100) NOT NULL,
    -- 认知扭曲类型（基于Beck的认知疗法分类）
    distortion_type VARCHAR(50),  -- all_or_nothing/catastrophizing/mind_reading/mental_filtering
                                  -- discounting_positive/emotional_reasoning/should_statements
                                  -- labeling/overgeneralization/personalization
    
    -- A: Activating Event 诱发事件
    activating_event   TEXT,
    event_context      JSONB,     -- {where, when, who, what}
    
    -- B: Beliefs 信念系统（分层级）
    automatic_thought  TEXT,     -- 自动化思维
    intermediate_belief TEXT,    -- 中间信念（态度、规则、假设）
    core_belief        TEXT,     -- 核心信念（关于自我、他人、世界的根本信念）
    
    -- C: Consequences 后果（情绪+行为+生理）
    consequence_emotional    TEXT,
    consequence_behavioral   TEXT,
    consequence_physiological TEXT, -- 生理反应：心跳加速、肌肉紧张等
    
    -- 核心信念和早期适应不良图式
    latent_schema   JSONB,        -- {core_need, early_maladaptive_schema, coping_style}
    
    -- 认知重构
    cognitive_reframing_patch TEXT,  -- 反向陈述
    reframing_evidence JSONB,   -- 支持证据列表
    
    -- 状态
    is_active       BOOLEAN DEFAULT TRUE,
    severity_score  INTEGER CHECK (severity_score BETWEEN 1 AND 10),
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_user_id ON cognitive_schemas(user_id);
CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_distortion ON cognitive_schemas(distortion_type);
CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_active ON cognitive_schemas(user_id, is_active);

-- 5. 行为实验表（CBT Behavioral Experiments）
CREATE TABLE IF NOT EXISTS behavioral_experiments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    schema_id       UUID REFERENCES cognitive_schemas(id) ON DELETE SET NULL,
    
    -- 实验定义（基于Bennett-Levy等行为实验手册）
    experiment_id   VARCHAR(100) UNIQUE,  -- exp_2026_cat_001 格式
    title           VARCHAR(200) NOT NULL,
    hypothesis_to_test TEXT,      -- 要证伪的假设（负面预测）
    alternative_hypothesis TEXT,  -- 替代性假设（积极预测）
    
    -- 实验设计
    counter_behavioral_action TEXT, -- 具体低摩擦行动
    difficulty_level    INTEGER CHECK (difficulty_level BETWEEN 1 AND 5),
    estimated_duration_minutes INTEGER, -- 预计耗时
    
    -- 实验类型（基于暴露疗法和学习理论）
    experiment_type     VARCHAR(50), -- hypothesis_testing/exposure/behavioral_activation/skills_practice
    
    -- 情绪预测（核心机制）
    predicted_emotion_before  TEXT,    -- 预测："我会感到焦虑"
    predicted_intensity_min   INTEGER, -- 预测情绪强度范围（最低）
    predicted_intensity_max   INTEGER, -- 预测情绪强度范围（最高）
    
    -- 二元遥测指标
    binary_telemetry_metric TEXT, -- "Did someone scold you? Yes/No"
    success_criteria    JSONB,    -- {metric, threshold, operator}
    
    -- 安全行为识别（需要减少的逃避行为）
    safety_behaviors    TEXT[],   -- 如 ["避免眼神接触", "提前准备借口"]
    behavioral_goal   TEXT,       -- 具体行为目标（SMART原则）
    
    -- 执行追踪
    status          VARCHAR(20) DEFAULT 'pending', -- pending/in_progress/completed/abandoned
    scheduled_at    TIMESTAMP,
    completed_at    TIMESTAMP,
    
    -- 结果
    actual_outcome    JSONB,      -- {result, evidence, emotion_after}
    hypothesis_falsified BOOLEAN, -- 是否证伪
    user_reflection   TEXT,
    
    -- 元数据
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reminder_sent   BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_user_id ON behavioral_experiments(user_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_schema ON behavioral_experiments(schema_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_status ON behavioral_experiments(status);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_scheduled ON behavioral_experiments(scheduled_at);

-- ============================================================
-- L2: 执行力边缘引导 - 状态机
-- ============================================================

-- 6. 心理状态机快照（State Machine）
CREATE TABLE IF NOT EXISTS psychological_states (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 状态机定义
    state_name      VARCHAR(50) NOT NULL,  -- crisis/dysregulated/regulated/flow/integrated
    state_level     INTEGER CHECK (state_level BETWEEN 0 AND 4), -- 0=crisis, 4=integrated
    
    -- 维度评估
    arousal_level   INTEGER CHECK (arousal_level BETWEEN 1 AND 10), -- 生理唤醒
    valence_score   INTEGER CHECK (valence_score BETWEEN -10 AND 10), -- 情绪效价
    focus_capacity  INTEGER CHECK (focus_capacity BETWEEN 1 AND 10), -- 专注能力
    
    -- 触发因素
    triggering_factors JSONB[],  -- [{type, description, intensity}]
    protective_factors JSONB[],  -- [{type, description, strength}]
    
    -- 推荐干预
    recommended_action TEXT,     -- 当前状态推荐的即时行动
    escalation_protocol TEXT,    -- 升级协议（如果恶化）
    
    -- 时间
    captured_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at      TIMESTAMP,   -- 状态有效期（动态过期）
    
    -- 连续状态链
    previous_state_id UUID REFERENCES psychological_states(id),
    state_duration_seconds INTEGER -- 该状态持续多久
);

CREATE INDEX IF NOT EXISTS idx_psychological_states_user_id ON psychological_states(user_id);
CREATE INDEX IF NOT EXISTS idx_psychological_states_captured ON psychological_states(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_psychological_states_level ON psychological_states(state_level);

-- 7. 执行力干预日志（边缘引导执行记录）
CREATE TABLE IF NOT EXISTS intervention_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    state_id        UUID REFERENCES psychological_states(id) ON DELETE SET NULL,
    experiment_id   UUID REFERENCES behavioral_experiments(id) ON DELETE SET NULL,
    
    intervention_type   VARCHAR(50), -- micro_skill/state_shift/experiment_launch/grounding
    intervention_layer  INTEGER CHECK (intervention_layer BETWEEN 0 AND 4), -- L0-L4
    
    -- 干预内容
    prompt_text     TEXT,           -- 给用户的提示语
    technique_used  VARCHAR(100),   -- 使用的技术（如：5-4-3-2-1 grounding）
    
    -- 执行结果
    was_delivered   BOOLEAN DEFAULT FALSE,
    user_response   TEXT,           -- 用户反馈
    effectiveness_score INTEGER CHECK (effectiveness_score BETWEEN 1 AND 10),
    
    delivered_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_intervention_logs_user_id ON intervention_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_intervention_logs_delivered ON intervention_logs(delivered_at DESC);

-- ============================================================
-- L3: 长期身份认同系统
-- ============================================================

-- 8. 身份认同叙事（Identity Narrative）
CREATE TABLE IF NOT EXISTS identity_narratives (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 叙事维度
    narrative_type  VARCHAR(50),  -- origin/turning_point/redemption/contamination
    narrative_title VARCHAR(200),
    narrative_text  TEXT,           -- 完整叙事
    
    -- 身份主题
    identity_themes JSONB[],       -- ["survivor", "helper", "creative", "struggler"]
    core_values     JSONB[],       -- [{value, importance_score}]
    
    -- 时间线
    narrative_period_start DATE,
    narrative_period_end   DATE,
    is_current      BOOLEAN DEFAULT FALSE, -- 是否是当前主导叙事
    
    -- 连贯性评估
    coherence_score     INTEGER CHECK (coherence_score BETWEEN 1 AND 10),
    agency_score        INTEGER CHECK (agency_score BETWEEN 1 AND 10),
    redemption_score    INTEGER CHECK (redemption_score BETWEEN 1 AND 10),
    
    -- 元数据
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_current_narrative UNIQUE (user_id, is_current) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS idx_identity_narratives_user_id ON identity_narratives(user_id);
CREATE INDEX IF NOT EXISTS idx_identity_narratives_current ON identity_narratives(user_id, is_current) WHERE is_current = TRUE;

-- 9. 自我概念模型（Self-Concept）
CREATE TABLE IF NOT EXISTS self_concept_models (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 自我维度评估
    self_efficacy   INTEGER CHECK (self_efficacy BETWEEN 1 AND 10),      -- 自我效能感
    self_worth      INTEGER CHECK (self_worth BETWEEN 1 AND 10),        -- 自我价值感
    self_stability  INTEGER CHECK (self_stability BETWEEN 1 AND 10),     -- 自我稳定性
    
    -- 理想自我 vs 现实自我
    ideal_self      JSONB,          -- {attributes, goals, timeline}
    actual_self     JSONB,          -- {attributes, current_state}
    discrepancy_score INTEGER CHECK (discrepancy_score BETWEEN 0 AND 10), -- 差距分数
    
    -- 身份承诺
    identity_commitments JSONB[],   -- [{domain, commitment_level, progress}]
    
    assessed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_assessment_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_self_concept_user_id ON self_concept_models(user_id);
CREATE INDEX IF NOT EXISTS idx_self_concept_assessed ON self_concept_models(assessed_at DESC);

-- ============================================================
-- L4: 记忆与成长轨迹
-- ============================================================

-- 10. 成长轨迹指标
CREATE TABLE IF NOT EXISTS growth_trajectories (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 时间维度
    period_type     VARCHAR(20),  -- daily/weekly/monthly/quarterly/yearly
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    
    -- 多维度成长指标
    emotional_regulation_score  INTEGER CHECK (emotional_regulation_score BETWEEN 1 AND 100),
    cognitive_flexibility_score INTEGER CHECK (cognitive_flexibility_score BETWEEN 1 AND 100),
    behavioral_activation_score INTEGER CHECK (behavioral_activation_score BETWEEN 1 AND 100),
    interpersonal_effectiveness_score INTEGER CHECK (interpersonal_effectiveness_score BETWEEN 1 AND 100),
    self_concept_clarity_score INTEGER CHECK (self_concept_clarity_score BETWEEN 1 AND 100),
    
    -- 纵向变化
    change_from_last_period JSONB, -- {metric_name, previous_score, delta, percent_change}
    
    -- 关键事件
    significant_events JSONB[],    -- [{type, description, impact_score}]
    
    -- 洞察生成
    generated_insights TEXT[],     -- AI生成的周期性洞察
    recommended_focus_areas TEXT[], -- 下一阶段建议
    
    calculated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_growth_trajectories_user_id ON growth_trajectories(user_id);
CREATE INDEX IF NOT EXISTS idx_growth_trajectories_period ON growth_trajectories(user_id, period_type, period_start DESC);

-- 11. 模式识别结果（Pattern Recognition）
CREATE TABLE IF NOT EXISTS pattern_recognitions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    pattern_type    VARCHAR(50),  -- cyclical/linear/chaotic/stable/chaotic_stable
    pattern_name    VARCHAR(200),
    pattern_description TEXT,
    
    -- 模式数据
    detected_in_logs UUID[],      -- 涉及的日志ID列表
    time_range_start TIMESTAMP,
    time_range_end   TIMESTAMP,
    
    -- 模式特征
    frequency_pattern JSONB,      -- {avg_interval, regularity_score}
    trigger_pattern   JSONB,      -- 常见触发因素
    response_pattern  JSONB,      -- 典型反应模式
    
    -- 预测性指标
    predictability_score INTEGER CHECK (predictability_score BETWEEN 1 AND 10),
    next_occurrence_prediction TIMESTAMP, -- 预测下次发生时间
    
    -- 干预建议
    breaking_strategy TEXT,       -- 打破模式的策略
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_user_id ON pattern_recognitions(user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_type ON pattern_recognitions(pattern_type);

-- 12. 长期记忆摘要（Episodic Memory Consolidation）
CREATE TABLE IF NOT EXISTS memory_consolidations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    memory_type     VARCHAR(50),  -- semantic/episodic/procedural/emotional
    memory_title    VARCHAR(200),
    memory_content  TEXT,
    
    -- 情绪标记
    emotional_valence   INTEGER CHECK (emotional_valence BETWEEN -10 AND 10),
    emotional_arousal   INTEGER CHECK (emotional_arousal BETWEEN 1 AND 10),
    
    -- 记忆链接
    related_logs    UUID[],
    related_schemas UUID[],
    related_narratives UUID[],
    
    -- 记忆强度（随时间衰减）
    memory_strength     INTEGER CHECK (memory_strength BETWEEN 1 AND 100),
    last_accessed_at    TIMESTAMP,
    access_count        INTEGER DEFAULT 1,
    
    -- 时间
    original_event_at   TIMESTAMP, -- 原始事件发生时间
    consolidated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 元数据
    is_archived         BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_memory_consolidations_user_id ON memory_consolidations(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_type ON memory_consolidations(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_strength ON memory_consolidations(user_id, memory_strength DESC);

-- ============================================================
-- 视图与辅助功能
-- ============================================================

-- 用户心理仪表盘视图
CREATE OR REPLACE VIEW user_psychological_dashboard AS
SELECT 
    u.id as user_id,
    u.nickname,
    
    -- 最新状态
    (SELECT state_name FROM psychological_states 
     WHERE user_id = u.id ORDER BY captured_at DESC LIMIT 1) as current_state,
    
    -- 活跃图式数量
    (SELECT COUNT(*) FROM cognitive_schemas 
     WHERE user_id = u.id AND is_active = TRUE) as active_schemas_count,
    
    -- 待完成实验
    (SELECT COUNT(*) FROM behavioral_experiments 
     WHERE user_id = u.id AND status IN ('pending', 'in_progress')) as pending_experiments,
    
    -- 本周情绪日志
    (SELECT COUNT(*) FROM emotion_logs 
     WHERE user_id = u.id AND occurred_at > NOW() - INTERVAL '7 days') as weekly_logs,
    
    -- 最新成长评估
    (SELECT jsonb_build_object(
        'emotional_regulation', emotional_regulation_score,
        'cognitive_flexibility', cognitive_flexibility_score,
        'behavioral_activation', behavioral_activation_score
    ) FROM growth_trajectories 
    WHERE user_id = u.id ORDER BY period_start DESC LIMIT 1) as latest_growth_scores,
    
    -- 主导身份叙事
    (SELECT narrative_title FROM identity_narratives 
     WHERE user_id = u.id AND is_current = TRUE LIMIT 1) as current_identity
    
FROM users u;

-- 自动更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要更新时间的表创建触发器
DROP TRIGGER IF EXISTS trg_cognitive_schemas_updated ON cognitive_schemas;
CREATE TRIGGER trg_cognitive_schemas_updated 
BEFORE UPDATE ON cognitive_schemas 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_identity_narratives_updated ON identity_narratives;
CREATE TRIGGER trg_identity_narratives_updated 
BEFORE UPDATE ON identity_narratives 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 心理学分析结果持久化（L0-L4 多层分析）
-- ============================================================

CREATE TABLE IF NOT EXISTS psychology_analysis_results (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 分析元数据
    analysis_type       VARCHAR(50) DEFAULT 'emotion',  -- emotion/behavior/execution
    input_text          TEXT,
    intensity           INTEGER CHECK (intensity BETWEEN 1 AND 10),
    
    -- L0: 人格驱动
    l0_driver_category      VARCHAR(50),  -- Perfectionism/Catastrophizing/etc
    l0_surface_problem      TEXT,
    l0_deep_emotion         TEXT,
    l0_core_belief          TEXT,
    l0_intervention_priority INTEGER CHECK (l0_intervention_priority BETWEEN 1 AND 5),
    
    -- L1: 认知图式
    l1_distortion_type      VARCHAR(50),
    l1_activating_event     TEXT,
    l1_core_belief          TEXT,
    l1_reframing_patch      TEXT,
    l1_experiment_id        VARCHAR(100),
    l1_experiment_title     TEXT,
    l1_experiment_action    TEXT,
    
    -- L2: 心理状态
    l2_state_name           VARCHAR(50),
    l2_state_level          INTEGER CHECK (l2_state_level BETWEEN 0 AND 4),
    l2_arousal_level        INTEGER CHECK (l2_arousal_level BETWEEN 1 AND 10),
    l2_valence_score        INTEGER,
    l2_recommended_action   TEXT,
    l2_escalation_protocol  TEXT,
    
    -- L3: 身份认同（可选，当有历史数据时）
    l3_narrative_type       VARCHAR(50),
    l3_narrative_title      TEXT,
    l3_coherence_score      INTEGER,
    l3_agency_score         INTEGER,
    
    -- L4: 成长指标（可选）
    l4_emotional_regulation     INTEGER,
    l4_cognitive_flexibility    INTEGER,
    l4_behavioral_activation    INTEGER,
    l4_interpersonal_effectiveness INTEGER,
    l4_self_concept_clarity     INTEGER,
    
    -- 综合输出
    synthesis_immediate_action  TEXT,
    synthesis_core_insight      TEXT,
    synthesis_risk_level        VARCHAR(20),
    
    -- 系统状态
    is_crisis                   BOOLEAN DEFAULT FALSE,
    crisis_action               TEXT,
    
    -- 时间戳
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_psych_analysis_user ON psychology_analysis_results(user_id);
CREATE INDEX IF NOT EXISTS idx_psych_analysis_time ON psychology_analysis_results(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_psych_analysis_type ON psychology_analysis_results(analysis_type);
CREATE INDEX IF NOT EXISTS idx_psych_analysis_crisis ON psychology_analysis_results(user_id, is_crisis);

-- 触发器自动更新 updated_at
DROP TRIGGER IF EXISTS trg_psych_analysis_updated ON psychology_analysis_results;
CREATE TRIGGER trg_psych_analysis_updated 
BEFORE UPDATE ON psychology_analysis_results 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 子系统二：行为调节系统 + 习惯养成状态机
-- ============================================================

-- 13. 行为调节会话（动态行为工程追踪）
CREATE TABLE IF NOT EXISTS behavior_regulation_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 会话状态
    session_type    VARCHAR(50),  -- habit_task/emotion_regulation/crisis_intervention
    target_habit    VARCHAR(200),
    
    -- 实时系统状态评估 (Fogg模型: B=MAP)
    motivation_level    INTEGER CHECK (motivation_level BETWEEN 1 AND 10),
    ability_level       INTEGER CHECK (ability_level BETWEEN 1 AND 10),
    trigger_strength    INTEGER CHECK (trigger_strength BETWEEN 1 AND 10),
    
    -- 能量等级 (1-5, 用于状态机降级)
    energy_level        INTEGER CHECK (energy_level BETWEEN 1 AND 5),
    
    -- 执行阻力分析
    behavioral_resistance   INTEGER CHECK (behavioral_resistance BETWEEN 1 AND 10),
    cognitive_load          INTEGER CHECK (cognitive_load BETWEEN 1 AND 10),
    emotional_stability     INTEGER CHECK (emotional_stability BETWEEN 1 AND 10),
    attention_state         VARCHAR(20),  -- focused/distracted/scattered
    procrastination_level   INTEGER CHECK (procrastination_level BETWEEN 1 AND 10),
    
    -- 动态调节输出
    selected_tier           VARCHAR(10),  -- Green/Yellow/Red
    min_executable_action   TEXT,         -- 最小可执行动作
    task_downgrade          TEXT,         -- 降级版本
    emotional_compensation  TEXT,         -- 情绪补偿方式
    continuity_advice       TEXT,         -- 连续性建议
    
    -- 执行结果
    was_executed            BOOLEAN DEFAULT FALSE,
    execution_duration_seconds INTEGER,
    completion_percentage   INTEGER CHECK (completion_percentage BETWEEN 0 AND 100),
    
    -- 时间
    started_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at            TIMESTAMP,
    
    -- 防羞耻保护记录
    shame_mitigation_applied BOOLEAN DEFAULT FALSE,
    continuity_preserved    BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_behavior_sessions_user ON behavior_regulation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_behavior_sessions_time ON behavior_regulation_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_behavior_sessions_energy ON behavior_regulation_sessions(user_id, energy_level);

-- 14. 习惯状态机定义 (FSM - Causal Habit State Machine)
CREATE TABLE IF NOT EXISTS habit_state_machines (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 习惯定义
    habit_name          VARCHAR(200) NOT NULL,
    habit_description   TEXT,
    category            VARCHAR(50),  -- health/work/relationship/creative/spiritual
    
    -- 福格行为模型锚点
    deterministic_anchor    VARCHAR(200),  -- 硬编码锚点 (如"倒第一杯咖啡后")
    trigger_anchor_time     TIME,          -- 可选固定时间
    
    -- 三层状态机定义 (JSON存储各层配置)
    tier_green_config       JSONB,  -- 完整版
    tier_yellow_config      JSONB,  -- 标准版
    tier_red_config         JSONB,    -- 熔断版 (60秒原子动作)
    
    -- 代币系统配置
    token_green_yield       INTEGER DEFAULT 10,
    token_yellow_yield      INTEGER DEFAULT 5,
    token_red_yield         INTEGER DEFAULT 1,
    
    -- 状态
    is_active               BOOLEAN DEFAULT TRUE,
    current_streak_days     INTEGER DEFAULT 0,
    max_streak_days         INTEGER DEFAULT 0,
    total_executions        INTEGER DEFAULT 0,
    
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_execution_at       TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_habit_machines_user ON habit_state_machines(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_machines_active ON habit_state_machines(user_id, is_active);

-- 15. 习惯执行日志 (状态机运行记录)
CREATE TABLE IF NOT EXISTS habit_execution_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    habit_id        UUID REFERENCES habit_state_machines(id) ON DELETE CASCADE,
    
    -- 执行时的系统状态
    energy_level_at_execution   INTEGER CHECK (energy_level_at_execution BETWEEN 1 AND 5),
    selected_tier               VARCHAR(10),  -- Green/Yellow/Red
    
    -- 执行详情
    action_taken                TEXT,       -- 实际执行的动作
    execution_duration_seconds  INTEGER,
    tokens_earned               INTEGER,
    
    -- 结果
    was_completed               BOOLEAN DEFAULT FALSE,
    completion_percentage       INTEGER CHECK (completion_percentage BETWEEN 0 AND 100),
    
    -- 熔断保护记录
    circuit_breaker_triggered   BOOLEAN DEFAULT FALSE,
    anti_guilt_message_shown    BOOLEAN DEFAULT FALSE,
    
    -- 遥测数据
    mood_before     INTEGER CHECK (mood_before BETWEEN 1 AND 10),
    mood_after      INTEGER CHECK (mood_after BETWEEN 1 AND 10),
    
    executed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_habit_logs_user ON habit_execution_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs_habit ON habit_execution_logs(habit_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs_time ON habit_execution_logs(executed_at DESC);

-- 16. 用户代币账本 (Gamified Credit Ledger)
CREATE TABLE IF NOT EXISTS user_token_ledgers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    current_balance     INTEGER DEFAULT 0,
    lifetime_earned     INTEGER DEFAULT 0,
    lifetime_spent      INTEGER DEFAULT 0,
    
    -- 统计
    green_tier_count    INTEGER DEFAULT 0,
    yellow_tier_count   INTEGER DEFAULT 0,
    red_tier_count      INTEGER DEFAULT 0,
    
    last_updated        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_token_ledger_user ON user_token_ledgers(user_id);

-- 17. 代币交易记录
CREATE TABLE IF NOT EXISTS token_transactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    transaction_type    VARCHAR(20),  -- earn/spend/penalty/adjustment
    amount              INTEGER,
    balance_after       INTEGER,
    
    -- 关联
    habit_id            UUID REFERENCES habit_state_machines(id) ON DELETE SET NULL,
    habit_log_id        UUID REFERENCES habit_execution_logs(id) ON DELETE SET NULL,
    
    description         TEXT,
    
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_token_tx_user ON token_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_token_tx_time ON token_transactions(created_at DESC);

-- 为习惯表添加更新时间触发器
DROP TRIGGER IF EXISTS trg_habit_machines_updated ON habit_state_machines;
CREATE TRIGGER trg_habit_machines_updated 
BEFORE UPDATE ON habit_state_machines 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 行为调节系统视图
-- ============================================================

-- 用户习惯执行仪表盘
CREATE OR REPLACE VIEW user_habit_dashboard AS
SELECT 
    u.id as user_id,
    
    -- 活跃习惯数
    (SELECT COUNT(*) FROM habit_state_machines 
     WHERE user_id = u.id AND is_active = TRUE) as active_habits,
    
    -- 今日执行数
    (SELECT COUNT(*) FROM habit_execution_logs 
     WHERE user_id = u.id AND executed_at >= CURRENT_DATE) as today_executions,
    
    -- 当前连胜天数 (取最大)
    (SELECT MAX(current_streak_days) FROM habit_state_machines 
     WHERE user_id = u.id AND is_active = TRUE) as max_current_streak,
    
    -- 代币余额
    (SELECT current_balance FROM user_token_ledgers 
     WHERE user_id = u.id) as token_balance,
    
    -- 最近执行的习惯
    (SELECT habit_name FROM habit_execution_logs hel
     JOIN habit_state_machines hsm ON hel.habit_id = hsm.id
     WHERE hel.user_id = u.id 
     ORDER BY hel.executed_at DESC LIMIT 1) as last_habit_name,
    
    -- 熔断保护触发次数（本周）
    (SELECT COUNT(*) FROM habit_execution_logs 
     WHERE user_id = u.id 
     AND circuit_breaker_triggered = TRUE
     AND executed_at >= CURRENT_DATE - INTERVAL '7 days') as circuit_breaker_count

FROM users u;

-- ============================================================
-- 子系统三：执行力边缘引导系统 (Edge Execution Intervention)
-- ============================================================

-- 18. 执行力崩溃检测日志 (实时边缘监测)
CREATE TABLE IF NOT EXISTS execution_paralysis_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 检测到的崩溃信号
    paralysis_type  VARCHAR(50),  -- distraction/procrastination/anxiety_avoidance/emotional_collapse
    detected_signals JSONB[],     -- [{signal_type, description, intensity}]
    
    -- 原始任务上下文
    raw_backlog_task    TEXT,     -- 用户正在拖延的大任务
    edge_context        JSONB,    -- {hardware, location, time, battery, noise_level}
    
    -- 环境遥测
    tab_switch_count    INTEGER,  -- 检测到的高频切换次数
    idle_duration_seconds INTEGER, -- 无意义浏览/空闲时长
    window_thrashing    BOOLEAN DEFAULT FALSE,  -- 系统抖动标志
    
    -- 干预执行
    intervention_triggered  BOOLEAN DEFAULT FALSE,
    ignition_sequence_delivered TEXT, -- 2分钟点火序列内容
    user_responded      BOOLEAN DEFAULT FALSE,
    response_latency_seconds INTEGER, -- 用户响应延迟
    
    -- 结果
    ignition_completed  BOOLEAN DEFAULT FALSE,
    task_restarted      BOOLEAN DEFAULT FALSE,
    post_intervention_mood INTEGER CHECK (post_intervention_mood BETWEEN 1 AND 10),
    
    detected_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    intervened_at       TIMESTAMP,
    completed_at        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_paralysis_logs_user ON execution_paralysis_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_paralysis_logs_time ON execution_paralysis_logs(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_paralysis_logs_type ON execution_paralysis_logs(paralysis_type);

-- 19. 微调度器会话 (实时微干预追踪)
CREATE TABLE IF NOT EXISTS micro_scheduler_sessions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    paralysis_log_id UUID REFERENCES execution_paralysis_logs(id) ON DELETE SET NULL,
    
    -- 会话状态
    session_status  VARCHAR(20) DEFAULT 'active', -- active/paused/completed/abandoned
    
    -- 任务解耦链
    original_task       TEXT,       -- 原始大任务
    decoupled_chain     JSONB[],    -- [{step_id, action, duration_sec, completed}]
    current_step_index  INTEGER DEFAULT 0,
    
    -- 环境隔离配置
    context_isolation   JSONB,      -- {hidden_tabs, muted_notifications, focused_window}
    noise_floor_level   INTEGER CHECK (noise_floor_level BETWEEN 1 AND 10),
    
    -- 实时反馈
    telemetry_signals   JSONB[],    -- 用户反馈信号序列
    last_user_signal_at TIMESTAMP,
    
    -- 成果
    steps_completed     INTEGER DEFAULT 0,
    total_steps         INTEGER,
    micro_momentum_score INTEGER CHECK (micro_momentum_score BETWEEN 1 AND 100),
    
    started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_step_at        TIMESTAMP,
    completed_at        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_micro_scheduler_user ON micro_scheduler_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_micro_scheduler_status ON micro_scheduler_sessions(session_status);

-- 20. 执行意图模板库 (Implementation Intentions Library)
CREATE TABLE IF NOT EXISTS implementation_intentions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 意图定义 (If-Then 格式)
    intention_name      VARCHAR(200),
    if_trigger          TEXT,       -- "如果..." (环境锚点)
    then_action         TEXT,       -- "那么..." (原子动作)
    
    -- 上下文匹配条件
    applicable_contexts JSONB,      -- [{time_range, location, energy_level, device_type}]
    
    -- 效果统计
    usage_count         INTEGER DEFAULT 0,
    success_rate        INTEGER CHECK (success_rate BETWEEN 0 AND 100),
    avg_completion_time_seconds INTEGER,
    
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_intentions_user ON implementation_intentions(user_id);
CREATE INDEX IF NOT EXISTS idx_intentions_active ON implementation_intentions(user_id, is_active);

-- 21. 边缘干预效果追踪
CREATE TABLE IF NOT EXISTS edge_intervention_analytics (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 统计周期
    period_type     VARCHAR(20),  -- daily/weekly/monthly
    period_start    DATE,
    period_end      DATE,
    
    -- 崩溃指标
    paralysis_events_count      INTEGER DEFAULT 0,
    avg_detection_latency_seconds INTEGER, -- 从崩溃开始到检测到的平均时间
    
    -- 干预效果
    interventions_triggered     INTEGER DEFAULT 0,
    ignition_completion_rate    INTEGER CHECK (ignition_completion_rate BETWEEN 0 AND 100),
    task_restart_success_rate   INTEGER CHECK (task_restart_success_rate BETWEEN 0 AND 100),
    
    -- 系统健康度
    micro_momentum_avg          INTEGER CHECK (micro_momentum_avg BETWEEN 1 AND 100),
    continuity_preservation_score INTEGER CHECK (continuity_preservation_score BETWEEN 1 AND 100),
    
    -- 洞察
    top_paralysis_triggers      TEXT[],
    most_effective_ignitions    JSONB[],
    recommended_adjustments     TEXT[],
    
    calculated_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_edge_analytics_user ON edge_intervention_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_edge_analytics_period ON edge_intervention_analytics(user_id, period_type, period_start DESC);

-- 执行力系统仪表盘视图
CREATE OR REPLACE VIEW user_execution_dashboard AS
SELECT 
    u.id as user_id,
    
    -- 今日崩溃检测数
    (SELECT COUNT(*) FROM execution_paralysis_logs 
     WHERE user_id = u.id AND detected_at >= CURRENT_DATE) as today_paralysis_events,
    
    -- 活跃微调度器会话
    (SELECT COUNT(*) FROM micro_scheduler_sessions 
     WHERE user_id = u.id AND session_status = 'active') as active_micro_sessions,
    
    -- 总干预成功率
    (SELECT COALESCE(AVG(
        CASE WHEN ignition_completed THEN 100 ELSE 0 END
     ), 0)::INTEGER 
     FROM execution_paralysis_logs 
     WHERE user_id = u.id AND detected_at >= CURRENT_DATE - INTERVAL '7 days') as weekly_success_rate,
    
    -- 最常检测到的崩溃类型
    (SELECT paralysis_type FROM execution_paralysis_logs 
     WHERE user_id = u.id AND detected_at >= CURRENT_DATE - INTERVAL '7 days'
     GROUP BY paralysis_type ORDER BY COUNT(*) DESC LIMIT 1) as top_paralysis_type,
    
    -- 当前微动量分数
    (SELECT micro_momentum_score FROM micro_scheduler_sessions 
     WHERE user_id = u.id AND session_status = 'active'
     ORDER BY started_at DESC LIMIT 1) as current_momentum,
    
    -- 保存的执行意图数
    (SELECT COUNT(*) FROM implementation_intentions 
     WHERE user_id = u.id AND is_active = TRUE) as active_intentions

FROM users u;

-- ============================================================
-- 子系统四：身份认同重塑系统 (Identity Reinforcement Engine)
-- ============================================================

-- 22. 身份认同强化记录 (核心表)
CREATE TABLE IF NOT EXISTS identity_reinforcement_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 当前身份叙事 (基于 Dan McAdams 的叙事认同理论)
    current_narrative   TEXT,       -- "我是能够长期成长的人"
    -- 叙事类型说明：
    -- redemption: 救赎叙事 - 从负面经历中获得成长 (如："那次失败后我变得更强大")
    -- contamination: 污染叙事 - 负面事件持续影响 (需重点关注和干预)
    -- turning_point: 转折点叙事 - 人生方向改变的关键时刻
    -- stable: 稳定叙事 - 核心自我保持稳定
    narrative_type      VARCHAR(50), -- redemption/contamination/turning_point/stable
    
    -- 负面身份标签（需要解构的）
    negative_identity_labels TEXT[], -- ["我是懒惰的人", "我总是半途而废"]
    
    -- 新身份强化目标
    target_identity     TEXT,       -- "我是可以恢复的人"
    identity_category   VARCHAR(50), -- growth_continuity/resilience/stability/long_term/self_mastery
    
    -- 强化语言记录
    reinforcement_language  TEXT,   -- 系统生成的强化语句
    user_reflection     TEXT,       -- 用户对此的反思
    
    -- 强化效果
    reinforcement_strength  INTEGER CHECK (reinforcement_strength BETWEEN 1 AND 10),
    user_resonance      INTEGER CHECK (user_resonance BETWEEN 1 AND 10), -- 用户共鸣度
    
    -- 长期人格迁移追踪
    migration_direction     VARCHAR(50), -- toward_positive/stabilizing/recovering
    migration_progress      INTEGER CHECK (migration_progress BETWEEN 0 AND 100),
    
    -- 关联数据
    related_emotion_log_id  UUID REFERENCES emotion_logs(id) ON DELETE SET NULL,
    related_habit_id        UUID REFERENCES habit_state_machines(id) ON DELETE SET NULL,
    related_intervention_id UUID REFERENCES execution_paralysis_logs(id) ON DELETE SET NULL,
    
    reinforced_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_identity_logs_user ON identity_reinforcement_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_identity_logs_time ON identity_reinforcement_logs(reinforced_at DESC);
CREATE INDEX IF NOT EXISTS idx_identity_logs_category ON identity_reinforcement_logs(identity_category);

-- 23. 长期人格迁移追踪 (Personality Migration Tracker)
CREATE TABLE IF NOT EXISTS personality_migrations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 迁移维度
    migration_dimension VARCHAR(50), -- continuity/resilience/stability/long_term/self_mastery
    
    -- 起点与目标
    starting_identity   TEXT,       -- "我以前认为自己是..."
    target_identity     TEXT,       -- "我正在成为..."
    
    -- 迁移路径
    migration_path      JSONB[],    -- [{stage, milestone, achieved_at}]
    current_stage       INTEGER DEFAULT 0,
    
    -- 支撑证据
    supporting_evidence JSONB[],    -- [{event_type, description, impact_score}]
    
    -- 迁移状态
    migration_status    VARCHAR(20) DEFAULT 'in_progress', -- in_progress/completed/paused
    progress_percentage INTEGER CHECK (progress_percentage BETWEEN 0 AND 100),
    
    started_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estimated_completion TIMESTAMP,
    achieved_at         TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_migration_user ON personality_migrations(user_id);
CREATE INDEX IF NOT EXISTS idx_migration_dimension ON personality_migrations(user_id, migration_dimension);

-- 24. 身份认同仪表盘快照
CREATE OR REPLACE VIEW user_identity_dashboard AS
SELECT 
    u.id as user_id,
    
    -- 当前主导身份叙事
    (SELECT current_narrative FROM identity_reinforcement_logs 
     WHERE user_id = u.id ORDER BY reinforced_at DESC LIMIT 1) as current_identity_narrative,
    
    -- 负面标签数量（需要解构的）
    (SELECT COUNT(*) FROM (
        SELECT UNNEST(negative_identity_labels) as label 
        FROM identity_reinforcement_logs 
        WHERE user_id = u.id AND reinforced_at >= CURRENT_DATE - INTERVAL '30 days'
    ) subq) as active_negative_labels,
    
    -- 长期人格迁移进度（平均）
    (SELECT COALESCE(AVG(progress_percentage), 0)::INTEGER 
     FROM personality_migrations 
     WHERE user_id = u.id AND migration_status = 'in_progress') as avg_migration_progress,
    
    -- 最近强化记录数
    (SELECT COUNT(*) FROM identity_reinforcement_logs 
     WHERE user_id = u.id AND reinforced_at >= CURRENT_DATE - INTERVAL '7 days') as weekly_reinforcements,
    
    -- 身份认同清晰度分数
    (SELECT COALESCE(AVG(reinforcement_strength * user_resonance / 10.0), 50)::INTEGER 
     FROM identity_reinforcement_logs 
     WHERE user_id = u.id AND reinforced_at >= CURRENT_DATE - INTERVAL '30 days') as identity_clarity_score

FROM users u;

-- ============================================================
-- 全局状态机与数据总线架构 (System Integration Layer)
-- ============================================================

-- 25. 全局系统状态定义 (Personality OS State Machine)
CREATE TABLE IF NOT EXISTS system_state_definitions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    state_name      VARCHAR(50) UNIQUE NOT NULL, -- NORMAL/LOW_ENERGY/ANXIETY_ESCAPE/SHAME_COLLAPSE/RECOVERY/FLOW
    state_code      VARCHAR(20) UNIQUE NOT NULL, -- 状态代码
    
    -- 状态特征
    arousal_range       JSONB,  -- {min, max}
    valence_range       JSONB,  -- {min, max}
    energy_level_range  JSONB,  -- {min, max}
    
    -- 触发条件
    trigger_conditions  JSONB[], -- [{condition_type, threshold, description}]
    
    -- 行为策略
    behavior_strategy   TEXT,    -- 该状态下的行为策略描述
    task_intensity      VARCHAR(20), -- full/reduced/minimal/paused
    social_interaction  VARCHAR(20), -- encouraged/neutral/minimized
    
    -- Prompt特征
    prompt_tone         VARCHAR(20), -- supportive/neutral/firm/gentle
    prompt_focus        TEXT[],  -- 该状态下Prompt应关注的重点
    
    is_active           BOOLEAN DEFAULT TRUE
);

-- 初始化标准状态
INSERT INTO system_state_definitions (state_name, state_code, arousal_range, valence_range, energy_level_range, trigger_conditions, behavior_strategy, task_intensity, social_interaction, prompt_tone, prompt_focus) VALUES
('STATE_NORMAL', 'NORMAL', '{"min": 3, "max": 6}', '{"min": 0, "max": 7}', '{"min": 3, "max": 5}', '[{"condition": "energy >= 3", "threshold": 3}]', '标准执行模式', 'full', 'encouraged', 'supportive', ARRAY['常规任务', '习惯维护', '成长追踪']),
('STATE_LOW_ENERGY', 'LOW_ENERGY', '{"min": 2, "max": 4}', '{"min": -3, "max": 3}', '{"min": 1, "max": 2}', '[{"condition": "energy <= 2", "threshold": 2}]', '低功耗模式 - 熔断保护', 'minimal', 'neutral', 'gentle', ARRAY['最小动作', '连续性保持', '休息许可']),
('STATE_ANXIETY_ESCAPE', 'ANXIETY_ESCAPE', '{"min": 6, "max": 9}', '{"min": -7, "max": -2}', '{"min": 1, "max": 3}', '[{"condition": "anxiety_peak", "threshold": 7}]', '焦虑应对模式 - grounding优先', 'reduced', 'minimized', 'gentle', ARRAY[' grounding', '呼吸调节', '小步启动']),
('STATE_SHAME_COLLAPSE', 'SHAME_COLLAPSE', '{"min": 4, "max": 8}', '{"min": -9, "max": -5}', '{"min": 1, "max": 2}', '[{"condition": "self_negation", "threshold": 8}]', '羞耻恢复模式 - 重建安全基地', 'paused', 'minimized', 'gentle', ARRAY['身份强化', '负面标签解构', '自我慈悲']),
('STATE_RECOVERY', 'RECOVERY', '{"min": 3, "max": 6}', '{"min": -2, "max": 4}', '{"min": 2, "max": 4}', '[{"condition": "post_crisis", "threshold": 5}]', '恢复期 - 渐进式重启', 'reduced', 'neutral', 'supportive', ARRAY['渐进任务', '成功经验', '动量积累']),
('STATE_FLOW', 'FLOW', '{"min": 5, "max": 8}', '{"min": 5, "max": 10}', '{"min": 4, "max": 5}', '[{"condition": "momentum > 80", "threshold": 80}]', '心流模式 - 最大化产出', 'full', 'neutral', 'neutral', ARRAY['深度工作', '保持节奏', '避免打断'])
ON CONFLICT (state_name) DO NOTHING;

-- 26. 用户当前系统状态 (Personality OS Runtime State)
CREATE TABLE IF NOT EXISTS user_system_states (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    
    -- 当前状态
    current_state_code      VARCHAR(20) DEFAULT 'NORMAL',
    previous_state_code     VARCHAR(20),
    
    -- 状态迁移信息
    state_entered_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    state_duration_seconds  INTEGER DEFAULT 0,
    state_transition_reason TEXT,    -- 为什么进入这个状态
    
    -- 实时指标
    current_arousal         INTEGER CHECK (current_arousal BETWEEN 1 AND 10),
    current_valence         INTEGER CHECK (current_valence BETWEEN -10 AND 10),
    current_energy_level    INTEGER CHECK (current_energy_level BETWEEN 1 AND 5),
    
    -- 自动调节配置
    auto_regulation_enabled BOOLEAN DEFAULT TRUE,
    system_energy_override  INTEGER, -- 手动覆盖能耗等级
    
    -- 全局联动状态
    psychology_layer_active BOOLEAN DEFAULT TRUE,  -- L0-L4引擎
    behavior_layer_active   BOOLEAN DEFAULT TRUE,  -- 行为调节
    execution_layer_active  BOOLEAN DEFAULT TRUE,  -- 执行力引导
    identity_layer_active   BOOLEAN DEFAULT TRUE,  -- 身份认同
    
    last_updated            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_states_current ON user_system_states(user_id, current_state_code);

-- 27. 状态迁移历史日志 (State Transition Log)
CREATE TABLE IF NOT EXISTS state_transition_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    from_state_code     VARCHAR(20),
    to_state_code       VARCHAR(20),
    transition_trigger  TEXT,       -- 触发迁移的事件
    
    -- 迁移时的系统指标
    arousal_at_transition   INTEGER,
    valence_at_transition   INTEGER,
    energy_at_transition    INTEGER,
    
    -- 自动干预记录
    auto_interventions  JSONB[],    -- [{subsystem, action, result}]
    
    -- 数据总线信号
    signals_broadcast   JSONB[],    -- 广播给其他子系统的信号
    
    transitioned_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_state_transitions_user ON state_transition_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_state_transitions_time ON state_transition_logs(transitioned_at DESC);

-- 28. 全局数据总线事件 (Data Bus Events)
CREATE TABLE IF NOT EXISTS data_bus_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    event_type      VARCHAR(50),  -- telemetry/signal/broadcast/command
    event_source    VARCHAR(50),  -- psychology/behavior/execution/identity/system
    event_target    VARCHAR(50),  -- 目标子系统或 'all'
    
    -- 事件内容
    event_payload   JSONB,
    
    -- 优先级与时效
    priority        INTEGER DEFAULT 5, -- 1-10, 1最高
    ttl_seconds     INTEGER DEFAULT 300, -- 默认5分钟过期
    
    -- 处理状态
    is_processed    BOOLEAN DEFAULT FALSE,
    processed_at    TIMESTAMP,
    processed_by    VARCHAR(50), -- 处理该事件的子系统
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bus_events_unprocessed ON data_bus_events(is_processed, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS idx_bus_events_target ON data_bus_events(event_target, is_processed);

-- 29. 动态负载均衡器配置 (Dynamic Load Balancer)
CREATE TABLE IF NOT EXISTS dynamic_load_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- 当前认知载荷估算
    cognitive_load_score      INTEGER CHECK (cognitive_load_score BETWEEN 1 AND 10),
    emotional_load_score      INTEGER CHECK (emotional_load_score BETWEEN 1 AND 10),
    behavioral_load_score     INTEGER CHECK (behavioral_load_score BETWEEN 1 AND 10),
    
    -- 自动调节配置
    auto_override_enabled     BOOLEAN DEFAULT TRUE,
    red_tier_threshold        INTEGER DEFAULT 2, -- 能量低于此值强制熔断
    
    -- 当前全局设置
    current_system_energy_level INTEGER DEFAULT 3,
    current_task_intensity      VARCHAR(20) DEFAULT 'full',
    current_prompt_tone         VARCHAR(20) DEFAULT 'supportive',
    
    -- 熔断记录
    last_circuit_breaker_at     TIMESTAMP,
    circuit_breaker_count_7d    INTEGER DEFAULT 0,
    
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_load_config_user ON dynamic_load_configs(user_id);

-- ============================================================
-- 心理学分析仪表盘视图
-- ============================================================

CREATE OR REPLACE VIEW psychology_analysis_dashboard AS
SELECT 
    u.id as user_id,
    
    -- 分析统计
    (SELECT COUNT(*) FROM psychology_analysis_results 
     WHERE user_id = u.id) as total_analyses,
    
    (SELECT COUNT(*) FROM psychology_analysis_results 
     WHERE user_id = u.id AND created_at >= CURRENT_DATE) as today_analyses,
    
    (SELECT COUNT(*) FROM psychology_analysis_results 
     WHERE user_id = u.id AND is_crisis = TRUE) as total_crisis_detected,
    
    -- 最近分析
    (SELECT l0_driver_category FROM psychology_analysis_results 
     WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as recent_driver,
    
    (SELECT l1_distortion_type FROM psychology_analysis_results 
     WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as recent_distortion,
    
    (SELECT l2_state_name FROM psychology_analysis_results 
     WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as recent_state,
    
    (SELECT synthesis_risk_level FROM psychology_analysis_results 
     WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as recent_risk_level,
    
    -- 模式统计（近30天）
    (SELECT mode() WITHIN GROUP (ORDER BY l0_driver_category) 
     FROM psychology_analysis_results 
     WHERE user_id = u.id AND created_at >= CURRENT_DATE - INTERVAL '30 days') as dominant_driver,
    
    (SELECT ROUND(AVG(l2_arousal_level), 1) FROM psychology_analysis_results 
     WHERE user_id = u.id AND created_at >= CURRENT_DATE - INTERVAL '7 days') as avg_arousal_7d,
    
    (SELECT ROUND(AVG(intensity), 1) FROM psychology_analysis_results 
     WHERE user_id = u.id AND created_at >= CURRENT_DATE - INTERVAL '7 days') as avg_intensity_7d,
    
    -- 最近一次分析时间
    (SELECT MAX(created_at) FROM psychology_analysis_results 
     WHERE user_id = u.id) as last_analysis_at

FROM users u;

-- ============================================================
-- Personality OS 整合仪表盘
-- ============================================================

CREATE OR REPLACE VIEW personality_os_dashboard AS
SELECT 
    u.id as user_id,
    
    -- 当前系统状态
    (SELECT current_state_code FROM user_system_states WHERE user_id = u.id) as current_state,
    (SELECT current_energy_level FROM user_system_states WHERE user_id = u.id) as current_energy,
    
    -- 负载均衡器状态
    (SELECT current_system_energy_level FROM dynamic_load_configs WHERE user_id = u.id) as system_energy_level,
    (SELECT cognitive_load_score FROM dynamic_load_configs WHERE user_id = u.id) as cognitive_load,
    
    -- 各子系统活跃度
    (SELECT psychology_layer_active FROM user_system_states WHERE user_id = u.id) as l0_l4_active,
    (SELECT behavior_layer_active FROM user_system_states WHERE user_id = u.id) as behavior_active,
    (SELECT execution_layer_active FROM user_system_states WHERE user_id = u.id) as execution_active,
    (SELECT identity_layer_active FROM user_system_states WHERE user_id = u.id) as identity_active,
    
    -- 今日事件统计
    (SELECT COUNT(*) FROM data_bus_events 
     WHERE event_payload->>'user_id' = u.id::text 
     AND created_at >= CURRENT_DATE) as today_bus_events,
    
    -- 熔断次数
    (SELECT circuit_breaker_count_7d FROM dynamic_load_configs WHERE user_id = u.id) as weekly_circuit_breakers,
    
    -- 综合健康度
    (SELECT COALESCE(
        (SELECT identity_clarity_score FROM user_identity_dashboard WHERE user_id = u.id), 50
    )) as identity_health,
    (SELECT COALESCE(
        (SELECT current_momentum FROM user_execution_dashboard WHERE user_id = u.id), 50
    )) as execution_health,
    (SELECT COALESCE(
        (SELECT token_balance FROM user_habit_dashboard WHERE user_id = u.id), 0
    )) as behavior_health

FROM users u;

-- ============================================================
-- 30. 软删除支持 (Soft Delete)
-- ============================================================

-- 为所有业务表添加软删除字段（使用DO块批量处理）
DO $$
DECLARE
    tables_list TEXT[] := ARRAY[
        'emotion_logs', 'psychology_analysis_results', 'personal_notes',
        'behavior_regulation_sessions', 'habit_state_machines', 'habit_tokens',
        'execution_paralysis_logs', 'micro_scheduler_sessions', 'ignition_logs',
        'identity_reinforcement_logs', 'identity_deconstruction_logs',
        'personality_migrations', 'behavioral_experiments', 'cognitive_schemas',
        'personality_drivers', 'psychological_states', 'data_bus_events'
    ];
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY tables_list
    LOOP
        EXECUTE format(
            'ALTER TABLE %I ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP DEFAULT NULL;',
            tbl
        );
        EXECUTE format(
            'ALTER TABLE %I ADD COLUMN IF NOT EXISTS deleted_by INTEGER DEFAULT NULL;',
            tbl
        );
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_%s_deleted_at ON %I(deleted_at) WHERE deleted_at IS NULL;',
            tbl, tbl
        );
    END LOOP;
END $$;

-- ============================================================
-- 31. 数据版本控制 (Data Versioning)
-- ============================================================

CREATE TABLE IF NOT EXISTS data_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name      VARCHAR(100) NOT NULL,
    record_id       UUID NOT NULL,
    version         INTEGER NOT NULL,
    data_snapshot   JSONB NOT NULL,      -- 完整数据快照
    changed_fields  TEXT[],              -- 变更的字段列表
    change_type     VARCHAR(20),         -- CREATE/UPDATE/DELETE
    change_reason   VARCHAR(200),        -- 变更原因
    changed_by      INTEGER REFERENCES users(id),
    changed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(table_name, record_id, version)
);

CREATE INDEX IF NOT EXISTS idx_data_versions_record ON data_versions(table_name, record_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_data_versions_changed_at ON data_versions(changed_at DESC);

-- 版本号自动递增触发器函数
CREATE OR REPLACE FUNCTION increment_version()
RETURNS TRIGGER AS $$
DECLARE
    next_version INTEGER;
BEGIN
    SELECT COALESCE(MAX(version), 0) + 1 INTO next_version
    FROM data_versions
    WHERE table_name = TG_TABLE_NAME AND record_id = NEW.id;
    
    NEW.version := next_version;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 32. 审计日志表 (Audit Logging)
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name      VARCHAR(100) NOT NULL,
    record_id       UUID,
    action          VARCHAR(20) NOT NULL,    -- INSERT/UPDATE/DELETE/SELECT
    old_data        JSONB,
    new_data        JSONB,
    changed_fields  TEXT[],                  -- 变更的字段
    user_id         INTEGER REFERENCES users(id),
    user_ip         INET,
    user_agent      TEXT,
    session_id      VARCHAR(255),
    request_id      VARCHAR(255),            -- 请求追踪ID
    executed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_table ON audit_logs(table_name, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_record ON audit_logs(record_id, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_request ON audit_logs(request_id);

-- 审计日志触发器函数
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    old_json JSONB;
    new_json JSONB;
    changed_fields TEXT[] := ARRAY[]::TEXT[];
    key TEXT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        old_json := to_jsonb(OLD);
        
        INSERT INTO audit_logs (
            table_name, record_id, action, old_data,
            user_id, executed_at
        ) VALUES (
            TG_TABLE_NAME, OLD.id, 'DELETE', old_json,
            (current_setting('app.current_user_id', true))::INTEGER,
            CURRENT_TIMESTAMP
        );
        
        RETURN OLD;
        
    ELSIF TG_OP = 'INSERT' THEN
        new_json := to_jsonb(NEW);
        
        INSERT INTO audit_logs (
            table_name, record_id, action, new_data,
            user_id, executed_at
        ) VALUES (
            TG_TABLE_NAME, NEW.id, 'INSERT', new_json,
            (current_setting('app.current_user_id', true))::INTEGER,
            CURRENT_TIMESTAMP
        );
        
        -- 同时创建版本记录
        INSERT INTO data_versions (
            table_name, record_id, version, data_snapshot,
            change_type, changed_by, changed_at
        ) VALUES (
            TG_TABLE_NAME, NEW.id, 1, new_json,
            'CREATE', 
            (current_setting('app.current_user_id', true))::INTEGER,
            CURRENT_TIMESTAMP
        );
        
        RETURN NEW;
        
    ELSIF TG_OP = 'UPDATE' THEN
        old_json := to_jsonb(OLD);
        new_json := to_jsonb(NEW);
        
        -- 检测变更的字段
        FOR key IN SELECT jsonb_object_keys(new_json)
        LOOP
            IF old_json->key IS DISTINCT FROM new_json->key THEN
                changed_fields := array_append(changed_fields, key);
            END IF;
        END LOOP;
        
        INSERT INTO audit_logs (
            table_name, record_id, action, old_data, new_data,
            changed_fields, user_id, executed_at
        ) VALUES (
            TG_TABLE_NAME, NEW.id, 'UPDATE', old_json, new_json,
            changed_fields,
            (current_setting('app.current_user_id', true))::INTEGER,
            CURRENT_TIMESTAMP
        );
        
        -- 创建版本记录
        INSERT INTO data_versions (
            table_name, record_id, version, data_snapshot,
            changed_fields, change_type, changed_by, changed_at
        ) SELECT
            TG_TABLE_NAME, NEW.id, 
            COALESCE(MAX(version), 0) + 1,
            new_json, changed_fields, 'UPDATE',
            (current_setting('app.current_user_id', true))::INTEGER,
            CURRENT_TIMESTAMP
        FROM data_versions
        WHERE table_name = TG_TABLE_NAME AND record_id = NEW.id;
        
        RETURN NEW;
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 为关键表启用审计日志（示例：emotion_logs）
DROP TRIGGER IF EXISTS emotion_logs_audit ON emotion_logs;
CREATE TRIGGER emotion_logs_audit
    AFTER INSERT OR UPDATE OR DELETE ON emotion_logs
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

-- ============================================================
-- 33. 数据归档表 (Data Archiving for GDPR)
-- ============================================================

CREATE TABLE IF NOT EXISTS archived_data (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_table  VARCHAR(100) NOT NULL,
    original_id     UUID NOT NULL,
    user_id         INTEGER REFERENCES users(id),
    data_payload    JSONB NOT NULL,
    archived_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archive_reason  VARCHAR(100),           -- USER_REQUEST/SYSTEM/RETENTION
    retention_until TIMESTAMP,              -- 数据保留截止日期
    anonymized      BOOLEAN DEFAULT FALSE -- 是否已匿名化
);

CREATE INDEX IF NOT EXISTS idx_archived_data_user ON archived_data(user_id, archived_at DESC);
CREATE INDEX IF NOT EXISTS idx_archived_data_retention ON archived_data(retention_until) WHERE retention_until IS NOT NULL;

-- ============================================================
-- 子系统四：用户人格画像标签系统 (Persona Tag System)
-- ============================================================

-- 34. 标签库（预定义 + 用户自定义）
CREATE TABLE IF NOT EXISTS persona_tags (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_name        VARCHAR(100) NOT NULL,
    tag_category    VARCHAR(50) NOT NULL,  -- emotion/behavior/habit/personality/cognition/relationship/value
    tag_type        VARCHAR(20) DEFAULT 'auto',  -- auto/manual/system
    description     TEXT,
    synonyms        TEXT[],
    keywords        TEXT[],
    weight_default  FLOAT DEFAULT 1.0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_persona_tags_name ON persona_tags(tag_name, tag_category);
CREATE INDEX IF NOT EXISTS idx_persona_tags_category ON persona_tags(tag_category);

-- 35. 用户标签关联（带权重和频次）
CREATE TABLE IF NOT EXISTS user_persona_tags (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tag_id          UUID REFERENCES persona_tags(id) ON DELETE CASCADE,
    
    weight          FLOAT DEFAULT 1.0,  -- 当前权重 0-10
    frequency       INTEGER DEFAULT 1,
    
    source_type     VARCHAR(50),  -- emotion_log/decision/behavior_regulation/habit_creation/manual
    source_id       UUID,
    
    first_seen_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    confidence      FLOAT DEFAULT 0.8  -- 0-1 标签抽取置信度
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_persona_tags_unique ON user_persona_tags(user_id, tag_id, source_type);

CREATE INDEX IF NOT EXISTS idx_user_persona_tags_user ON user_persona_tags(user_id);
CREATE INDEX IF NOT EXISTS idx_user_persona_tags_tag ON user_persona_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_user_persona_tags_weight ON user_persona_tags(user_id, weight DESC);

-- 36. 用户人格画像（聚合表）
CREATE TABLE IF NOT EXISTS user_persona_profiles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    tag_cloud       JSONB DEFAULT '{}',
    emotion_dominance JSONB DEFAULT '{}',
    behavior_patterns JSONB DEFAULT '{}',
    habit_strength  JSONB DEFAULT '{}',
    personality_vector JSONB DEFAULT '{}',
    
    stability_score FLOAT,
    resilience_score FLOAT,
    growth_trend    VARCHAR(20),  -- improving/stable/declining
    risk_level      VARCHAR(20),    -- low/moderate/high
    
    profile_version INTEGER DEFAULT 1,
    computed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_persona_profiles_user ON user_persona_profiles(user_id);

DROP TRIGGER IF EXISTS trg_user_persona_profiles_updated ON user_persona_profiles;
CREATE TRIGGER trg_user_persona_profiles_updated
BEFORE UPDATE ON user_persona_profiles
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 37. 标签抽取规则库（关键词匹配）
CREATE TABLE IF NOT EXISTS tag_extraction_rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_id          UUID REFERENCES persona_tags(id) ON DELETE CASCADE,
    pattern_type    VARCHAR(20) DEFAULT 'keyword',  -- keyword/regex/semantic
    pattern_value   TEXT NOT NULL,
    weight_boost    FLOAT DEFAULT 1.0,
    context_hint    VARCHAR(50),  -- 适用上下文: emotion/decision/behavior/habit
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tag_extraction_rules_tag ON tag_extraction_rules(tag_id);
CREATE INDEX IF NOT EXISTS idx_tag_extraction_rules_pattern ON tag_extraction_rules(pattern_value);

-- ============================================================
-- 初始化说明
-- ============================================================
-- 执行顺序：
-- 1. 先执行 db_init.sql（基础用户表）
-- 2. 再执行本文件（心理系统完整schema）
-- 3. 所有视图和整合层将自动创建
-- 
-- 使用方式：
-- psql $DATABASE_URL -f backend/psychology_schema.sql
-- ============================================================
