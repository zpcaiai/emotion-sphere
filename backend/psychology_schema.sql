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

CREATE INDEX idx_emotion_logs_user_id ON emotion_logs(user_id);
CREATE INDEX idx_emotion_logs_occurred_at ON emotion_logs(occurred_at DESC);
CREATE INDEX idx_emotion_logs_emotion_tags ON emotion_logs USING GIN(emotion_tags);

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
    
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzed_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_personality_drivers_user_id ON personality_drivers(user_id);
CREATE INDEX idx_personality_drivers_log_id ON personality_drivers(log_id);
CREATE INDEX idx_personality_drivers_category ON personality_drivers(driver_category);

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

CREATE INDEX idx_behavioral_triggers_user_id ON behavioral_triggers(user_id);
CREATE INDEX idx_behavioral_triggers_type ON behavioral_triggers(trigger_type);

-- ============================================================
-- L1: 行为调节引擎 - 认知图式与干预
-- ============================================================

-- 4. 认知图式表（Schema Therapy + REBT）
CREATE TABLE IF NOT EXISTS cognitive_schemas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- ABC 分析
    schema_name     VARCHAR(100) NOT NULL,
    distortion_type VARCHAR(50),  -- Perfectionism/Catastrophizing/Impostor_Syndrome/Emotional_Reasoning/Overgeneralization
    
    activating_event   TEXT,
    consequence_emotional   TEXT,
    consequence_behavioral  TEXT,
    
    -- 核心信念
    core_belief     TEXT,
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

CREATE INDEX idx_cognitive_schemas_user_id ON cognitive_schemas(user_id);
CREATE INDEX idx_cognitive_schemas_distortion ON cognitive_schemas(distortion_type);
CREATE INDEX idx_cognitive_schemas_active ON cognitive_schemas(user_id, is_active);

-- 5. 行为实验表（CBT Behavioral Experiments）
CREATE TABLE IF NOT EXISTS behavioral_experiments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    schema_id       UUID REFERENCES cognitive_schemas(id) ON DELETE SET NULL,
    
    -- 实验定义
    experiment_id   VARCHAR(100) UNIQUE,  -- exp_2026_cat_001 格式
    title           VARCHAR(200) NOT NULL,
    hypothesis_to_test TEXT,      -- 要证伪的假设
    
    -- 实验设计
    counter_behavioral_action TEXT, -- 具体低摩擦行动
    difficulty_level    INTEGER CHECK (difficulty_level BETWEEN 1 AND 5),
    estimated_duration_minutes INTEGER, -- 预计耗时
    
    -- 二元遥测指标
    binary_telemetry_metric TEXT, -- "Did someone scold you? Yes/No"
    success_criteria    JSONB,    -- {metric, threshold, operator}
    
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

CREATE INDEX idx_behavioral_experiments_user_id ON behavioral_experiments(user_id);
CREATE INDEX idx_behavioral_experiments_schema ON behavioral_experiments(schema_id);
CREATE INDEX idx_behavioral_experiments_status ON behavioral_experiments(status);
CREATE INDEX idx_behavioral_experiments_scheduled ON behavioral_experiments(scheduled_at);

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

CREATE INDEX idx_psychological_states_user_id ON psychological_states(user_id);
CREATE INDEX idx_psychological_states_captured ON psychological_states(captured_at DESC);
CREATE INDEX idx_psychological_states_level ON psychological_states(state_level);

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

CREATE INDEX idx_intervention_logs_user_id ON intervention_logs(user_id);
CREATE INDEX idx_intervention_logs_delivered ON intervention_logs(delivered_at DESC);

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

CREATE INDEX idx_identity_narratives_user_id ON identity_narratives(user_id);
CREATE INDEX idx_identity_narratives_current ON identity_narratives(user_id, is_current) WHERE is_current = TRUE;

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

CREATE INDEX idx_self_concept_user_id ON self_concept_models(user_id);
CREATE INDEX idx_self_concept_assessed ON self_concept_models(assessed_at DESC);

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

CREATE INDEX idx_growth_trajectories_user_id ON growth_trajectories(user_id);
CREATE INDEX idx_growth_trajectories_period ON growth_trajectories(user_id, period_type, period_start DESC);

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

CREATE INDEX idx_pattern_recognitions_user_id ON pattern_recognitions(user_id);
CREATE INDEX idx_pattern_recognitions_type ON pattern_recognitions(pattern_type);

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

CREATE INDEX idx_memory_consolidations_user_id ON memory_consolidations(user_id);
CREATE INDEX idx_memory_consolidations_type ON memory_consolidations(memory_type);
CREATE INDEX idx_memory_consolidations_strength ON memory_consolidations(user_id, memory_strength DESC);

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

CREATE INDEX idx_behavior_sessions_user ON behavior_regulation_sessions(user_id);
CREATE INDEX idx_behavior_sessions_time ON behavior_regulation_sessions(started_at DESC);
CREATE INDEX idx_behavior_sessions_energy ON behavior_regulation_sessions(user_id, energy_level);

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

CREATE INDEX idx_habit_machines_user ON habit_state_machines(user_id);
CREATE INDEX idx_habit_machines_active ON habit_state_machines(user_id, is_active);

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

CREATE INDEX idx_habit_logs_user ON habit_execution_logs(user_id);
CREATE INDEX idx_habit_logs_habit ON habit_execution_logs(habit_id);
CREATE INDEX idx_habit_logs_time ON habit_execution_logs(executed_at DESC);

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

CREATE UNIQUE INDEX idx_token_ledger_user ON user_token_ledgers(user_id);

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

CREATE INDEX idx_token_tx_user ON token_transactions(user_id);
CREATE INDEX idx_token_tx_time ON token_transactions(created_at DESC);

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
-- 初始化说明
-- ============================================================
-- 执行顺序：
-- 1. 先执行 db_init.sql（基础用户表）
-- 2. 再执行本文件（心理系统完整schema）
-- 
-- 使用方式：
-- psql $DATABASE_URL -f backend/psychology_schema.sql
-- ============================================================
