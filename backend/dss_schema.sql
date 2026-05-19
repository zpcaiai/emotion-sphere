-- ============================================================================
-- DSS (Decision Support System) Core Schema - 决策支持系统数据表
-- 去宗教化版本 - 保留功能，替换宗教术语
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- DSS Core Tables - 决策支持核心表
-- ============================================================================

-- Users table (reference to existing users table)
CREATE TABLE IF NOT EXISTS dss_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    avatar_url TEXT,
    inner_maturity_score INTEGER CHECK (inner_maturity_score BETWEEN 0 AND 10) DEFAULT 5,
    discernment_history_count INTEGER DEFAULT 0,
    personality_type VARCHAR(20),
    decision_style VARCHAR(20),
    email_notifications BOOLEAN DEFAULT true,
    weekly_digest BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Decision Events - 决策事件表
CREATE TABLE IF NOT EXISTS dss_decision_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL CHECK (category IN (
        'career', 'education', 'calling', 'relationship', 'family', 'community',
        'financial', 'housing', 'possessions', 'health', 'mental', 'temptation',
        'spiritual', 'ministry', 'time', 'lifestyle', 'boundary', 'crisis',
        'transition', 'loss', 'ethics', 'media', 'other'
    )),
    urgency INTEGER CHECK (urgency BETWEEN 1 AND 5) DEFAULT 3,
    importance INTEGER CHECK (importance BETWEEN 1 AND 5) DEFAULT 3,
    
    -- 12维度状态快照
    stress_level INTEGER CHECK (stress_level BETWEEN 0 AND 10) DEFAULT 5,
    anxiety_level INTEGER CHECK (anxiety_level BETWEEN 0 AND 10) DEFAULT 5,
    fatigue_level INTEGER CHECK (fatigue_level BETWEEN 0 AND 10) DEFAULT 5,
    spiritual_dryness INTEGER CHECK (spiritual_dryness BETWEEN 0 AND 10) DEFAULT 5, -- UI中显示为"内心枯竭"
    emotional_stability INTEGER CHECK (emotional_stability BETWEEN 0 AND 10) DEFAULT 5,
    physical_health INTEGER CHECK (physical_health BETWEEN 0 AND 10) DEFAULT 5,
    sleep_quality INTEGER CHECK (sleep_quality BETWEEN 0 AND 10) DEFAULT 5,
    social_connection INTEGER CHECK (social_connection BETWEEN 0 AND 10) DEFAULT 5,
    financial_pressure INTEGER CHECK (financial_pressure BETWEEN 0 AND 10) DEFAULT 5,
    cognitive_clarity INTEGER CHECK (cognitive_clarity BETWEEN 0 AND 10) DEFAULT 5,
    identity_confusion INTEGER CHECK (identity_confusion BETWEEN 0 AND 10) DEFAULT 5,
    moral_tension INTEGER CHECK (moral_tension BETWEEN 0 AND 10) DEFAULT 5,
    
    -- 分析结果
    motive_analysis JSONB,
    discernment_result JSONB,
    guidance JSONB,
    emotion_logs JSONB DEFAULT '[]',
    context_factors JSONB,
    
    -- 状态
    status VARCHAR(20) DEFAULT 'analyzing' CHECK (status IN ('analyzing', 'guided', 'decided', 'reviewed', 'archived')),
    final_decision TEXT,
    outcome_status VARCHAR(20) DEFAULT 'pending' CHECK (outcome_status IN ('pending', 'implemented', 'reversed', 'abandoned', 'ongoing')),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analyzed_at TIMESTAMP WITH TIME ZONE,
    decided_at TIMESTAMP WITH TIME ZONE,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE
);

-- 决策事件索引
CREATE INDEX IF NOT EXISTS idx_dss_decisions_user ON dss_decision_events(user_id);
CREATE INDEX IF NOT EXISTS idx_dss_decisions_category ON dss_decision_events(category);
CREATE INDEX IF NOT EXISTS idx_dss_decisions_status ON dss_decision_events(status);
CREATE INDEX IF NOT EXISTS idx_dss_decisions_created ON dss_decision_events(created_at DESC);

-- Review Logs - 决策回顾表
CREATE TABLE IF NOT EXISTS dss_review_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES dss_decision_events(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    outcome_description TEXT NOT NULL,
    outcome_category VARCHAR(20) CHECK (outcome_category IN ('positive', 'negative', 'mixed', 'neutral', 'ongoing', 'unclear')),
    peace_level INTEGER CHECK (peace_level BETWEEN -5 AND 5),
    regret_level INTEGER CHECK (regret_level BETWEEN 0 AND 10),
    satisfaction_level INTEGER CHECK (satisfaction_level BETWEEN 0 AND 10),
    followed_guidance BOOLEAN,
    guidance_accuracy INTEGER CHECK (guidance_accuracy BETWEEN 0 AND 10),
    growth_impact TEXT,  -- renamed from character_impact
    lessons_learned TEXT,
    relational_impact TEXT,
    what_went_well TEXT[],
    what_could_improve TEXT[],
    what_i_learned TEXT,
    review_date DATE NOT NULL,
    days_since_decision INTEGER,
    would_decide_differently BOOLEAN,
    what_would_change TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dss_reviews_decision ON dss_review_logs(decision_id);
CREATE INDEX IF NOT EXISTS idx_dss_reviews_user ON dss_review_logs(user_id);

-- Wisdom Principles - 智慧原则库
CREATE TABLE IF NOT EXISTS dss_wisdom_principles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    principle_text TEXT NOT NULL,
    principle_summary VARCHAR(200),
    reference VARCHAR(100),  -- renamed from scripture_reference
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50),
    applicable_contexts TEXT[],
    applicable_emotions TEXT[],
    teaching_notes TEXT,
    historical_examples TEXT[],
    counter_principles UUID[],
    search_keywords TEXT[],
    reference_count INTEGER DEFAULT 0,
    last_referenced_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dss_principles_category ON dss_wisdom_principles(category);
CREATE INDEX IF NOT EXISTS idx_dss_principles_active ON dss_wisdom_principles(is_active) WHERE is_active = TRUE;

-- Decision-Principles Junction - 决策与原则关联表
CREATE TABLE IF NOT EXISTS dss_decision_principles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES dss_decision_events(id) ON DELETE CASCADE,
    principle_id UUID NOT NULL REFERENCES dss_wisdom_principles(id) ON DELETE CASCADE,
    relationship_type VARCHAR(20) CHECK (relationship_type IN ('supporting', 'conflicting', 'neutral', 'primary', 'secondary')) DEFAULT 'supporting',
    relevance_score DECIMAL(3,2) CHECK (relevance_score BETWEEN 0.0 AND 1.0),
    application_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(decision_id, principle_id)
);

-- User Patterns - 用户决策模式识别
CREATE TABLE IF NOT EXISTS dss_user_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_name VARCHAR(100) NOT NULL,
    pattern_description TEXT,
    first_observed_at TIMESTAMP WITH TIME ZONE,
    last_observed_at TIMESTAMP WITH TIME ZONE,
    occurrence_count INTEGER DEFAULT 1,
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    related_decision_ids UUID[],
    pattern_data JSONB,
    is_active BOOLEAN DEFAULT true,
    is_addressed BOOLEAN DEFAULT false,
    addressed_how TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dss_patterns_user ON dss_user_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_dss_patterns_type ON dss_user_patterns(pattern_type);

-- ============================================================================
-- 触发器函数
-- ============================================================================

-- 自动更新时间戳函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有需要自动更新的表创建触发器
DROP TRIGGER IF EXISTS trg_dss_users_updated ON dss_users;
CREATE TRIGGER trg_dss_users_updated 
BEFORE UPDATE ON dss_users 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_dss_decisions_updated ON dss_decision_events;
CREATE TRIGGER trg_dss_decisions_updated 
BEFORE UPDATE ON dss_decision_events 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_dss_reviews_updated ON dss_review_logs;
CREATE TRIGGER trg_dss_reviews_updated 
BEFORE UPDATE ON dss_review_logs 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_dss_principles_updated ON dss_wisdom_principles;
CREATE TRIGGER trg_dss_principles_updated 
BEFORE UPDATE ON dss_wisdom_principles 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_dss_patterns_updated ON dss_user_patterns;
CREATE TRIGGER trg_dss_patterns_updated 
BEFORE UPDATE ON dss_user_patterns 
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 初始化默认智慧原则
-- ============================================================================

INSERT INTO dss_wisdom_principles (principle_text, reference, category, search_keywords) VALUES
('凡事察验，善美的要持守', '智慧格言', 'discernment', ARRAY['察验', '分辨', '善美']),
('你要保守你心，胜过保守一切', '内心守护', 'heart_guarding', ARRAY['保守', '内心', '守护']),
('不要恐惧，因为我与你同在', '勇气支持', 'fear', ARRAY['恐惧', '勇气', '支持']),
('看别人比自己强', '谦逊智慧', 'humility', ARRAY['谦逊', '看人', '自己']),
('凭果子认出他们来', '结果验证', 'judgment', ARRAY['果子', '结果', '认出']),
('爱比成功更高', '爱的优先', 'love', ARRAY['爱', '成功', '优先']),
('真理比舒适更重要', '真实勇气', 'truth', ARRAY['真理', '舒适', '勇气']),
('谦卑在智慧以先', '谦逊智慧', 'wisdom', ARRAY['谦卑', '智慧']),
('安息是内在操练', '休息重要', 'rest', ARRAY['安息', '休息', '操练']),
('听从良知，不随波逐流', '独立判断', 'integrity', ARRAY['良知', '听从', '独立']),
('愿意受苦而不愿违背良知', '坚守原则', 'sacrifice', ARRAY['受苦', '良知', '坚守']),
('患难生忍耐，忍耐生老练', '成长历练', 'patience', ARRAY['患难', '忍耐', '成长']),
('不为明天忧虑', '活在当下', 'anxiety', ARRAY['忧虑', '明天', '当下']),
('在压力中保持平静', '内在平静', 'peace', ARRAY['压力', '平静', '内在']),
('不可为恶所胜，反要以善胜恶', '善胜恶', 'victory', ARRAY['善', '恶', '胜利'])
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 视图
-- ============================================================================

-- 用户决策统计视图
CREATE OR REPLACE VIEW dss_user_decision_stats AS
SELECT 
    user_id,
    COUNT(*) as total_decisions,
    COUNT(*) FILTER (WHERE status = 'guided') as analyzed_decisions,
    COUNT(*) FILTER (WHERE status = 'reviewed') as reviewed_decisions,
    COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as recent_decisions,
    MAX(created_at) as last_decision_at
FROM dss_decision_events
WHERE deleted_at IS NULL
GROUP BY user_id;

-- 决策类别统计视图
CREATE OR REPLACE VIEW dss_category_stats AS
SELECT 
    category,
    COUNT(*) as total_count,
    AVG((motive_analysis->>'fear_driven_score')::float) as avg_fear_score,
    AVG((motive_analysis->>'love_driven_score')::float) as avg_love_score,
    AVG((discernment_result->>'confidence')::float) as avg_confidence
FROM dss_decision_events
WHERE created_at > NOW() - INTERVAL '90 days'
GROUP BY category;
