-- ============================================================
-- Emotion Sphere — full schema + linked test data
-- Each CREATE TABLE and each table's INSERTs in separate transactions
-- Tables ordered by FK dependency (parents before children)
-- psql $DATABASE_URL -f backend/seed_all.sql
-- ============================================================

-- Setup: extensions and functions
BEGIN;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END;$$ LANGUAGE plpgsql;
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END;$$ LANGUAGE plpgsql;
COMMIT;

-- ============================================================
-- Schema Creation (one transaction per table, dependency-ordered)
-- ============================================================

-- Table: users
BEGIN;
CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE, nickname VARCHAR(100) NOT NULL DEFAULT '', avatar VARCHAR(500) DEFAULT '', openid VARCHAR(255) UNIQUE, unionid VARCHAR(255) UNIQUE, login_type VARCHAR(20) NOT NULL DEFAULT 'email', password_hash VARCHAR(255) DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users (LOWER(email)) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_openid ON users(openid) WHERE openid IS NOT NULL;
DROP TRIGGER IF EXISTS trg_users_updated_at ON users; CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
COMMIT;

-- Table: security_audit
BEGIN;
CREATE TABLE IF NOT EXISTS security_audit (id SERIAL PRIMARY KEY, event_type VARCHAR(50) NOT NULL, email VARCHAR(255), ip_address INET, user_agent TEXT DEFAULT '', details JSONB DEFAULT '{}', success BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_security_audit_email ON security_audit(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_security_audit_created ON security_audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_audit_event_type ON security_audit(event_type);
COMMIT;

-- Table: user_tokens
BEGIN;
CREATE TABLE IF NOT EXISTS user_tokens (token VARCHAR(255) PRIMARY KEY, email VARCHAR(255) NOT NULL, data JSONB NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, ip_address INET);
CREATE INDEX IF NOT EXISTS idx_user_tokens_email ON user_tokens(email);
CREATE INDEX IF NOT EXISTS idx_user_tokens_expires ON user_tokens(expires_at);
COMMIT;

-- Table: system_state_definitions
BEGIN;
CREATE TABLE IF NOT EXISTS system_state_definitions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), state_name VARCHAR(50) UNIQUE NOT NULL, state_code VARCHAR(20) UNIQUE NOT NULL, arousal_range JSONB, valence_range JSONB, energy_level_range JSONB, trigger_conditions JSONB[], behavior_strategy TEXT, task_intensity VARCHAR(20), social_interaction VARCHAR(20), prompt_tone VARCHAR(20), prompt_focus TEXT[], is_active BOOLEAN DEFAULT TRUE);
COMMIT;

-- Table: data_bus_events
BEGIN;
CREATE TABLE IF NOT EXISTS data_bus_events (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), event_type VARCHAR(50), event_source VARCHAR(50), event_target VARCHAR(50), event_payload JSONB, priority INTEGER DEFAULT 5, ttl_seconds INTEGER DEFAULT 300, is_processed BOOLEAN DEFAULT FALSE, processed_at TIMESTAMP, processed_by VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_bus_events_unprocessed ON data_bus_events(is_processed, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS idx_bus_events_target ON data_bus_events(event_target, is_processed);
COMMIT;

-- Table: user_oauth_bindings (多平台OAuth认证绑定)
BEGIN;
CREATE TABLE IF NOT EXISTS user_oauth_bindings (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform        VARCHAR(30) NOT NULL,           -- wechat_miniprogram / wechat_official / xiaohongshu / apple / google
    platform_uid    VARCHAR(255) NOT NULL,        -- 平台用户唯一ID (openid/xhs_user_id)
    platform_unionid VARCHAR(255) DEFAULT '',      -- 平台统一ID（微信unionid）
    access_token    VARCHAR(500) DEFAULT '',       -- OAuth access_token（加密存储）
    refresh_token   VARCHAR(500) DEFAULT '',       -- OAuth refresh_token（加密存储）
    token_expires_at TIMESTAMP,                     -- access_token 过期时间
    platform_data   JSONB DEFAULT '{}',             -- 平台返回的原始用户信息
    is_primary      BOOLEAN DEFAULT FALSE,          -- 是否为主绑定（用于默认登录）
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (platform, platform_uid)
);
CREATE INDEX IF NOT EXISTS idx_oauth_bindings_user ON user_oauth_bindings(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_bindings_platform ON user_oauth_bindings(platform, platform_uid);
CREATE INDEX IF NOT EXISTS idx_oauth_bindings_unionid ON user_oauth_bindings(platform_unionid) WHERE platform_unionid != '';
DROP TRIGGER IF EXISTS trg_oauth_bindings_updated_at ON user_oauth_bindings;
CREATE TRIGGER trg_oauth_bindings_updated_at BEFORE UPDATE ON user_oauth_bindings FOR EACH ROW EXECUTE FUNCTION set_updated_at();
COMMIT;

-- Table: daily_notes (替代 devotion_journals，去除圣经元素)
BEGIN;
CREATE TABLE IF NOT EXISTS daily_notes (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    title           VARCHAR(200) DEFAULT '',
    content         TEXT DEFAULT '',
    mood            VARCHAR(50) DEFAULT '',
    tags            TEXT[] DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, date)
);
CREATE INDEX IF NOT EXISTS idx_daily_notes_user ON daily_notes(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_notes_date ON daily_notes(user_id, date DESC);
DROP TRIGGER IF EXISTS trg_daily_notes_updated_at ON daily_notes;
CREATE TRIGGER trg_daily_notes_updated_at BEFORE UPDATE ON daily_notes FOR EACH ROW EXECUTE FUNCTION set_updated_at();
COMMIT;

-- Table: personal_notes
BEGIN;
CREATE TABLE IF NOT EXISTS personal_notes (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, date DATE NOT NULL, title VARCHAR(200) DEFAULT '', content TEXT DEFAULT '', mood VARCHAR(50) DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE (user_id, date));
CREATE INDEX IF NOT EXISTS idx_personal_user ON personal_notes(user_id);
COMMIT;

-- Table: checkins
BEGIN;
CREATE TABLE IF NOT EXISTS checkins (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL, nickname VARCHAR(100) DEFAULT '', emotion_label VARCHAR(100) DEFAULT '', emotion_key VARCHAR(200) DEFAULT '', note TEXT DEFAULT '', is_anonymous BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_checkins_user ON checkins(user_id);
CREATE INDEX IF NOT EXISTS idx_checkins_created ON checkins(created_at DESC);
COMMIT;

-- Table: emotion_logs
BEGIN;
CREATE TABLE IF NOT EXISTS emotion_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, raw_text TEXT NOT NULL, emotion_tags TEXT[], intensity INTEGER CHECK (intensity BETWEEN 1 AND 10), occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, context_json JSONB DEFAULT '{}', source VARCHAR(50) DEFAULT 'web', CONSTRAINT uq_emotion_logs_user_time UNIQUE (user_id, occurred_at, id));
CREATE INDEX IF NOT EXISTS idx_emotion_logs_user_id ON emotion_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_emotion_logs_occurred_at ON emotion_logs(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_emotion_logs_emotion_tags ON emotion_logs USING GIN(emotion_tags);
COMMIT;

-- Table: cognitive_schemas
BEGIN;
CREATE TABLE IF NOT EXISTS cognitive_schemas (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, schema_name VARCHAR(100) NOT NULL, distortion_type VARCHAR(50), activating_event TEXT, consequence_emotional TEXT, consequence_behavioral TEXT, core_belief TEXT, latent_schema JSONB, cognitive_reframing_patch TEXT, reframing_evidence JSONB, is_active BOOLEAN DEFAULT TRUE, severity_score INTEGER CHECK (severity_score BETWEEN 1 AND 10), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, resolved_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_user_id ON cognitive_schemas(user_id);
CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_distortion ON cognitive_schemas(distortion_type);
CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_active ON cognitive_schemas(user_id, is_active);
DROP TRIGGER IF EXISTS trg_cognitive_schemas_updated ON cognitive_schemas; CREATE TRIGGER trg_cognitive_schemas_updated BEFORE UPDATE ON cognitive_schemas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
COMMIT;

-- Table: psychological_states
BEGIN;
CREATE TABLE IF NOT EXISTS psychological_states (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, state_name VARCHAR(50) NOT NULL, state_level INTEGER CHECK (state_level BETWEEN 0 AND 4), arousal_level INTEGER CHECK (arousal_level BETWEEN 1 AND 10), valence_score INTEGER CHECK (valence_score BETWEEN -10 AND 10), focus_capacity INTEGER CHECK (focus_capacity BETWEEN 1 AND 10), triggering_factors JSONB[], protective_factors JSONB[], recommended_action TEXT, escalation_protocol TEXT, captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, previous_state_id UUID REFERENCES psychological_states(id), state_duration_seconds INTEGER);
CREATE INDEX IF NOT EXISTS idx_psychological_states_user_id ON psychological_states(user_id);
CREATE INDEX IF NOT EXISTS idx_psychological_states_captured ON psychological_states(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_psychological_states_level ON psychological_states(state_level);
COMMIT;

-- Table: habit_state_machines
BEGIN;
CREATE TABLE IF NOT EXISTS habit_state_machines (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, habit_name VARCHAR(200) NOT NULL, habit_description TEXT, category VARCHAR(50), deterministic_anchor VARCHAR(200), trigger_anchor_time TIME, tier_green_config JSONB, tier_yellow_config JSONB, tier_red_config JSONB, token_green_yield INTEGER DEFAULT 10, token_yellow_yield INTEGER DEFAULT 5, token_red_yield INTEGER DEFAULT 1, is_active BOOLEAN DEFAULT TRUE, current_streak_days INTEGER DEFAULT 0, max_streak_days INTEGER DEFAULT 0, total_executions INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_execution_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_habit_machines_user ON habit_state_machines(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_machines_active ON habit_state_machines(user_id, is_active);
DROP TRIGGER IF EXISTS trg_habit_machines_updated ON habit_state_machines; CREATE TRIGGER trg_habit_machines_updated BEFORE UPDATE ON habit_state_machines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
COMMIT;

-- Table: execution_paralysis_logs
BEGIN;
CREATE TABLE IF NOT EXISTS execution_paralysis_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, paralysis_type VARCHAR(50), detected_signals JSONB[], raw_backlog_task TEXT, edge_context JSONB, tab_switch_count INTEGER, idle_duration_seconds INTEGER, window_thrashing BOOLEAN DEFAULT FALSE, intervention_triggered BOOLEAN DEFAULT FALSE, ignition_sequence_delivered TEXT, user_responded BOOLEAN DEFAULT FALSE, response_latency_seconds INTEGER, ignition_completed BOOLEAN DEFAULT FALSE, task_restarted BOOLEAN DEFAULT FALSE, post_intervention_mood INTEGER CHECK (post_intervention_mood BETWEEN 1 AND 10), detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, intervened_at TIMESTAMP, completed_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_paralysis_logs_user ON execution_paralysis_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_paralysis_logs_time ON execution_paralysis_logs(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_paralysis_logs_type ON execution_paralysis_logs(paralysis_type);
COMMIT;

-- Table: behavior_regulation_sessions
BEGIN;
CREATE TABLE IF NOT EXISTS behavior_regulation_sessions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, session_type VARCHAR(50), target_habit VARCHAR(200), motivation_level INTEGER CHECK (motivation_level BETWEEN 1 AND 10), ability_level INTEGER CHECK (ability_level BETWEEN 1 AND 10), trigger_strength INTEGER CHECK (trigger_strength BETWEEN 1 AND 10), energy_level INTEGER CHECK (energy_level BETWEEN 1 AND 5), behavioral_resistance INTEGER CHECK (behavioral_resistance BETWEEN 1 AND 10), cognitive_load INTEGER CHECK (cognitive_load BETWEEN 1 AND 10), emotional_stability INTEGER CHECK (emotional_stability BETWEEN 1 AND 10), attention_state VARCHAR(20), procrastination_level INTEGER CHECK (procrastination_level BETWEEN 1 AND 10), selected_tier VARCHAR(10), min_executable_action TEXT, task_downgrade TEXT, emotional_compensation TEXT, continuity_advice TEXT, was_executed BOOLEAN DEFAULT FALSE, execution_duration_seconds INTEGER, completion_percentage INTEGER CHECK (completion_percentage BETWEEN 0 AND 100), started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP, shame_mitigation_applied BOOLEAN DEFAULT FALSE, continuity_preserved BOOLEAN DEFAULT TRUE);
CREATE INDEX IF NOT EXISTS idx_behavior_sessions_user ON behavior_regulation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_behavior_sessions_time ON behavior_regulation_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_behavior_sessions_energy ON behavior_regulation_sessions(user_id, energy_level);
COMMIT;

-- Table: growth_trajectories
BEGIN;
CREATE TABLE IF NOT EXISTS growth_trajectories (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, period_type VARCHAR(20), period_start DATE NOT NULL, period_end DATE NOT NULL, emotional_regulation_score INTEGER CHECK (emotional_regulation_score BETWEEN 1 AND 100), cognitive_flexibility_score INTEGER CHECK (cognitive_flexibility_score BETWEEN 1 AND 100), behavioral_activation_score INTEGER CHECK (behavioral_activation_score BETWEEN 1 AND 100), interpersonal_effectiveness_score INTEGER CHECK (interpersonal_effectiveness_score BETWEEN 1 AND 100), self_concept_clarity_score INTEGER CHECK (self_concept_clarity_score BETWEEN 1 AND 100), change_from_last_period JSONB, significant_events JSONB[], generated_insights TEXT[], recommended_focus_areas TEXT[], calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_growth_trajectories_user_id ON growth_trajectories(user_id);
CREATE INDEX IF NOT EXISTS idx_growth_trajectories_period ON growth_trajectories(user_id, period_type, period_start DESC);
COMMIT;

-- Table: pattern_recognitions
BEGIN;
CREATE TABLE IF NOT EXISTS pattern_recognitions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, pattern_type VARCHAR(50), pattern_name VARCHAR(200), pattern_description TEXT, detected_in_logs UUID[], time_range_start TIMESTAMP, time_range_end TIMESTAMP, frequency_pattern JSONB, trigger_pattern JSONB, response_pattern JSONB, predictability_score INTEGER CHECK (predictability_score BETWEEN 1 AND 10), next_occurrence_prediction TIMESTAMP, breaking_strategy TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_active BOOLEAN DEFAULT TRUE);
CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_user_id ON pattern_recognitions(user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_type ON pattern_recognitions(pattern_type);
COMMIT;

-- Table: memory_consolidations
BEGIN;
CREATE TABLE IF NOT EXISTS memory_consolidations (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, memory_type VARCHAR(50), memory_title VARCHAR(200), memory_content TEXT, emotional_valence INTEGER CHECK (emotional_valence BETWEEN -10 AND 10), emotional_arousal INTEGER CHECK (emotional_arousal BETWEEN 1 AND 10), related_logs UUID[], related_schemas UUID[], related_narratives UUID[], memory_strength INTEGER CHECK (memory_strength BETWEEN 1 AND 100), last_accessed_at TIMESTAMP, access_count INTEGER DEFAULT 1, original_event_at TIMESTAMP, consolidated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_archived BOOLEAN DEFAULT FALSE);
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_user_id ON memory_consolidations(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_type ON memory_consolidations(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_strength ON memory_consolidations(user_id, memory_strength DESC);
COMMIT;

-- Table: self_concept_models
BEGIN;
CREATE TABLE IF NOT EXISTS self_concept_models (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, self_efficacy INTEGER CHECK (self_efficacy BETWEEN 1 AND 10), self_worth INTEGER CHECK (self_worth BETWEEN 1 AND 10), self_stability INTEGER CHECK (self_stability BETWEEN 1 AND 10), ideal_self JSONB, actual_self JSONB, discrepancy_score INTEGER CHECK (discrepancy_score BETWEEN 0 AND 10), identity_commitments JSONB[], assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, next_assessment_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_self_concept_user_id ON self_concept_models(user_id);
CREATE INDEX IF NOT EXISTS idx_self_concept_assessed ON self_concept_models(assessed_at DESC);
COMMIT;

-- Table: identity_narratives
BEGIN;
CREATE TABLE IF NOT EXISTS identity_narratives (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, narrative_type VARCHAR(50), narrative_title VARCHAR(200), narrative_text TEXT, identity_themes JSONB[], core_values JSONB[], narrative_period_start DATE, narrative_period_end DATE, is_current BOOLEAN DEFAULT FALSE, coherence_score INTEGER CHECK (coherence_score BETWEEN 1 AND 10), agency_score INTEGER CHECK (agency_score BETWEEN 1 AND 10), redemption_score INTEGER CHECK (redemption_score BETWEEN 1 AND 10), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, CONSTRAINT unique_current_narrative UNIQUE (user_id, is_current) DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX IF NOT EXISTS idx_identity_narratives_user_id ON identity_narratives(user_id);
CREATE INDEX IF NOT EXISTS idx_identity_narratives_current ON identity_narratives(user_id, is_current) WHERE is_current = TRUE;
DROP TRIGGER IF EXISTS trg_identity_narratives_updated ON identity_narratives; CREATE TRIGGER trg_identity_narratives_updated BEFORE UPDATE ON identity_narratives FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
COMMIT;

-- Table: personality_migrations
BEGIN;
CREATE TABLE IF NOT EXISTS personality_migrations (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, migration_dimension VARCHAR(50), starting_identity TEXT, target_identity TEXT, migration_path JSONB[], current_stage INTEGER DEFAULT 0, supporting_evidence JSONB[], migration_status VARCHAR(20) DEFAULT 'in_progress', progress_percentage INTEGER CHECK (progress_percentage BETWEEN 0 AND 100), started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, estimated_completion TIMESTAMP, achieved_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_migration_user ON personality_migrations(user_id);
CREATE INDEX IF NOT EXISTS idx_migration_dimension ON personality_migrations(user_id, migration_dimension);
COMMIT;

-- Table: user_system_states
BEGIN;
CREATE TABLE IF NOT EXISTS user_system_states (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE, current_state_code VARCHAR(20) DEFAULT 'NORMAL', previous_state_code VARCHAR(20), state_entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, state_duration_seconds INTEGER DEFAULT 0, state_transition_reason TEXT, current_arousal INTEGER CHECK (current_arousal BETWEEN 1 AND 10), current_valence INTEGER CHECK (current_valence BETWEEN -10 AND 10), current_energy_level INTEGER CHECK (current_energy_level BETWEEN 1 AND 5), auto_regulation_enabled BOOLEAN DEFAULT TRUE, system_energy_override INTEGER, psychology_layer_active BOOLEAN DEFAULT TRUE, behavior_layer_active BOOLEAN DEFAULT TRUE, execution_layer_active BOOLEAN DEFAULT TRUE, identity_layer_active BOOLEAN DEFAULT TRUE, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_user_states_current ON user_system_states(user_id, current_state_code);
COMMIT;

-- Table: user_token_ledgers
BEGIN;
CREATE TABLE IF NOT EXISTS user_token_ledgers (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, current_balance INTEGER DEFAULT 0, lifetime_earned INTEGER DEFAULT 0, lifetime_spent INTEGER DEFAULT 0, green_tier_count INTEGER DEFAULT 0, yellow_tier_count INTEGER DEFAULT 0, red_tier_count INTEGER DEFAULT 0, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_token_ledger_user ON user_token_ledgers(user_id);
COMMIT;

-- Table: state_transition_logs
BEGIN;
CREATE TABLE IF NOT EXISTS state_transition_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, from_state_code VARCHAR(20), to_state_code VARCHAR(20), transition_trigger TEXT, arousal_at_transition INTEGER, valence_at_transition INTEGER, energy_at_transition INTEGER, auto_interventions JSONB[], signals_broadcast JSONB[], transitioned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_state_transitions_user ON state_transition_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_state_transitions_time ON state_transition_logs(transitioned_at DESC);
COMMIT;

-- Table: dynamic_load_configs
BEGIN;
CREATE TABLE IF NOT EXISTS dynamic_load_configs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, cognitive_load_score INTEGER CHECK (cognitive_load_score BETWEEN 1 AND 10), emotional_load_score INTEGER CHECK (emotional_load_score BETWEEN 1 AND 10), behavioral_load_score INTEGER CHECK (behavioral_load_score BETWEEN 1 AND 10), auto_override_enabled BOOLEAN DEFAULT TRUE, red_tier_threshold INTEGER DEFAULT 2, current_system_energy_level INTEGER DEFAULT 3, current_task_intensity VARCHAR(20) DEFAULT 'full', current_prompt_tone VARCHAR(20) DEFAULT 'supportive', last_circuit_breaker_at TIMESTAMP, circuit_breaker_count_7d INTEGER DEFAULT 0, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_load_config_user ON dynamic_load_configs(user_id);
COMMIT;

-- Table: implementation_intentions
BEGIN;
CREATE TABLE IF NOT EXISTS implementation_intentions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, intention_name VARCHAR(200), if_trigger TEXT, then_action TEXT, applicable_contexts JSONB, usage_count INTEGER DEFAULT 0, success_rate INTEGER CHECK (success_rate BETWEEN 0 AND 100), avg_completion_time_seconds INTEGER, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_used_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_intentions_user ON implementation_intentions(user_id);
CREATE INDEX IF NOT EXISTS idx_intentions_active ON implementation_intentions(user_id, is_active);
COMMIT;

-- Table: edge_intervention_analytics
BEGIN;
CREATE TABLE IF NOT EXISTS edge_intervention_analytics (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, period_type VARCHAR(20), period_start DATE, period_end DATE, paralysis_events_count INTEGER DEFAULT 0, avg_detection_latency_seconds INTEGER, interventions_triggered INTEGER DEFAULT 0, ignition_completion_rate INTEGER CHECK (ignition_completion_rate BETWEEN 0 AND 100), task_restart_success_rate INTEGER CHECK (task_restart_success_rate BETWEEN 0 AND 100), micro_momentum_avg INTEGER CHECK (micro_momentum_avg BETWEEN 1 AND 100), continuity_preservation_score INTEGER CHECK (continuity_preservation_score BETWEEN 1 AND 100), top_paralysis_triggers TEXT[], most_effective_ignitions JSONB[], recommended_adjustments TEXT[], calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_edge_analytics_user ON edge_intervention_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_edge_analytics_period ON edge_intervention_analytics(user_id, period_type, period_start DESC);
COMMIT;

-- Table: behavioral_triggers
BEGIN;
CREATE TABLE IF NOT EXISTS behavioral_triggers (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, trigger_name VARCHAR(200) NOT NULL, trigger_type VARCHAR(50), trigger_pattern TEXT, activating_event TEXT, belief_system JSONB, consequence JSONB, frequency_count INTEGER DEFAULT 1, last_triggered_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_behavioral_triggers_user_id ON behavioral_triggers(user_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_triggers_type ON behavioral_triggers(trigger_type);
COMMIT;

-- Table: prayer_amens
BEGIN;
CREATE TABLE IF NOT EXISTS prayer_amens (prayer_id INTEGER REFERENCES prayers(id) ON DELETE CASCADE, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (prayer_id, user_id));
COMMIT;

-- Table: evangelism_amens
BEGIN;
CREATE TABLE IF NOT EXISTS evangelism_amens (prayer_id INTEGER REFERENCES evangelism_prayers(id) ON DELETE CASCADE, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (prayer_id, user_id));
COMMIT;

-- Table: personality_drivers
BEGIN;
CREATE TABLE IF NOT EXISTS personality_drivers (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, log_id UUID REFERENCES emotion_logs(id) ON DELETE CASCADE, surface_problem TEXT, deep_emotion TEXT, hidden_dynamics TEXT, behavioral_cycle JSONB, personality_traits JSONB, long_term_risk TEXT, intervention_priority INTEGER, driver_category VARCHAR(50), core_belief TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_personality_drivers_user_id ON personality_drivers(user_id);
CREATE INDEX IF NOT EXISTS idx_personality_drivers_log_id ON personality_drivers(log_id);
CREATE INDEX IF NOT EXISTS idx_personality_drivers_category ON personality_drivers(driver_category);
COMMIT;

-- Table: behavioral_experiments
BEGIN;
CREATE TABLE IF NOT EXISTS behavioral_experiments (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, schema_id UUID REFERENCES cognitive_schemas(id) ON DELETE SET NULL, experiment_id VARCHAR(100) UNIQUE, title VARCHAR(200) NOT NULL, hypothesis_to_test TEXT, counter_behavioral_action TEXT, difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 5), estimated_duration_minutes INTEGER, binary_telemetry_metric TEXT, success_criteria JSONB, status VARCHAR(20) DEFAULT 'pending', scheduled_at TIMESTAMP, completed_at TIMESTAMP, actual_outcome JSONB, hypothesis_falsified BOOLEAN, user_reflection TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reminder_sent BOOLEAN DEFAULT FALSE);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_user_id ON behavioral_experiments(user_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_schema ON behavioral_experiments(schema_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_status ON behavioral_experiments(status);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_scheduled ON behavioral_experiments(scheduled_at);
COMMIT;

-- Table: habit_execution_logs
BEGIN;
CREATE TABLE IF NOT EXISTS habit_execution_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, habit_id UUID REFERENCES habit_state_machines(id) ON DELETE CASCADE, energy_level_at_execution INTEGER CHECK (energy_level_at_execution BETWEEN 1 AND 5), selected_tier VARCHAR(10), action_taken TEXT, execution_duration_seconds INTEGER, tokens_earned INTEGER, was_completed BOOLEAN DEFAULT FALSE, completion_percentage INTEGER CHECK (completion_percentage BETWEEN 0 AND 100), circuit_breaker_triggered BOOLEAN DEFAULT FALSE, anti_guilt_message_shown BOOLEAN DEFAULT FALSE, mood_before INTEGER CHECK (mood_before BETWEEN 1 AND 10), mood_after INTEGER CHECK (mood_after BETWEEN 1 AND 10), executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_habit_logs_user ON habit_execution_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs_habit ON habit_execution_logs(habit_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs_time ON habit_execution_logs(executed_at DESC);
COMMIT;

-- Table: micro_scheduler_sessions
BEGIN;
CREATE TABLE IF NOT EXISTS micro_scheduler_sessions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, paralysis_log_id UUID REFERENCES execution_paralysis_logs(id) ON DELETE SET NULL, session_status VARCHAR(20) DEFAULT 'active', original_task TEXT, decoupled_chain JSONB[], current_step_index INTEGER DEFAULT 0, context_isolation JSONB, noise_floor_level INTEGER CHECK (noise_floor_level BETWEEN 1 AND 10), telemetry_signals JSONB[], last_user_signal_at TIMESTAMP, steps_completed INTEGER DEFAULT 0, total_steps INTEGER, micro_momentum_score INTEGER CHECK (micro_momentum_score BETWEEN 1 AND 100), started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_step_at TIMESTAMP, completed_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_micro_scheduler_user ON micro_scheduler_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_micro_scheduler_status ON micro_scheduler_sessions(session_status);
COMMIT;

-- Table: intervention_logs
BEGIN;
CREATE TABLE IF NOT EXISTS intervention_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, state_id UUID REFERENCES psychological_states(id) ON DELETE SET NULL, experiment_id UUID REFERENCES behavioral_experiments(id) ON DELETE SET NULL, intervention_type VARCHAR(50), intervention_layer INTEGER CHECK (intervention_layer BETWEEN 0 AND 4), prompt_text TEXT, technique_used VARCHAR(100), was_delivered BOOLEAN DEFAULT FALSE, user_response TEXT, effectiveness_score INTEGER CHECK (effectiveness_score BETWEEN 1 AND 10), delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, responded_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_intervention_logs_user_id ON intervention_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_intervention_logs_delivered ON intervention_logs(delivered_at DESC);
COMMIT;

-- Table: token_transactions
BEGIN;
CREATE TABLE IF NOT EXISTS token_transactions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, transaction_type VARCHAR(20), amount INTEGER, balance_after INTEGER, habit_id UUID REFERENCES habit_state_machines(id) ON DELETE SET NULL, habit_log_id UUID REFERENCES habit_execution_logs(id) ON DELETE SET NULL, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_token_tx_user ON token_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_token_tx_time ON token_transactions(created_at DESC);
COMMIT;

-- Table: identity_reinforcement_logs
BEGIN;
CREATE TABLE IF NOT EXISTS identity_reinforcement_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, current_narrative TEXT, narrative_type VARCHAR(50), negative_identity_labels TEXT[], target_identity TEXT, identity_category VARCHAR(50), reinforcement_language TEXT, user_reflection TEXT, reinforcement_strength INTEGER CHECK (reinforcement_strength BETWEEN 1 AND 10), user_resonance INTEGER CHECK (user_resonance BETWEEN 1 AND 10), migration_direction VARCHAR(50), migration_progress INTEGER CHECK (migration_progress BETWEEN 0 AND 100), related_emotion_log_id UUID REFERENCES emotion_logs(id) ON DELETE SET NULL, related_habit_id UUID REFERENCES habit_state_machines(id) ON DELETE SET NULL, related_intervention_id UUID REFERENCES execution_paralysis_logs(id) ON DELETE SET NULL, reinforced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_identity_logs_user ON identity_reinforcement_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_identity_logs_time ON identity_reinforcement_logs(reinforced_at DESC);
CREATE INDEX IF NOT EXISTS idx_identity_logs_category ON identity_reinforcement_logs(identity_category);
COMMIT;

-- Table: persona_tags
BEGIN;
CREATE TABLE IF NOT EXISTS persona_tags (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), tag_name VARCHAR(100) NOT NULL, tag_category VARCHAR(50) NOT NULL, tag_type VARCHAR(20) DEFAULT 'auto', description TEXT, synonyms TEXT[], keywords TEXT[], weight_default FLOAT DEFAULT 1.0, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_persona_tags_name ON persona_tags(tag_name, tag_category);
CREATE INDEX IF NOT EXISTS idx_persona_tags_category ON persona_tags(tag_category);
COMMIT;

-- Table: user_persona_tags
BEGIN;
CREATE TABLE IF NOT EXISTS user_persona_tags (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, tag_id UUID REFERENCES persona_tags(id) ON DELETE CASCADE, weight FLOAT DEFAULT 1.0, frequency INTEGER DEFAULT 1, source_type VARCHAR(50), source_id UUID, first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, confidence FLOAT DEFAULT 0.8);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_persona_tags_unique ON user_persona_tags(user_id, tag_id, source_type);
CREATE INDEX IF NOT EXISTS idx_user_persona_tags_user ON user_persona_tags(user_id);
CREATE INDEX IF NOT EXISTS idx_user_persona_tags_tag ON user_persona_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_user_persona_tags_weight ON user_persona_tags(user_id, weight DESC);
COMMIT;

-- Table: user_persona_profiles
BEGIN;
CREATE TABLE IF NOT EXISTS user_persona_profiles (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, tag_cloud JSONB DEFAULT '{}', emotion_dominance JSONB DEFAULT '{}', behavior_patterns JSONB DEFAULT '{}', habit_strength JSONB DEFAULT '{}', personality_vector JSONB DEFAULT '{}', stability_score FLOAT, resilience_score FLOAT, growth_trend VARCHAR(20), risk_level VARCHAR(20), profile_version INTEGER DEFAULT 1, computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_persona_profiles_user ON user_persona_profiles(user_id);
DROP TRIGGER IF EXISTS trg_user_persona_profiles_updated ON user_persona_profiles;
CREATE TRIGGER trg_user_persona_profiles_updated BEFORE UPDATE ON user_persona_profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();
COMMIT;

-- Table: tag_extraction_rules
BEGIN;
CREATE TABLE IF NOT EXISTS tag_extraction_rules (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), tag_id UUID REFERENCES persona_tags(id) ON DELETE CASCADE, pattern_type VARCHAR(20) DEFAULT 'keyword', pattern_value TEXT NOT NULL, weight_boost FLOAT DEFAULT 1.0, context_hint VARCHAR(50), is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_tag_extraction_rules_tag ON tag_extraction_rules(tag_id);
CREATE INDEX IF NOT EXISTS idx_tag_extraction_rules_pattern ON tag_extraction_rules(pattern_value);
COMMIT;

-- ============================================================
-- Test Data (one transaction per table, dependency-ordered)
-- ============================================================

-- Data for: users
BEGIN;
INSERT INTO users (id, email, nickname, avatar, login_type, password_hash, created_at) VALUES
(1, 'alice@example.com', 'Alice', 'https://i.pravatar.cc/150?u=alice', 'email', 'bcrypt:xxx', '2025-01-10 08:00:00'),
(2, 'bob@example.com', 'Bob', 'https://i.pravatar.cc/150?u=bob', 'email', 'bcrypt:xxx', '2025-01-15 10:30:00'),
(3, 'charlie@example.com', 'Charlie', '', 'wxapp', '', '2025-02-01 14:00:00'),
(4, 'diana@example.com', 'Diana', 'https://i.pravatar.cc/150?u=diana', 'email', 'bcrypt:xxx', '2025-02-20 09:00:00'),
(5, 'eve@example.com', 'Eve', '', 'email', 'bcrypt:xxx', '2025-03-05 11:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: security_audit
BEGIN;
INSERT INTO security_audit (event_type, email, ip_address, details, success, created_at) VALUES
('LOGIN_SUCCESS', 'alice@example.com', '192.168.1.10', '{"device": "chrome"}', TRUE, '2025-01-10 08:05:00'),
('REGISTER_SUCCESS', 'bob@example.com', '192.168.1.11', '{"source": "web"}', TRUE, '2025-01-15 10:30:00'),
('LOGIN_FAILED', 'eve@example.com', '10.0.0.5', '{"reason": "wrong_password"}', FALSE, '2025-03-05 12:00:00'),
('WXAPP_LOGIN_SUCCESS', NULL, '172.16.0.3', '{"openid": "oxxx"}', TRUE, '2025-02-01 14:00:00'),
('PASSWORD_RESET_SUCCESS', 'alice@example.com', '192.168.1.10', '{}', TRUE, '2025-04-01 09:00:00'),
('LOGOUT', 'bob@example.com', '192.168.1.11', '{}', TRUE, '2025-01-20 18:00:00'),
('EMAIL_SEND_CODE', 'diana@example.com', '192.168.1.12', '{"type": "register"}', TRUE, '2025-02-20 09:01:00'),
('PRAYER_SUBMIT', 'alice@example.com', '192.168.1.10', '{"prayer_id": 1}', TRUE, '2025-01-12 20:00:00'),
('SESSION_EXPIRED', 'eve@example.com', '10.0.0.5', '{"token_age_days": 31}', FALSE, '2025-04-10 08:00:00'),
('PROFILE_UPDATE', 'charlie@example.com', '172.16.0.3', '{"field": "nickname"}', TRUE, '2025-03-01 15:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: user_tokens
BEGIN;
INSERT INTO user_tokens (token, email, data, created_at, expires_at) VALUES
('tok_alice_001', 'alice@example.com', '{"id":1,"nickname":"Alice"}', '2025-01-10 08:05:00', '2025-02-10 08:05:00'),
('tok_bob_001', 'bob@example.com', '{"id":2,"nickname":"Bob"}', '2025-01-15 10:35:00', '2025-02-15 10:35:00'),
('tok_charlie_001', 'charlie@example.com', '{"id":3,"nickname":"Charlie"}', '2025-02-01 14:00:00', '2025-03-01 14:00:00'),
('tok_alice_002', 'alice@example.com', '{"id":1,"nickname":"Alice"}', '2025-03-01 09:00:00', '2025-04-01 09:00:00'),
('tok_diana_001', 'diana@example.com', '{"id":4,"nickname":"Diana"}', '2025-02-20 09:10:00', '2025-03-20 09:10:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: system_state_definitions
BEGIN;
INSERT INTO system_state_definitions (state_name, state_code, arousal_range, valence_range, energy_level_range, trigger_conditions, behavior_strategy, task_intensity, social_interaction, prompt_tone, prompt_focus) VALUES
('STATE_NORMAL', 'NORMAL', '{"min": 3, "max": 6}', '{"min": 0, "max": 7}', '{"min": 3, "max": 5}', ARRAY['{"condition": "energy >= 3", "threshold": 3}']::JSONB[], '标准执行模式', 'full', 'encouraged', 'supportive', ARRAY['常规任务', '习惯维护', '成长追踪']),
('STATE_LOW_ENERGY', 'LOW_ENERGY', '{"min": 2, "max": 4}', '{"min": -3, "max": 3}', '{"min": 1, "max": 2}', ARRAY['{"condition": "energy <= 2", "threshold": 2}']::JSONB[], '低功耗模式 - 熔断保护', 'minimal', 'neutral', 'gentle', ARRAY['最小动作', '连续性保持', '休息许可']),
('STATE_ANXIETY_ESCAPE', 'ANXIETY_ESCAPE', '{"min": 6, "max": 9}', '{"min": -7, "max": -2}', '{"min": 1, "max": 3}', ARRAY['{"condition": "anxiety_peak", "threshold": 7}']::JSONB[], '焦虑应对模式 - grounding优先', 'reduced', 'minimized', 'gentle', ARRAY['grounding', '呼吸调节', '小步启动']),
('STATE_SHAME_COLLAPSE', 'SHAME_COLLAPSE', '{"min": 4, "max": 8}', '{"min": -9, "max": -5}', '{"min": 1, "max": 2}', ARRAY['{"condition": "self_negation", "threshold": 8}']::JSONB[], '羞耻恢复模式 - 重建安全基地', 'paused', 'minimized', 'gentle', ARRAY['身份强化', '负面标签解构', '自我慈悲']),
('STATE_RECOVERY', 'RECOVERY', '{"min": 3, "max": 6}', '{"min": -2, "max": 4}', '{"min": 2, "max": 4}', ARRAY['{"condition": "post_crisis", "threshold": 5}']::JSONB[], '恢复期 - 渐进式重启', 'reduced', 'neutral', 'supportive', ARRAY['渐进任务', '成功经验', '动量积累']),
('STATE_FLOW', 'FLOW', '{"min": 5, "max": 8}', '{"min": 5, "max": 10}', '{"min": 4, "max": 5}', ARRAY['{"condition": "momentum > 80", "threshold": 80}']::JSONB[], '心流模式 - 最大化产出', 'full', 'neutral', 'neutral', ARRAY['深度工作', '保持节奏', '避免打断'])
ON CONFLICT (state_name) DO NOTHING;
COMMIT;

-- Data for: data_bus_events
BEGIN;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 1, "metric": "arousal"}', 1, FALSE, '2025-04-01 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 2, "metric": "arousal"}', 2, FALSE, '2025-04-02 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 3, "metric": "arousal"}', 3, FALSE, '2025-04-03 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 4, "metric": "arousal"}', 4, FALSE, '2025-04-04 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 5, "metric": "arousal"}', 5, FALSE, '2025-04-05 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 1, "metric": "arousal"}', 6, FALSE, '2025-04-06 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 2, "metric": "arousal"}', 7, FALSE, '2025-04-07 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 3, "metric": "arousal"}', 8, FALSE, '2025-04-08 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 4, "metric": "arousal"}', 9, FALSE, '2025-04-09 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{"user_id": 5, "metric": "arousal"}', 10, FALSE, '2025-04-10 12:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: prayers
BEGIN;
INSERT INTO prayers (user_id, nickname, content, is_anonymous, amen_count, created_at) VALUES
(1, 'Alice', '为家人健康祷告，求主保守。', FALSE, 3, '2025-01-12 20:00:00'),
(2, 'Bob', '工作中遇到困难，求主赐智慧。', FALSE, 5, '2025-01-18 08:30:00'),
(1, 'Alice', '为考试顺利通过祈求。', FALSE, 2, '2025-02-05 14:00:00'),
(NULL, '匿名', '心里很难过，求主安慰。', TRUE, 7, '2025-02-14 22:00:00'),
(3, 'Charlie', '刚信主，求主坚固信心。', FALSE, 4, '2025-02-20 10:00:00'),
(4, 'Diana', '求职面试，求主带领。', FALSE, 1, '2025-03-01 09:00:00'),
(2, 'Bob', '为远方的朋友代祷。', FALSE, 2, '2025-03-10 19:00:00'),
(5, 'Eve', '求主医治我的失眠。', FALSE, 6, '2025-03-15 23:00:00'),
(1, 'Alice', '感恩主，今天顺利完成了项目。', FALSE, 0, '2025-04-01 17:00:00'),
(NULL, '匿名', '请不要为我祷告，只是来倾诉。', TRUE, 0, '2025-04-10 21:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: evangelism_prayers
BEGIN;
INSERT INTO evangelism_prayers (user_id, nickname, content, is_anonymous, amen_count, created_at) VALUES
(1, 'Alice', '求主预备传道的机会给公司同事。', FALSE, 2, '2025-01-20 12:00:00'),
(2, 'Bob', '为不信主的父母祷告，soften their hearts.', FALSE, 4, '2025-01-25 18:00:00'),
(NULL, '匿名', '求主赐胆量向室友传福音。', TRUE, 3, '2025-02-10 20:00:00'),
(4, 'Diana', '为教会的布道会预备祷告。', FALSE, 1, '2025-03-05 07:00:00'),
(3, 'Charlie', '刚向同学分享了福音，求主浇灌。', FALSE, 5, '2025-03-20 16:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: devotion_journals
BEGIN;
INSERT INTO devotion_journals (user_id, date, title, content, verse, reflection, created_at) VALUES
(1, '2025-01-12', '登山宝训心得', '今天读了马太福音5章...', '马太福音 5:3-10', '虚心的人有福了，因为天国是他们的。', '2025-01-12 21:00:00'),
(1, '2025-01-19', '好撒玛利亚人', '路加福音10章的故事让我深思...', '路加福音 10:25-37', '爱邻舍如同自己，不仅限于认识的人。', '2025-01-19 22:00:00'),
(2, '2025-01-20', '初信读经', '第一次完整读完一卷书...', '约翰福音 3:16', '神爱世人，这是何等大的爱。', '2025-01-20 20:30:00'),
(3, '2025-02-05', '腓立比书4:6', '凡事藉着祷告、祈求...', '腓立比书 4:6-7', '在焦虑中学习交托，是每天的功课。', '2025-02-05 21:00:00'),
(4, '2025-03-01', '诗篇23篇', '耶和华是我的牧者...', '诗篇 23:1-4', '在低谷中神的同在是最真实的安慰。', '2025-03-01 20:00:00'),
(1, '2025-03-15', '罗马书8章', '圣灵与我们的软弱...', '罗马书 8:26', '不知道如何祷告时，圣灵亲自代求。', '2025-03-15 21:30:00'),
(2, '2025-04-01', '复活节默想', '基督从死里复活的意义...', '哥林多前书 15:4', '因祂活着，我能面对明天。', '2025-04-01 19:00:00'),
(5, '2025-04-10', '雅各书1章', '试炼生忍耐...', '雅各书 1:2-4', '在困难中看见成长的契机。', '2025-04-10 20:00:00'),
(3, '2025-04-15', '以弗所书6章', '属灵军装...', '以弗所书 6:10-18', '每天都要穿戴神所赐的全副军装。', '2025-04-15 21:00:00'),
(4, '2025-04-20', '箴言3章', '专心仰赖耶和华...', '箴言 3:5-6', '承认祂，祂必指引我的路。', '2025-04-20 20:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: sermon_journals
BEGIN;
INSERT INTO sermon_journals (user_id, date, title, preacher, verse, content, reflection, created_at) VALUES
(1, '2025-01-12', '新年的盼望', '张牧师', '耶利米书 29:11', '今天的信息讲到了神对百姓的计划...', '我也要在新的一年里更多信靠祂的计划。', '2025-01-12 14:00:00'),
(2, '2025-01-19', '信心的一小步', '李传道', '马太福音 14:29', '彼得在水面上行走的故事...', '信心不需要很大，只要愿意跨出一步。', '2025-01-19 14:30:00'),
(1, '2025-02-02', '爱的真谛', '王牧师', '哥林多前书 13:4-8', '爱是恒久忍耐，又有恩慈...', '需要在生活中更多操练对家人的爱。', '2025-02-02 14:00:00'),
(3, '2025-02-16', '初信造就', '陈长老', '约翰福音 1:12', '凡接待祂的，就是神的儿女...', '确信自己已经是神的儿女，这带来平安。', '2025-02-16 13:00:00'),
(4, '2025-03-02', '圣灵的果子', '赵牧师', '加拉太书 5:22-23', '仁爱、喜乐、和平、忍耐、恩慈...', '需要在忍耐和节制上更多成长。', '2025-03-02 14:00:00'),
(2, '2025-03-16', '饶恕的力量', '孙传道', '马太福音 18:21-22', '彼得问主饶恕几次...', '饶恕不是感觉，而是选择释放对方。', '2025-03-16 14:00:00'),
(1, '2025-04-06', '复活节的清晨', '张牧师', '马可福音 16:6', '基督已经复活了...', '因祂复活，我的信仰有确据。', '2025-04-06 14:00:00'),
(5, '2025-04-13', '祷告的生活', '李牧师', '帖撒罗尼迦前书 5:17', '要常常祷告...', '需要在忙碌中也不忽略与神的交通。', '2025-04-13 14:00:00'),
(3, '2025-04-20', '初信答疑', '陈长老', '罗马书 10:9', '口里承认，心里相信...', '对因信称义有了更深的理解。', '2025-04-20 13:30:00'),
(4, '2025-04-27', '管家职分', '王牧师', '路加福音 16:10', '在最小的事上忠心...', '要管理好神所赐的时间和才干。', '2025-04-27 14:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: personal_notes
BEGIN;
INSERT INTO personal_notes (user_id, date, title, content, mood, created_at) VALUES
(1, '2025-01-11', '周一感悟', '新的一周开始了，求主加力。', '平静', '2025-01-11 07:00:00'),
(2, '2025-01-22', '工作压力大', '项目deadline快到了，有点焦虑。', '焦虑', '2025-01-22 22:00:00'),
(1, '2025-02-14', '情人节独处', '一个人也挺好，神的爱足够。', '感恩', '2025-02-14 23:00:00'),
(3, '2025-03-01', '搬家', '搬到新城市，一切重新开始。', '期待', '2025-03-01 20:00:00'),
(4, '2025-03-20', '失业第7天', '投了几十份简历没有回音，心很慌。', '沮丧', '2025-03-20 21:00:00'),
(5, '2025-04-05', '失眠夜', '凌晨3点还睡不着，起来祷告。', '疲惫', '2025-04-05 03:00:00'),
(1, '2025-04-12', '收到好消息', '面试通过了！感谢主。', '喜乐', '2025-04-12 10:00:00'),
(2, '2025-04-18', '与好友和好', '冷战一周的室友终于说话了。', '轻松', '2025-04-18 21:00:00'),
(3, '2025-04-25', '第一次带领查经', '紧张但感恩，神赐下属灵的智慧。', '满足', '2025-04-25 20:30:00'),
(4, '2025-05-01', '新的开始', '入职新公司第一天，感恩主的带领。', '感恩', '2025-05-01 22:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: checkins
BEGIN;
INSERT INTO checkins (user_id, nickname, emotion_label, emotion_key, note, is_anonymous, created_at) VALUES
(1, 'Alice', '感恩', 'gratitude', '今天天气很好，读完了一章圣经。', FALSE, '2025-01-10 09:00:00'),
(2, 'Bob', '焦虑', 'anxiety', '明天有重要汇报，有点紧张。', FALSE, '2025-01-16 22:00:00'),
(3, 'Charlie', '喜乐', 'joy', '刚受洗一周，每天都充满感恩。', FALSE, '2025-02-10 08:00:00'),
(NULL, '匿名', '悲伤', 'sadness', '失去了亲人，心里很痛。', TRUE, '2025-02-14 20:00:00'),
(4, 'Diana', '迷茫', 'confusion', '不知道未来在哪里，求主指引。', FALSE, '2025-03-10 21:00:00'),
(1, 'Alice', '平静', 'peace', '在祷告中找到了内心的安宁。', FALSE, '2025-03-20 07:00:00'),
(5, 'Eve', '愤怒', 'anger', '被人误解了，心里很不舒服。', FALSE, '2025-04-05 18:00:00'),
(2, 'Bob', '希望', 'hope', '收到了一个好消息，感谢主。', FALSE, '2025-04-15 10:00:00'),
(3, 'Charlie', '谦卑', 'humility', '认识到自己的不足，需要更多恩典。', FALSE, '2025-04-25 20:00:00'),
(4, 'Diana', '信心', 'faith', '虽然看不见前路，但选择信靠。', FALSE, '2025-05-05 06:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: emotion_logs
BEGIN;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-000000000001', 1, '被领导当众批评，觉得自己很无能', '{"羞耻","愤怒","挫败"}', 8, '2025-03-01 18:00:00', '{"scene":"work","trigger":"public_criticism"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-000000000002', 2, '凌晨三点还睡不着，反复回想白天的事', '{"焦虑","失眠","反刍"}', 9, '2025-03-02 18:00:00', '{"scene":"bedtime","trigger":"rumination"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-000000000003', 3, '和朋友吵架后，觉得自己不被爱', '{"悲伤","孤独","被抛弃感"}', 7, '2025-03-03 18:00:00', '{"scene":"friendship","trigger":"conflict"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-000000000004', 4, '考试前手心冒汗，脑子里一片空白', '{"恐惧","紧张","无助"}', 8, '2025-03-04 18:00:00', '{"scene":"exam","trigger":"performance_pressure"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-000000000005', 5, '看到社交媒体上别人的完美生活，感到自卑', '{"嫉妒","自卑","孤独"}', 6, '2025-03-05 18:00:00', '{"scene":"social_media","trigger":"comparison"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-000000000006', 1, '终于完成了拖延两周的报告，如释重负', '{"轻松","成就感","解脱"}', 3, '2025-03-06 18:00:00', '{"scene":"work","trigger":"task_completion"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-000000000007', 2, '独自走在雨中，突然感到莫名的平静', '{"平静","感恩","孤独中的平安"}', 4, '2025-03-07 18:00:00', '{"scene":"nature","trigger":"rain_walk"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-000000000008', 3, '被父母催婚，感到巨大的压力和愧疚', '{"焦虑","愧疚","愤怒"}', 8, '2025-03-08 18:00:00', '{"scene":"family","trigger":"marriage_pressure"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-000000000009', 4, '跑步五公里后，心情舒畅很多', '{"放松","成就感","活力"}', 3, '2025-03-09 18:00:00', '{"scene":"exercise","trigger":"endorphin_release"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-00000000000a', 5, '在教会敬拜中流泪，感到被神拥抱', '{"感恩","被爱","释放"}', 4, '2025-03-10 18:00:00', '{"scene":"worship","trigger":"spiritual_connection"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-00000000000b', 1, '工作中被同事抢功劳，气得发抖', '{"愤怒","不公","背叛"}', 9, '2025-03-11 18:00:00', '{"scene":"work","trigger":"unfair_treatment"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-00000000000c', 2, '失业三个月后终于拿到offer，感恩主', '{"喜乐","感恩","希望"}', 2, '2025-03-12 18:00:00', '{"scene":"career","trigger":"job_offer"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-00000000000d', 3, '和室友冷战一周，家里气氛压抑', '{"疲惫","愤怒","回避"}', 7, '2025-03-13 18:00:00', '{"scene":"home","trigger":"roommate_conflict"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-00000000000e', 4, '祷告一小时后内心得平安，不再焦虑', '{"平安","感恩","信心"}', 3, '2025-03-14 18:00:00', '{"scene":"prayer","trigger":"spiritual_practice"}', 'web')
ON CONFLICT DO NOTHING;
INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ('00000000-0000-0000-0000-00000000000f', 5, '又一次刷手机到半夜，痛恨自己的自制力', '{"自责","挫败","空虚"}', 8, '2025-03-15 18:00:00', '{"scene":"bedtime","trigger":"phone_addiction"}', 'web')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: cognitive_schemas
BEGIN;
INSERT INTO cognitive_schemas (id, user_id, schema_name, distortion_type, core_belief, severity_score, created_at) VALUES ('00000000-0000-0000-0000-000000000033', 1, '我不够好', 'perfectionism', 'If I fail, I am worthless', 2, '2025-01-01 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO cognitive_schemas (id, user_id, schema_name, distortion_type, core_belief, severity_score, created_at) VALUES ('00000000-0000-0000-0000-000000000034', 2, '我不可爱', 'perfectionism', 'I cannot handle pressure', 3, '2025-01-02 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO cognitive_schemas (id, user_id, schema_name, distortion_type, core_belief, severity_score, created_at) VALUES ('00000000-0000-0000-0000-000000000035', 3, '我必须完美', 'perfectionism', 'If someone is upset, it is my fault', 4, '2025-01-03 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO cognitive_schemas (id, user_id, schema_name, distortion_type, core_belief, severity_score, created_at) VALUES ('00000000-0000-0000-0000-000000000036', 4, '我无能', 'perfectionism', 'Others are better than me', 5, '2025-01-04 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO cognitive_schemas (id, user_id, schema_name, distortion_type, core_belief, severity_score, created_at) VALUES ('00000000-0000-0000-0000-000000000037', 5, '我会被拒绝', 'perfectionism', 'I must be perfect to be accepted', 6, '2025-01-05 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO cognitive_schemas (id, user_id, schema_name, distortion_type, core_belief, severity_score, created_at) VALUES ('00000000-0000-0000-0000-000000000038', 1, '我不值得', 'perfectionism', 'My worth depends on productivity', 7, '2025-01-06 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO cognitive_schemas (id, user_id, schema_name, distortion_type, core_belief, severity_score, created_at) VALUES ('00000000-0000-0000-0000-000000000039', 2, '我危险', 'perfectionism', 'I am fundamentally alone', 8, '2025-01-07 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO cognitive_schemas (id, user_id, schema_name, distortion_type, core_belief, severity_score, created_at) VALUES ('00000000-0000-0000-0000-00000000003a', 3, '我失控', 'perfectionism', 'I must meet everyone''s expectations', 9, '2025-01-08 12:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: psychological_states
BEGIN;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-000000000047', 1, 'regulated', 0, 2, -5, 2, '维持当前活动', NULL, '2025-03-01 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-000000000048', 2, 'mild_dysregulation', 1, 3, -4, 3, '5-4-3-2-1 grounding', '00000000-0000-0000-0000-000000000047', '2025-03-02 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-000000000049', 3, 'moderate_dysregulation', 2, 4, -3, 4, '暂停任务，深呼吸', '00000000-0000-0000-0000-000000000048', '2025-03-03 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-00000000004a', 4, 'severe_dysregulation', 3, 5, -2, 5, '启动安全基地协议', '00000000-0000-0000-0000-000000000049', '2025-03-04 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-00000000004b', 5, 'recovery', 4, 6, -1, 6, '渐进式重启', '00000000-0000-0000-0000-00000000004a', '2025-03-05 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-00000000004c', 1, 'regulated', 0, 7, 0, 7, '维持当前活动', '00000000-0000-0000-0000-00000000004b', '2025-03-06 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-00000000004d', 2, 'mild_dysregulation', 1, 8, 1, 8, '短暂休息', '00000000-0000-0000-0000-00000000004c', '2025-03-07 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-00000000004e', 3, 'regulated', 2, 9, 2, 9, '维持当前活动', '00000000-0000-0000-0000-00000000004d', '2025-03-08 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-00000000004f', 4, 'regulated', 3, 2, 3, 2, '维持当前活动', '00000000-0000-0000-0000-00000000004e', '2025-03-09 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ('00000000-0000-0000-0000-000000000050', 5, 'moderate_dysregulation', 4, 3, 4, 3, '任务降级', '00000000-0000-0000-0000-00000000004f', '2025-03-10 08:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: habit_state_machines
BEGIN;
INSERT INTO habit_state_machines (id, user_id, habit_name, habit_description, category, deterministic_anchor, token_green_yield, current_streak_days, total_executions, created_at) VALUES ('00000000-0000-0000-0000-000000000065', 1, '晨祷', '晚上10点后情绪显著低落，伴随反刍思维', 'health', '闹钟响起后', 10, 0, 0, '2025-01-01 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_state_machines (id, user_id, habit_name, habit_description, category, deterministic_anchor, token_green_yield, current_streak_days, total_executions, created_at) VALUES ('00000000-0000-0000-0000-000000000066', 2, '运动', '面对邀请先答应后找理由取消', 'health', '周一/三/五下班', 10, 1, 5, '2025-01-02 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_state_machines (id, user_id, habit_name, habit_description, category, deterministic_anchor, token_green_yield, current_streak_days, total_executions, created_at) VALUES ('00000000-0000-0000-0000-000000000067', 3, '阅读', '任务截止前24小时焦虑激增但仍无法启动', 'health', '洗漱完毕上床', 10, 2, 10, '2025-01-03 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_state_machines (id, user_id, habit_name, habit_description, category, deterministic_anchor, token_green_yield, current_streak_days, total_executions, created_at) VALUES ('00000000-0000-0000-0000-000000000068', 4, '写日记', '准备阶段过度打磨导致无法交付', 'health', '晚餐后', 10, 3, 15, '2025-01-04 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_state_machines (id, user_id, habit_name, habit_description, category, deterministic_anchor, token_green_yield, current_streak_days, total_executions, created_at) VALUES ('00000000-0000-0000-0000-000000000069', 5, '早睡', '被冒犯后愤怒爆发，随后深度自责', 'health', '21:30手机充电', 10, 4, 20, '2025-01-05 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_state_machines (id, user_id, habit_name, habit_description, category, deterministic_anchor, token_green_yield, current_streak_days, total_executions, created_at) VALUES ('00000000-0000-0000-0000-00000000006a', 1, '专注工作', '上午2小时无干扰专注时间', 'health', '到达办公室后', 10, 5, 25, '2025-01-06 08:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: execution_paralysis_logs
BEGIN;
INSERT INTO execution_paralysis_logs (id, user_id, paralysis_type, detected_signals, raw_backlog_task, intervention_triggered, ignition_completed, detected_at) VALUES ('00000000-0000-0000-0000-00000000006f', 1, 'procrastination', '{}', '撰写Q1季度报告', TRUE, TRUE, '2025-03-01 14:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO execution_paralysis_logs (id, user_id, paralysis_type, detected_signals, raw_backlog_task, intervention_triggered, ignition_completed, detected_at) VALUES ('00000000-0000-0000-0000-000000000070', 2, 'procrastination', '{}', '准备客户演示PPT', TRUE, TRUE, '2025-03-02 14:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO execution_paralysis_logs (id, user_id, paralysis_type, detected_signals, raw_backlog_task, intervention_triggered, ignition_completed, detected_at) VALUES ('00000000-0000-0000-0000-000000000071', 3, 'procrastination', '{}', '回复积压邮件', TRUE, TRUE, '2025-03-03 14:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO execution_paralysis_logs (id, user_id, paralysis_type, detected_signals, raw_backlog_task, intervention_triggered, ignition_completed, detected_at) VALUES ('00000000-0000-0000-0000-000000000072', 4, 'procrastination', '{}', '开始学习新技能', TRUE, TRUE, '2025-03-04 14:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO execution_paralysis_logs (id, user_id, paralysis_type, detected_signals, raw_backlog_task, intervention_triggered, ignition_completed, detected_at) VALUES ('00000000-0000-0000-0000-000000000073', 5, 'procrastination', '{}', '整理税务文件', TRUE, TRUE, '2025-03-05 14:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO execution_paralysis_logs (id, user_id, paralysis_type, detected_signals, raw_backlog_task, intervention_triggered, ignition_completed, detected_at) VALUES ('00000000-0000-0000-0000-000000000074', 1, 'procrastination', '{}', '写求职信', TRUE, TRUE, '2025-03-06 14:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO execution_paralysis_logs (id, user_id, paralysis_type, detected_signals, raw_backlog_task, intervention_triggered, ignition_completed, detected_at) VALUES ('00000000-0000-0000-0000-000000000075', 2, 'procrastination', '{}', '更新简历', TRUE, TRUE, '2025-03-07 14:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO execution_paralysis_logs (id, user_id, paralysis_type, detected_signals, raw_backlog_task, intervention_triggered, ignition_completed, detected_at) VALUES ('00000000-0000-0000-0000-000000000076', 3, 'procrastination', '{}', '清理衣柜', TRUE, TRUE, '2025-03-08 14:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: behavior_regulation_sessions
BEGIN;
INSERT INTO behavior_regulation_sessions (user_id, session_type, target_habit, motivation_level, ability_level, energy_level, behavioral_resistance, cognitive_load, selected_tier, was_executed, completion_percentage, started_at) VALUES (1, 'habit_task', '晨祷', 2, 2, 1, 2, 2, 'Green', TRUE, 20, '2025-03-01 07:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavior_regulation_sessions (user_id, session_type, target_habit, motivation_level, ability_level, energy_level, behavioral_resistance, cognitive_load, selected_tier, was_executed, completion_percentage, started_at) VALUES (2, 'habit_task', '运动', 3, 3, 2, 3, 3, 'Green', TRUE, 30, '2025-03-02 07:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavior_regulation_sessions (user_id, session_type, target_habit, motivation_level, ability_level, energy_level, behavioral_resistance, cognitive_load, selected_tier, was_executed, completion_percentage, started_at) VALUES (3, 'habit_task', '阅读', 4, 4, 3, 4, 4, 'Green', TRUE, 40, '2025-03-03 07:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavior_regulation_sessions (user_id, session_type, target_habit, motivation_level, ability_level, energy_level, behavioral_resistance, cognitive_load, selected_tier, was_executed, completion_percentage, started_at) VALUES (4, 'habit_task', '写日记', 5, 5, 4, 5, 5, 'Green', TRUE, 50, '2025-03-04 07:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavior_regulation_sessions (user_id, session_type, target_habit, motivation_level, ability_level, energy_level, behavioral_resistance, cognitive_load, selected_tier, was_executed, completion_percentage, started_at) VALUES (5, 'habit_task', '早睡', 6, 6, 5, 6, 6, 'Green', TRUE, 60, '2025-03-05 07:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavior_regulation_sessions (user_id, session_type, target_habit, motivation_level, ability_level, energy_level, behavioral_resistance, cognitive_load, selected_tier, was_executed, completion_percentage, started_at) VALUES (1, 'habit_task', '专注工作', 7, 7, 1, 7, 7, 'Green', TRUE, 70, '2025-03-06 07:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavior_regulation_sessions (user_id, session_type, target_habit, motivation_level, ability_level, energy_level, behavioral_resistance, cognitive_load, selected_tier, was_executed, completion_percentage, started_at) VALUES (2, 'habit_task', '社交', 8, 8, 2, 8, 8, 'Green', TRUE, 80, '2025-03-07 07:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavior_regulation_sessions (user_id, session_type, target_habit, motivation_level, ability_level, energy_level, behavioral_resistance, cognitive_load, selected_tier, was_executed, completion_percentage, started_at) VALUES (3, 'habit_task', '灵修', 9, 9, 3, 9, 9, 'Green', TRUE, 90, '2025-03-08 07:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: growth_trajectories
BEGIN;
INSERT INTO growth_trajectories (user_id, period_type, period_start, period_end, emotional_regulation_score, cognitive_flexibility_score, behavioral_activation_score, interpersonal_effectiveness_score, self_concept_clarity_score, calculated_at) VALUES (1, 'weekly', '2025-03-01', '2025-03-07', 20, 25, 30, 35, 40, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO growth_trajectories (user_id, period_type, period_start, period_end, emotional_regulation_score, cognitive_flexibility_score, behavioral_activation_score, interpersonal_effectiveness_score, self_concept_clarity_score, calculated_at) VALUES (2, 'weekly', '2025-03-01', '2025-03-07', 30, 35, 40, 45, 50, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO growth_trajectories (user_id, period_type, period_start, period_end, emotional_regulation_score, cognitive_flexibility_score, behavioral_activation_score, interpersonal_effectiveness_score, self_concept_clarity_score, calculated_at) VALUES (3, 'weekly', '2025-03-01', '2025-03-07', 40, 45, 50, 55, 60, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO growth_trajectories (user_id, period_type, period_start, period_end, emotional_regulation_score, cognitive_flexibility_score, behavioral_activation_score, interpersonal_effectiveness_score, self_concept_clarity_score, calculated_at) VALUES (4, 'weekly', '2025-03-01', '2025-03-07', 50, 55, 60, 65, 70, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO growth_trajectories (user_id, period_type, period_start, period_end, emotional_regulation_score, cognitive_flexibility_score, behavioral_activation_score, interpersonal_effectiveness_score, self_concept_clarity_score, calculated_at) VALUES (5, 'weekly', '2025-03-01', '2025-03-07', 60, 65, 70, 75, 80, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO growth_trajectories (user_id, period_type, period_start, period_end, emotional_regulation_score, cognitive_flexibility_score, behavioral_activation_score, interpersonal_effectiveness_score, self_concept_clarity_score, calculated_at) VALUES (1, 'weekly', '2025-03-01', '2025-03-07', 70, 75, 80, 85, 90, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: pattern_recognitions
BEGIN;
INSERT INTO pattern_recognitions (user_id, pattern_type, pattern_name, pattern_description, predictability_score, created_at) VALUES (1, 'cyclical', '距截止72小时内', '晚上10点后情绪显著低落，伴随反刍思维', 2, '2025-04-01 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO pattern_recognitions (user_id, pattern_type, pattern_name, pattern_description, predictability_score, created_at) VALUES (2, 'cyclical', '打开朋友圈看到成功案例', '面对邀请先答应后找理由取消', 3, '2025-04-02 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO pattern_recognitions (user_id, pattern_type, pattern_name, pattern_description, predictability_score, created_at) VALUES (3, 'cyclical', '会议中被点名指出错误', '任务截止前24小时焦虑激增但仍无法启动', 4, '2025-04-03 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO pattern_recognitions (user_id, pattern_type, pattern_name, pattern_description, predictability_score, created_at) VALUES (4, 'cyclical', '节假日家庭聚餐', '准备阶段过度打磨导致无法交付', 5, '2025-04-04 12:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO pattern_recognitions (user_id, pattern_type, pattern_name, pattern_description, predictability_score, created_at) VALUES (5, 'cyclical', '考前一周复习', '被冒犯后愤怒爆发，随后深度自责', 6, '2025-04-05 12:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: memory_consolidations
BEGIN;
INSERT INTO memory_consolidations (user_id, memory_type, memory_title, memory_content, emotional_valence, emotional_arousal, memory_strength, original_event_at, consolidated_at) VALUES (1, 'episodic', '高考失利', '高考前夜失眠，考场上头脑空白，成绩远低于预期。', -5, 2, 20, '2024-06-01 10:00:00', '2025-01-01 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO memory_consolidations (user_id, memory_type, memory_title, memory_content, emotional_valence, emotional_arousal, memory_strength, original_event_at, consolidated_at) VALUES (2, 'episodic', '第一次祷告流泪', '在教会敬拜中突然泪流满面，感到前所未有的平安。', -4, 3, 30, '2024-06-02 10:00:00', '2025-01-02 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO memory_consolidations (user_id, memory_type, memory_title, memory_content, emotional_valence, emotional_arousal, memory_strength, original_event_at, consolidated_at) VALUES (3, 'episodic', '被好友背叛', '发现最好的朋友在背后说我的坏话，信任崩塌。', -3, 4, 40, '2024-06-03 10:00:00', '2025-01-03 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO memory_consolidations (user_id, memory_type, memory_title, memory_content, emotional_valence, emotional_arousal, memory_strength, original_event_at, consolidated_at) VALUES (4, 'episodic', '面试成功', '经历了三个月失业后，终于拿到心仪的offer。', -2, 5, 50, '2024-06-04 10:00:00', '2025-01-04 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO memory_consolidations (user_id, memory_type, memory_title, memory_content, emotional_valence, emotional_arousal, memory_strength, original_event_at, consolidated_at) VALUES (5, 'episodic', '父亲生病住院', '接到母亲电话说父亲中风，连夜赶回老家。', -1, 6, 60, '2024-06-05 10:00:00', '2025-01-05 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO memory_consolidations (user_id, memory_type, memory_title, memory_content, emotional_valence, emotional_arousal, memory_strength, original_event_at, consolidated_at) VALUES (1, 'episodic', '独自海外求学', '18岁第一次一个人飞出国，既害怕又兴奋。', 0, 7, 70, '2024-06-06 10:00:00', '2025-01-06 10:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: self_concept_models
BEGIN;
INSERT INTO self_concept_models (user_id, self_efficacy, self_worth, self_stability, discrepancy_score, assessed_at) VALUES (1, 2, 2, 2, 0, '2025-02-01 11:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO self_concept_models (user_id, self_efficacy, self_worth, self_stability, discrepancy_score, assessed_at) VALUES (2, 3, 3, 3, 1, '2025-02-02 11:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO self_concept_models (user_id, self_efficacy, self_worth, self_stability, discrepancy_score, assessed_at) VALUES (3, 4, 4, 4, 2, '2025-02-03 11:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO self_concept_models (user_id, self_efficacy, self_worth, self_stability, discrepancy_score, assessed_at) VALUES (4, 5, 5, 5, 3, '2025-02-04 11:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO self_concept_models (user_id, self_efficacy, self_worth, self_stability, discrepancy_score, assessed_at) VALUES (5, 6, 6, 6, 4, '2025-02-05 11:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: identity_narratives
BEGIN;
INSERT INTO identity_narratives (id, user_id, narrative_type, narrative_title, narrative_text, is_current, coherence_score, agency_score, redemption_score, created_at) VALUES ('00000000-0000-0000-0000-000000000051', 1, 'redemption', '从完美主义到真实自我', '我一直追求完美，直到发现完美让我窒息。', TRUE, 2, 2, 2, '2025-01-01 10:00:00')
ON CONFLICT (id) DO NOTHING;
INSERT INTO identity_narratives (id, user_id, narrative_type, narrative_title, narrative_text, is_current, coherence_score, agency_score, redemption_score, created_at) VALUES ('00000000-0000-0000-0000-000000000052', 2, 'redemption', '从取悦他人到设立边界', '我学会了说'不'，这反而让我更受欢迎。', FALSE, 3, 3, 3, '2025-01-02 10:00:00')
ON CONFLICT (id) DO NOTHING;
INSERT INTO identity_narratives (id, user_id, narrative_type, narrative_title, narrative_text, is_current, coherence_score, agency_score, redemption_score, created_at) VALUES ('00000000-0000-0000-0000-000000000053', 3, 'redemption', '从逃避到面对', '每次逃避都让我更害怕，现在选择面对。', FALSE, 4, 4, 4, '2025-01-03 10:00:00')
ON CONFLICT (id) DO NOTHING;
INSERT INTO identity_narratives (id, user_id, narrative_type, narrative_title, narrative_text, is_current, coherence_score, agency_score, redemption_score, created_at) VALUES ('00000000-0000-0000-0000-000000000054', 4, 'redemption', '从受害者到幸存者', '我不再问'为什么是我'，而是问'这教会了我什么'。', FALSE, 5, 5, 5, '2025-01-04 10:00:00')
ON CONFLICT (id) DO NOTHING;
INSERT INTO identity_narratives (id, user_id, narrative_type, narrative_title, narrative_text, is_current, coherence_score, agency_score, redemption_score, created_at) VALUES ('00000000-0000-0000-0000-000000000055', 5, 'redemption', '从比较到感恩', '当我停止比较，才发现自己已经很富足。', FALSE, 6, 6, 6, '2025-01-05 10:00:00')
ON CONFLICT (id) DO NOTHING;
INSERT INTO identity_narratives (id, user_id, narrative_type, narrative_title, narrative_text, is_current, coherence_score, agency_score, redemption_score, created_at) VALUES ('00000000-0000-0000-0000-000000000056', 1, 'redemption', '从控制到交托', '放下控制的手，我才真正摸到自由。', FALSE, 7, 7, 7, '2025-01-06 10:00:00')
ON CONFLICT (id) DO NOTHING;
COMMIT;

-- Data for: personality_migrations
BEGIN;
INSERT INTO personality_migrations (user_id, migration_dimension, starting_identity, target_identity, current_stage, migration_status, progress_percentage, started_at) VALUES (1, 'resilience', 'I am a victim', 'I am resilient', 0, 'in_progress', 20, '2025-01-01 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_migrations (user_id, migration_dimension, starting_identity, target_identity, current_stage, migration_status, progress_percentage, started_at) VALUES (2, 'resilience', 'I am unlovable', 'I am empowered', 1, 'in_progress', 30, '2025-01-02 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_migrations (user_id, migration_dimension, starting_identity, target_identity, current_stage, migration_status, progress_percentage, started_at) VALUES (3, 'resilience', 'I am a failure', 'I am worthy of love', 2, 'in_progress', 40, '2025-01-03 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_migrations (user_id, migration_dimension, starting_identity, target_identity, current_stage, migration_status, progress_percentage, started_at) VALUES (4, 'resilience', 'I am alone', 'I am learning', 3, 'in_progress', 50, '2025-01-04 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_migrations (user_id, migration_dimension, starting_identity, target_identity, current_stage, migration_status, progress_percentage, started_at) VALUES (5, 'resilience', 'I am fragile', 'I am connected', 4, 'in_progress', 60, '2025-01-05 09:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: user_system_states
BEGIN;
INSERT INTO user_system_states (user_id, current_state_code, previous_state_code, current_arousal, current_valence, current_energy_level, last_updated) VALUES (1, 'NORMAL', NULL, 2, -5, 1, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO user_system_states (user_id, current_state_code, previous_state_code, current_arousal, current_valence, current_energy_level, last_updated) VALUES (2, 'NORMAL', NULL, 3, -4, 2, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO user_system_states (user_id, current_state_code, previous_state_code, current_arousal, current_valence, current_energy_level, last_updated) VALUES (3, 'NORMAL', NULL, 4, -3, 3, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO user_system_states (user_id, current_state_code, previous_state_code, current_arousal, current_valence, current_energy_level, last_updated) VALUES (4, 'NORMAL', NULL, 5, -2, 4, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO user_system_states (user_id, current_state_code, previous_state_code, current_arousal, current_valence, current_energy_level, last_updated) VALUES (5, 'NORMAL', NULL, 6, -1, 5, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: user_token_ledgers
BEGIN;
INSERT INTO user_token_ledgers (user_id, current_balance, lifetime_earned, lifetime_spent, green_tier_count, yellow_tier_count, red_tier_count, last_updated) VALUES (1, 50, 80, 30, 5, 2, 0, '2025-04-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO user_token_ledgers (user_id, current_balance, lifetime_earned, lifetime_spent, green_tier_count, yellow_tier_count, red_tier_count, last_updated) VALUES (2, 100, 160, 60, 6, 3, 1, '2025-04-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO user_token_ledgers (user_id, current_balance, lifetime_earned, lifetime_spent, green_tier_count, yellow_tier_count, red_tier_count, last_updated) VALUES (3, 150, 240, 90, 7, 4, 2, '2025-04-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO user_token_ledgers (user_id, current_balance, lifetime_earned, lifetime_spent, green_tier_count, yellow_tier_count, red_tier_count, last_updated) VALUES (4, 200, 320, 120, 8, 5, 3, '2025-04-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO user_token_ledgers (user_id, current_balance, lifetime_earned, lifetime_spent, green_tier_count, yellow_tier_count, red_tier_count, last_updated) VALUES (5, 250, 400, 150, 9, 6, 4, '2025-04-01 00:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: state_transition_logs
BEGIN;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (1, 'NORMAL', 'RECOVERY', 'deadline_approaching', 2, -5, 1, '2025-03-01 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (2, 'NORMAL', 'RECOVERY', 'social_media_comparison', 3, -4, 2, '2025-03-02 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (3, 'NORMAL', 'RECOVERY', 'public_criticism', 4, -3, 3, '2025-03-03 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (4, 'NORMAL', 'RECOVERY', 'family_conflict', 5, -2, 4, '2025-03-04 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (5, 'NORMAL', 'RECOVERY', 'exam_pressure', 6, -1, 5, '2025-03-05 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (1, 'NORMAL', 'RECOVERY', 'loneliness_evening', 7, 0, 1, '2025-03-06 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (2, 'NORMAL', 'RECOVERY', '运动结束', 8, 1, 2, '2025-03-07 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (3, 'NORMAL', 'RECOVERY', '睡前 rumination', 9, 2, 3, '2025-03-08 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (4, 'NORMAL', 'RECOVERY', '收到好消息', 2, 3, 4, '2025-03-09 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES (5, 'NORMAL', 'RECOVERY', '任务完成', 3, 4, 5, '2025-03-10 10:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: dynamic_load_configs
BEGIN;
INSERT INTO dynamic_load_configs (user_id, cognitive_load_score, emotional_load_score, behavioral_load_score, current_system_energy_level, updated_at) VALUES (1, 2, 2, 2, 1, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO dynamic_load_configs (user_id, cognitive_load_score, emotional_load_score, behavioral_load_score, current_system_energy_level, updated_at) VALUES (2, 3, 3, 3, 2, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO dynamic_load_configs (user_id, cognitive_load_score, emotional_load_score, behavioral_load_score, current_system_energy_level, updated_at) VALUES (3, 4, 4, 4, 3, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO dynamic_load_configs (user_id, cognitive_load_score, emotional_load_score, behavioral_load_score, current_system_energy_level, updated_at) VALUES (4, 5, 5, 5, 4, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO dynamic_load_configs (user_id, cognitive_load_score, emotional_load_score, behavioral_load_score, current_system_energy_level, updated_at) VALUES (5, 6, 6, 6, 5, '2025-05-01 00:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: implementation_intentions
BEGIN;
INSERT INTO implementation_intentions (user_id, intention_name, if_trigger, then_action, usage_count, success_rate, is_active, created_at) VALUES (1, '晨祷习惯', '闹钟响起', '立即跪祷15分钟', 0, 50, TRUE, '2025-02-01 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO implementation_intentions (user_id, intention_name, if_trigger, then_action, usage_count, success_rate, is_active, created_at) VALUES (2, '运动启动', '下班到家', '换运动装备出门', 3, 60, TRUE, '2025-02-02 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO implementation_intentions (user_id, intention_name, if_trigger, then_action, usage_count, success_rate, is_active, created_at) VALUES (3, '阅读仪式', '洗漱完毕', '拿书上床阅读', 6, 70, TRUE, '2025-02-03 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO implementation_intentions (user_id, intention_name, if_trigger, then_action, usage_count, success_rate, is_active, created_at) VALUES (4, '情绪记录', '感到情绪波动', '打开手机日记APP', 9, 80, TRUE, '2025-02-04 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO implementation_intentions (user_id, intention_name, if_trigger, then_action, usage_count, success_rate, is_active, created_at) VALUES (5, '早睡准备', '21:30', '手机放到客厅充电', 12, 90, TRUE, '2025-02-05 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO implementation_intentions (user_id, intention_name, if_trigger, then_action, usage_count, success_rate, is_active, created_at) VALUES (1, '深度工作', '到达办公室', '开启勿扰模式', 15, 100, TRUE, '2025-02-06 10:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: edge_intervention_analytics
BEGIN;
INSERT INTO edge_intervention_analytics (user_id, period_type, period_start, period_end, paralysis_events_count, interventions_triggered, ignition_completion_rate, task_restart_success_rate, calculated_at) VALUES (1, 'weekly', '2025-03-01', '2025-03-07', 2, 1, 60, 50, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO edge_intervention_analytics (user_id, period_type, period_start, period_end, paralysis_events_count, interventions_triggered, ignition_completion_rate, task_restart_success_rate, calculated_at) VALUES (2, 'weekly', '2025-03-01', '2025-03-07', 3, 2, 70, 60, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO edge_intervention_analytics (user_id, period_type, period_start, period_end, paralysis_events_count, interventions_triggered, ignition_completion_rate, task_restart_success_rate, calculated_at) VALUES (3, 'weekly', '2025-03-01', '2025-03-07', 4, 3, 80, 70, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO edge_intervention_analytics (user_id, period_type, period_start, period_end, paralysis_events_count, interventions_triggered, ignition_completion_rate, task_restart_success_rate, calculated_at) VALUES (4, 'weekly', '2025-03-01', '2025-03-07', 5, 4, 90, 80, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO edge_intervention_analytics (user_id, period_type, period_start, period_end, paralysis_events_count, interventions_triggered, ignition_completion_rate, task_restart_success_rate, calculated_at) VALUES (5, 'weekly', '2025-03-01', '2025-03-07', 6, 5, 100, 90, '2025-03-08 00:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: behavioral_triggers
BEGIN;
INSERT INTO behavioral_triggers (user_id, trigger_name, trigger_type, trigger_pattern, activating_event, frequency_count, created_at) VALUES (1, 'deadline_approaching', 'situational', '距截止72小时内', '看到截止日期日历提醒', 1, '2025-02-01 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_triggers (user_id, trigger_name, trigger_type, trigger_pattern, activating_event, frequency_count, created_at) VALUES (2, 'social_media_comparison', 'situational', '打开朋友圈看到成功案例', '无意识滑动手机屏幕', 2, '2025-02-02 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_triggers (user_id, trigger_name, trigger_type, trigger_pattern, activating_event, frequency_count, created_at) VALUES (3, 'public_criticism', 'situational', '会议中被点名指出错误', '领导点名发言', 3, '2025-02-03 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_triggers (user_id, trigger_name, trigger_type, trigger_pattern, activating_event, frequency_count, created_at) VALUES (4, 'family_conflict', 'situational', '节假日家庭聚餐', '父母开始询问婚姻状况', 4, '2025-02-04 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_triggers (user_id, trigger_name, trigger_type, trigger_pattern, activating_event, frequency_count, created_at) VALUES (5, 'exam_pressure', 'situational', '考前一周复习', '翻开课本发现还有很多没看', 5, '2025-02-05 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_triggers (user_id, trigger_name, trigger_type, trigger_pattern, activating_event, frequency_count, created_at) VALUES (1, 'loneliness_evening', 'situational', '晚上10点后独自在家', '室友们都已入睡', 6, '2025-02-06 10:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: prayer_amens
BEGIN;
INSERT INTO prayer_amens (prayer_id, user_id, created_at) VALUES
(1, 2, '2025-01-13 08:00:00'),
(1, 3, '2025-01-13 09:00:00'),
(2, 1, '2025-01-18 10:00:00'),
(2, 4, '2025-01-19 11:00:00'),
(3, 2, '2025-02-06 08:00:00'),
(5, 1, '2025-02-21 07:00:00'),
(5, 2, '2025-02-21 08:00:00'),
(7, 3, '2025-03-11 10:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: evangelism_amens
BEGIN;
INSERT INTO evangelism_amens (prayer_id, user_id, created_at) VALUES
(1, 3, '2025-01-21 08:00:00'),
(2, 1, '2025-01-26 09:00:00'),
(2, 4, '2025-01-27 10:00:00'),
(5, 1, '2025-03-21 08:00:00'),
(5, 2, '2025-03-21 09:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: personality_drivers
BEGIN;
INSERT INTO personality_drivers (user_id, log_id, surface_problem, deep_emotion, hidden_dynamics, driver_category, core_belief, created_at) VALUES (1, '00000000-0000-0000-0000-000000000001', '被领导批评后陷入自我否定', '羞耻感', '完美主义驱动的自我价值绑定', 'perfectionism', 'If I fail, I am worthless', '2025-03-01 19:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_drivers (user_id, log_id, surface_problem, deep_emotion, hidden_dynamics, driver_category, core_belief, created_at) VALUES (2, '00000000-0000-0000-0000-000000000002', 'deadline临近时的灾难化思维', '恐惧感', '灾难化思维模式', 'perfectionism', 'I cannot handle pressure', '2025-03-02 19:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_drivers (user_id, log_id, surface_problem, deep_emotion, hidden_dynamics, driver_category, core_belief, created_at) VALUES (3, '00000000-0000-0000-0000-000000000003', '人际冲突后的讨好反应', '被抛弃恐惧', '讨好型人格的边界模糊', 'perfectionism', 'If someone is upset, it is my fault', '2025-03-03 19:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_drivers (user_id, log_id, surface_problem, deep_emotion, hidden_dynamics, driver_category, core_belief, created_at) VALUES (4, '00000000-0000-0000-0000-000000000004', '社交媒体比较引发的自卑', '低自尊', '社会比较的自我定义', 'perfectionism', 'Others are better than me', '2025-03-04 19:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_drivers (user_id, log_id, surface_problem, deep_emotion, hidden_dynamics, driver_category, core_belief, created_at) VALUES (5, '00000000-0000-0000-0000-000000000005', '考试前的表现焦虑', '完美主义焦虑', '成就导向的身份认同', 'perfectionism', 'I must be perfect to be accepted', '2025-03-05 19:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_drivers (user_id, log_id, surface_problem, deep_emotion, hidden_dynamics, driver_category, core_belief, created_at) VALUES (1, '00000000-0000-0000-0000-000000000006', '完成任务后的空虚感', '存在性空虚', '外在认可的内在空洞', 'perfectionism', 'My worth depends on productivity', '2025-03-06 19:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_drivers (user_id, log_id, surface_problem, deep_emotion, hidden_dynamics, driver_category, core_belief, created_at) VALUES (2, '00000000-0000-0000-0000-000000000007', '独处时的无价值感', '孤独感', '回避型依恋的激活', 'perfectionism', 'I am fundamentally alone', '2025-03-07 19:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO personality_drivers (user_id, log_id, surface_problem, deep_emotion, hidden_dynamics, driver_category, core_belief, created_at) VALUES (3, '00000000-0000-0000-0000-000000000008', '家庭压力下的情绪崩溃', '愧疚感', '家庭角色期望的冲突', 'perfectionism', 'I must meet everyone''s expectations', '2025-03-08 19:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: behavioral_experiments
BEGIN;
INSERT INTO behavioral_experiments (id, user_id, schema_id, experiment_id, title, hypothesis_to_test, difficulty_level, status, created_at) VALUES ('00000000-0000-0000-0000-00000000003d', 1, '00000000-0000-0000-0000-000000000033', 'exp_2025_000', '故意不完美提交报告', '如果不反复检查，结果也不会灾难性', 1, 'pending', '2025-02-01 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_experiments (id, user_id, schema_id, experiment_id, title, hypothesis_to_test, difficulty_level, status, created_at) VALUES ('00000000-0000-0000-0000-00000000003e', 2, '00000000-0000-0000-0000-000000000034', 'exp_2025_001', '主动表达不同意见', '表达不同意见不会导致关系破裂', 2, 'pending', '2025-02-02 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_experiments (id, user_id, schema_id, experiment_id, title, hypothesis_to_test, difficulty_level, status, created_at) VALUES ('00000000-0000-0000-0000-00000000003f', 3, '00000000-0000-0000-0000-000000000035', 'exp_2025_002', '在陌生人面前犯错', '即使出丑，他人也不会过度关注', 3, 'pending', '2025-02-03 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_experiments (id, user_id, schema_id, experiment_id, title, hypothesis_to_test, difficulty_level, status, created_at) VALUES ('00000000-0000-0000-0000-000000000040', 4, '00000000-0000-0000-0000-000000000036', 'exp_2025_003', '请求帮助而非独自承担', '请求帮助不会显得无能', 4, 'pending', '2025-02-04 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_experiments (id, user_id, schema_id, experiment_id, title, hypothesis_to_test, difficulty_level, status, created_at) VALUES ('00000000-0000-0000-0000-000000000041', 5, '00000000-0000-0000-0000-000000000037', 'exp_2025_004', '公开分享失败经历', '分享失败会拉近人与人距离', 5, 'pending', '2025-02-05 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO behavioral_experiments (id, user_id, schema_id, experiment_id, title, hypothesis_to_test, difficulty_level, status, created_at) VALUES ('00000000-0000-0000-0000-000000000042', 1, '00000000-0000-0000-0000-000000000038', 'exp_2025_005', '减少社交媒体使用', '减少比较会提升自我价值感', 1, 'pending', '2025-02-06 09:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: habit_execution_logs
BEGIN;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (1, '00000000-0000-0000-0000-000000000065', 1, 'Green', 10, TRUE, 100, 2, 3, '2025-03-01 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (2, '00000000-0000-0000-0000-000000000066', 2, 'Green', 10, TRUE, 100, 3, 4, '2025-03-02 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (3, '00000000-0000-0000-0000-000000000067', 3, 'Green', 10, TRUE, 100, 4, 5, '2025-03-03 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (4, '00000000-0000-0000-0000-000000000068', 4, 'Green', 10, TRUE, 100, 5, 6, '2025-03-04 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (5, '00000000-0000-0000-0000-000000000069', 5, 'Green', 10, TRUE, 100, 6, 7, '2025-03-05 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (1, '00000000-0000-0000-0000-00000000006a', 1, 'Green', 10, TRUE, 100, 7, 8, '2025-03-06 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (2, '00000000-0000-0000-0000-000000000065', 2, 'Green', 10, TRUE, 100, 8, 9, '2025-03-07 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (3, '00000000-0000-0000-0000-000000000066', 3, 'Green', 10, TRUE, 100, 9, 10, '2025-03-08 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (4, '00000000-0000-0000-0000-000000000067', 4, 'Green', 10, TRUE, 100, 2, 3, '2025-03-09 08:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES (5, '00000000-0000-0000-0000-000000000068', 5, 'Green', 10, TRUE, 100, 3, 4, '2025-03-10 08:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: micro_scheduler_sessions
BEGIN;
INSERT INTO micro_scheduler_sessions (user_id, paralysis_log_id, session_status, original_task, total_steps, steps_completed, micro_momentum_score, started_at) VALUES (1, '00000000-0000-0000-0000-00000000006f', 'completed', '撰写Q1季度报告', 5, 5, 50, '2025-03-01 14:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO micro_scheduler_sessions (user_id, paralysis_log_id, session_status, original_task, total_steps, steps_completed, micro_momentum_score, started_at) VALUES (2, '00000000-0000-0000-0000-000000000070', 'completed', '准备客户演示PPT', 5, 5, 60, '2025-03-02 14:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO micro_scheduler_sessions (user_id, paralysis_log_id, session_status, original_task, total_steps, steps_completed, micro_momentum_score, started_at) VALUES (3, '00000000-0000-0000-0000-000000000071', 'completed', '回复积压邮件', 5, 5, 70, '2025-03-03 14:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO micro_scheduler_sessions (user_id, paralysis_log_id, session_status, original_task, total_steps, steps_completed, micro_momentum_score, started_at) VALUES (4, '00000000-0000-0000-0000-000000000072', 'completed', '开始学习新技能', 5, 5, 80, '2025-03-04 14:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO micro_scheduler_sessions (user_id, paralysis_log_id, session_status, original_task, total_steps, steps_completed, micro_momentum_score, started_at) VALUES (5, '00000000-0000-0000-0000-000000000073', 'completed', '整理税务文件', 5, 5, 90, '2025-03-05 14:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO micro_scheduler_sessions (user_id, paralysis_log_id, session_status, original_task, total_steps, steps_completed, micro_momentum_score, started_at) VALUES (1, '00000000-0000-0000-0000-000000000074', 'completed', '写求职信', 5, 5, 100, '2025-03-06 14:05:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: intervention_logs
BEGIN;
INSERT INTO intervention_logs (user_id, state_id, experiment_id, intervention_type, intervention_layer, prompt_text, technique_used, was_delivered, effectiveness_score, delivered_at) VALUES (1, '00000000-0000-0000-0000-000000000047', '00000000-0000-0000-0000-00000000003d', 'micro_skill', 0, '现在注意到脚下的地面', 'self_soothing', TRUE, 2, '2025-03-01 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO intervention_logs (user_id, state_id, experiment_id, intervention_type, intervention_layer, prompt_text, technique_used, was_delivered, effectiveness_score, delivered_at) VALUES (2, '00000000-0000-0000-0000-000000000048', '00000000-0000-0000-0000-00000000003e', 'micro_skill', 1, '轻轻把手放在胸口', 'breathing', TRUE, 3, '2025-03-02 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO intervention_logs (user_id, state_id, experiment_id, intervention_type, intervention_layer, prompt_text, technique_used, was_delivered, effectiveness_score, delivered_at) VALUES (3, '00000000-0000-0000-0000-000000000049', '00000000-0000-0000-0000-00000000003f', 'micro_skill', 2, '深呼吸三次', 'cognitive_labeling', TRUE, 4, '2025-03-03 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO intervention_logs (user_id, state_id, experiment_id, intervention_type, intervention_layer, prompt_text, technique_used, was_delivered, effectiveness_score, delivered_at) VALUES (4, '00000000-0000-0000-0000-00000000004a', '00000000-0000-0000-0000-000000000040', 'micro_skill', 3, '告诉自己：这是焦虑，不是危险', 'sensory_anchoring', TRUE, 5, '2025-03-04 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO intervention_logs (user_id, state_id, experiment_id, intervention_type, intervention_layer, prompt_text, technique_used, was_delivered, effectiveness_score, delivered_at) VALUES (5, '00000000-0000-0000-0000-00000000004b', '00000000-0000-0000-0000-000000000041', 'micro_skill', 4, '慢慢数五个周围的颜色', 'movement', TRUE, 6, '2025-03-05 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO intervention_logs (user_id, state_id, experiment_id, intervention_type, intervention_layer, prompt_text, technique_used, was_delivered, effectiveness_score, delivered_at) VALUES (1, '00000000-0000-0000-0000-00000000004c', '00000000-0000-0000-0000-000000000042', 'micro_skill', 0, '站起来伸展身体', 'somatic_regulation', TRUE, 7, '2025-03-06 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO intervention_logs (user_id, state_id, experiment_id, intervention_type, intervention_layer, prompt_text, technique_used, was_delivered, effectiveness_score, delivered_at) VALUES (2, '00000000-0000-0000-0000-00000000004d', '00000000-0000-0000-0000-00000000003d', 'micro_skill', 1, '喝一杯温水', 'gratitude_priming', TRUE, 8, '2025-03-07 09:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO intervention_logs (user_id, state_id, experiment_id, intervention_type, intervention_layer, prompt_text, technique_used, was_delivered, effectiveness_score, delivered_at) VALUES (3, '00000000-0000-0000-0000-00000000004e', '00000000-0000-0000-0000-00000000003e', 'micro_skill', 2, '写下一个你感激的小事', 'grounding', TRUE, 9, '2025-03-08 09:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: token_transactions
BEGIN;
INSERT INTO token_transactions (user_id, transaction_type, amount, balance_after, habit_id, description, created_at) VALUES (1, 'earn', 10, 50, '00000000-0000-0000-0000-000000000065', 'completed habit', '2025-03-01 08:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO token_transactions (user_id, transaction_type, amount, balance_after, habit_id, description, created_at) VALUES (2, 'earn', 10, 100, '00000000-0000-0000-0000-000000000066', 'completed habit', '2025-03-02 08:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO token_transactions (user_id, transaction_type, amount, balance_after, habit_id, description, created_at) VALUES (3, 'earn', 10, 150, '00000000-0000-0000-0000-000000000067', 'completed habit', '2025-03-03 08:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO token_transactions (user_id, transaction_type, amount, balance_after, habit_id, description, created_at) VALUES (4, 'earn', 10, 200, '00000000-0000-0000-0000-000000000068', 'completed habit', '2025-03-04 08:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO token_transactions (user_id, transaction_type, amount, balance_after, habit_id, description, created_at) VALUES (5, 'earn', 10, 250, '00000000-0000-0000-0000-000000000069', 'completed habit', '2025-03-05 08:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO token_transactions (user_id, transaction_type, amount, balance_after, habit_id, description, created_at) VALUES (1, 'earn', 10, 300, '00000000-0000-0000-0000-00000000006a', 'completed habit', '2025-03-06 08:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO token_transactions (user_id, transaction_type, amount, balance_after, habit_id, description, created_at) VALUES (2, 'earn', 10, 350, '00000000-0000-0000-0000-000000000065', 'completed habit', '2025-03-07 08:05:00')
ON CONFLICT DO NOTHING;
INSERT INTO token_transactions (user_id, transaction_type, amount, balance_after, habit_id, description, created_at) VALUES (3, 'earn', 10, 400, '00000000-0000-0000-0000-000000000066', 'completed habit', '2025-03-08 08:05:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: identity_reinforcement_logs
BEGIN;
INSERT INTO identity_reinforcement_logs (user_id, current_narrative, narrative_type, target_identity, identity_category, reinforcement_strength, user_resonance, migration_progress, related_emotion_log_id, related_habit_id, related_intervention_id, reinforced_at) VALUES (1, 'I am learning to be gentle with myself', 'redemption', 'I am resilient', 'growth_continuity', 2, 2, 20, '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000065', '00000000-0000-0000-0000-00000000006f', '2025-04-01 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO identity_reinforcement_logs (user_id, current_narrative, narrative_type, target_identity, identity_category, reinforcement_strength, user_resonance, migration_progress, related_emotion_log_id, related_habit_id, related_intervention_id, reinforced_at) VALUES (2, 'I am becoming someone who shows up', 'redemption', 'I am resilient', 'growth_continuity', 3, 3, 30, '00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000066', '00000000-0000-0000-0000-000000000070', '2025-04-02 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO identity_reinforcement_logs (user_id, current_narrative, narrative_type, target_identity, identity_category, reinforcement_strength, user_resonance, migration_progress, related_emotion_log_id, related_habit_id, related_intervention_id, reinforced_at) VALUES (3, 'I am growing through discomfort', 'redemption', 'I am resilient', 'growth_continuity', 4, 4, 40, '00000000-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000067', '00000000-0000-0000-0000-000000000071', '2025-04-03 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO identity_reinforcement_logs (user_id, current_narrative, narrative_type, target_identity, identity_category, reinforcement_strength, user_resonance, migration_progress, related_emotion_log_id, related_habit_id, related_intervention_id, reinforced_at) VALUES (4, 'I am choosing courage over comfort', 'redemption', 'I am resilient', 'growth_continuity', 5, 5, 50, '00000000-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000068', '00000000-0000-0000-0000-000000000072', '2025-04-04 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO identity_reinforcement_logs (user_id, current_narrative, narrative_type, target_identity, identity_category, reinforcement_strength, user_resonance, migration_progress, related_emotion_log_id, related_habit_id, related_intervention_id, reinforced_at) VALUES (5, 'I am enough as I am', 'redemption', 'I am resilient', 'growth_continuity', 6, 6, 60, '00000000-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000069', '00000000-0000-0000-0000-000000000073', '2025-04-05 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO identity_reinforcement_logs (user_id, current_narrative, narrative_type, target_identity, identity_category, reinforcement_strength, user_resonance, migration_progress, related_emotion_log_id, related_habit_id, related_intervention_id, reinforced_at) VALUES (1, 'I am a work in progress', 'redemption', 'I am resilient', 'growth_continuity', 7, 7, 70, '00000000-0000-0000-0000-000000000006', '00000000-0000-0000-0000-00000000006a', '00000000-0000-0000-0000-000000000074', '2025-04-06 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO identity_reinforcement_logs (user_id, current_narrative, narrative_type, target_identity, identity_category, reinforcement_strength, user_resonance, migration_progress, related_emotion_log_id, related_habit_id, related_intervention_id, reinforced_at) VALUES (2, 'I am learning to receive love', 'redemption', 'I am resilient', 'growth_continuity', 8, 8, 80, '00000000-0000-0000-0000-000000000007', '00000000-0000-0000-0000-000000000065', '00000000-0000-0000-0000-000000000075', '2025-04-07 10:00:00')
ON CONFLICT DO NOTHING;
INSERT INTO identity_reinforcement_logs (user_id, current_narrative, narrative_type, target_identity, identity_category, reinforcement_strength, user_resonance, migration_progress, related_emotion_log_id, related_habit_id, related_intervention_id, reinforced_at) VALUES (3, 'I am becoming resilient', 'redemption', 'I am resilient', 'growth_continuity', 9, 9, 90, '00000000-0000-0000-0000-000000000008', '00000000-0000-0000-0000-000000000066', '00000000-0000-0000-0000-000000000076', '2025-04-08 10:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: persona_tags
BEGIN;
INSERT INTO persona_tags (id, tag_name, tag_category, tag_type, description, synonyms, keywords, weight_default) VALUES
('a0000000-0000-0000-0000-000000000001', '焦虑倾向', 'emotion', 'system', '容易出现焦虑情绪的倾向', ARRAY['紧张','不安','担忧'], ARRAY['焦虑','恐惧','害怕','紧张','不安'], 1.0),
('a0000000-0000-0000-0000-000000000002', '情绪敏感', 'emotion', 'system', '对情绪变化高度敏感', ARRAY['敏感','脆弱','易感'], ARRAY['敏感','脆弱','触动','感动','难过'], 1.0),
('a0000000-0000-0000-0000-000000000003', '乐观积极', 'emotion', 'system', '倾向于积极正面看待事物', ARRAY['积极','阳光','开朗'], ARRAY['开心','快乐','感恩','希望','期待'], 1.0),
('a0000000-0000-0000-0000-000000000004', '完美主义', 'personality', 'system', '对自我和他人有极高标准', ARRAY['苛求','严格','高标准'], ARRAY['完美','不够好','必须','应该','失败'], 1.2),
('a0000000-0000-0000-0000-000000000005', '回避型应对', 'behavior', 'system', '面对压力时倾向于回避', ARRAY['逃避','拖延','退缩'], ARRAY['回避','逃避','拖延','不想面对','算了'], 1.1),
('a0000000-0000-0000-0000-000000000006', '自律坚持', 'habit', 'system', '具有较强的习惯坚持能力', ARRAY['自律','坚持','毅力'], ARRAY['坚持','每天','习惯','自律','打卡'], 1.0),
('a0000000-0000-0000-0000-000000000007', '社交敏感', 'relationship', 'system', '在人际关系中容易感到不安', ARRAY['社恐','内向','敏感'], ARRAY['社交','别人怎么看','被拒绝','不被接受','尴尬'], 1.1),
('a0000000-0000-0000-0000-000000000008', '成长导向', 'value', 'system', '重视个人成长和自我提升', ARRAY['进步','学习','提升'], ARRAY['成长','进步','学习','提升','突破'], 1.0),
('a0000000-0000-0000-0000-000000000009', '灾难化思维', 'cognition', 'system', '倾向于将事情往最坏方向想', ARRAY['最坏打算','末日思维'], ARRAY['完蛋了','怎么办','万一','最坏','灾难'], 1.2),
('a0000000-0000-0000-0000-00000000000a', '反刍思维', 'cognition', 'system', '反复回想负面经历', ARRAY['胡思乱想','钻牛角尖'], ARRAY['反复想','忘不了','一直想','为什么','当时'], 1.1),
('a0000000-0000-0000-0000-00000000000b', '信仰依靠', 'value', 'system', '在困境中依靠信仰获得力量', ARRAY['祷告','交托','信靠'], ARRAY['祷告','神','上帝','信心','交托','恩典'], 1.0),
('a0000000-0000-0000-0000-00000000000c', '情绪化决策', 'behavior', 'system', '决策时容易受情绪影响', ARRAY['冲动','感性决策'], ARRAY['冲动','后悔','不该','没想清楚','一时'], 1.1),
('a0000000-0000-0000-0000-00000000000d', '讨好型人格', 'personality', 'system', '过度关注他人需求忽视自己', ARRAY['讨好','委曲求全','不敢拒绝'], ARRAY['讨好','不敢拒绝','别人','期望','应该'], 1.2),
('a0000000-0000-0000-0000-00000000000e', '自我批评', 'personality', 'system', '习惯性自我否定和批评', ARRAY['自责','内疚','自我否定'], ARRAY['我不行','我的错','对不起','不够好','无能'], 1.2),
('a0000000-0000-0000-0000-00000000000f', '韧性成长', 'personality', 'auto', '经历困难后展现出恢复力', ARRAY['复原力','坚韧'], ARRAY['挺过来','坚强','不放弃','重新开始','站起来'], 1.0)
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: tag_extraction_rules
BEGIN;
INSERT INTO tag_extraction_rules (tag_id, pattern_type, pattern_value, weight_boost, context_hint) VALUES
('a0000000-0000-0000-0000-000000000001', 'keyword', '焦虑', 1.5, 'emotion'),
('a0000000-0000-0000-0000-000000000001', 'keyword', '紧张不安', 1.2, 'emotion'),
('a0000000-0000-0000-0000-000000000004', 'keyword', '不够好', 1.5, 'emotion'),
('a0000000-0000-0000-0000-000000000004', 'regex', '必须|一定要|不能失败', 1.3, 'emotion'),
('a0000000-0000-0000-0000-000000000005', 'keyword', '不想面对', 1.4, 'behavior'),
('a0000000-0000-0000-0000-000000000005', 'keyword', '拖延', 1.2, 'behavior'),
('a0000000-0000-0000-0000-000000000009', 'regex', '完蛋|怎么办|万一.*最坏', 1.5, 'cognition'),
('a0000000-0000-0000-0000-00000000000a', 'keyword', '一直想', 1.3, 'cognition'),
('a0000000-0000-0000-0000-00000000000b', 'keyword', '祷告', 1.0, 'emotion'),
('a0000000-0000-0000-0000-00000000000b', 'regex', '感谢神|交托|信靠', 1.2, 'emotion'),
('a0000000-0000-0000-0000-00000000000d', 'keyword', '不敢拒绝', 1.5, 'behavior'),
('a0000000-0000-0000-0000-00000000000e', 'regex', '我不行|我的错|我很差|我无能', 1.5, 'emotion')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: user_persona_tags
BEGIN;
INSERT INTO user_persona_tags (user_id, tag_id, weight, frequency, source_type, source_id, confidence, first_seen_at, last_seen_at) VALUES
(1, 'a0000000-0000-0000-0000-000000000004', 7.5, 12, 'emotion_log', '00000000-0000-0000-0000-000000000001', 0.92, '2025-01-15 10:00:00', '2025-04-01 18:00:00'),
(1, 'a0000000-0000-0000-0000-000000000001', 6.2, 8, 'emotion_log', '00000000-0000-0000-0000-000000000004', 0.88, '2025-02-01 09:00:00', '2025-03-20 14:00:00'),
(1, 'a0000000-0000-0000-0000-00000000000b', 5.0, 15, 'emotion_log', '00000000-0000-0000-0000-000000000006', 0.95, '2025-01-10 08:00:00', '2025-04-08 20:00:00'),
(1, 'a0000000-0000-0000-0000-000000000006', 4.8, 6, 'habit_creation', '00000000-0000-0000-0000-000000000065', 0.85, '2025-01-01 08:00:00', '2025-03-15 08:00:00'),
(2, 'a0000000-0000-0000-0000-000000000007', 6.8, 10, 'emotion_log', '00000000-0000-0000-0000-000000000002', 0.90, '2025-01-20 11:00:00', '2025-04-05 16:00:00'),
(2, 'a0000000-0000-0000-0000-000000000005', 5.5, 7, 'behavior_regulation', '00000000-0000-0000-0000-000000000052', 0.82, '2025-02-10 13:00:00', '2025-03-28 10:00:00'),
(2, 'a0000000-0000-0000-0000-00000000000a', 5.0, 9, 'emotion_log', '00000000-0000-0000-0000-000000000007', 0.87, '2025-01-25 22:00:00', '2025-04-02 23:00:00'),
(3, 'a0000000-0000-0000-0000-000000000002', 7.0, 11, 'emotion_log', '00000000-0000-0000-0000-000000000003', 0.91, '2025-02-01 14:00:00', '2025-04-03 15:00:00'),
(3, 'a0000000-0000-0000-0000-00000000000e', 6.5, 8, 'emotion_log', '00000000-0000-0000-0000-000000000008', 0.89, '2025-02-05 18:00:00', '2025-03-30 20:00:00'),
(3, 'a0000000-0000-0000-0000-00000000000d', 5.8, 6, 'emotion_log', '00000000-0000-0000-0000-00000000000a', 0.84, '2025-02-10 10:00:00', '2025-03-25 11:00:00'),
(4, 'a0000000-0000-0000-0000-000000000003', 6.0, 9, 'emotion_log', '00000000-0000-0000-0000-000000000004', 0.88, '2025-02-20 09:00:00', '2025-04-04 12:00:00'),
(4, 'a0000000-0000-0000-0000-000000000008', 7.2, 14, 'emotion_log', '00000000-0000-0000-0000-00000000000c', 0.93, '2025-02-20 10:00:00', '2025-04-06 08:00:00'),
(4, 'a0000000-0000-0000-0000-00000000000f', 4.5, 5, 'emotion_log', '00000000-0000-0000-0000-00000000000d', 0.80, '2025-03-01 14:00:00', '2025-04-05 16:00:00'),
(5, 'a0000000-0000-0000-0000-000000000001', 8.0, 15, 'emotion_log', '00000000-0000-0000-0000-000000000005', 0.94, '2025-03-05 11:00:00', '2025-04-08 22:00:00'),
(5, 'a0000000-0000-0000-0000-000000000009', 7.0, 11, 'emotion_log', '00000000-0000-0000-0000-00000000000f', 0.91, '2025-03-06 09:00:00', '2025-04-07 21:00:00'),
(5, 'a0000000-0000-0000-0000-00000000000c', 4.2, 4, 'behavior_regulation', '00000000-0000-0000-0000-000000000057', 0.78, '2025-03-10 15:00:00', '2025-04-01 17:00:00')
ON CONFLICT DO NOTHING;
COMMIT;

-- Data for: user_persona_profiles
BEGIN;
INSERT INTO user_persona_profiles (user_id, tag_cloud, emotion_dominance, behavior_patterns, habit_strength, personality_vector, stability_score, resilience_score, growth_trend, risk_level, profile_version, computed_at) VALUES
(1, '{"完美主义": 7.5, "焦虑倾向": 6.2, "信仰依靠": 5.0, "自律坚持": 4.8}', '{"primary": "焦虑", "secondary": "羞耻", "positive_ratio": 0.35}', '{"coping_style": "active", "avoidance_score": 3, "help_seeking": 7}', '{"streak_avg": 12, "completion_rate": 0.78, "strongest": "晨祷"}', '{"openness": 7, "conscientiousness": 8, "neuroticism": 6, "agreeableness": 7, "extraversion": 5}', 6.5, 7.0, 'improving', 'moderate', 1, '2025-04-08 00:00:00'),
(2, '{"社交敏感": 6.8, "回避型应对": 5.5, "反刍思维": 5.0}', '{"primary": "社交焦虑", "secondary": "孤独", "positive_ratio": 0.40}', '{"coping_style": "avoidant", "avoidance_score": 7, "help_seeking": 3}', '{"streak_avg": 5, "completion_rate": 0.55, "strongest": "阅读"}', '{"openness": 6, "conscientiousness": 5, "neuroticism": 7, "agreeableness": 8, "extraversion": 3}', 5.0, 5.5, 'stable', 'moderate', 1, '2025-04-08 00:00:00'),
(3, '{"情绪敏感": 7.0, "自我批评": 6.5, "讨好型人格": 5.8}', '{"primary": "愧疚", "secondary": "悲伤", "positive_ratio": 0.30}', '{"coping_style": "people_pleasing", "avoidance_score": 5, "help_seeking": 4}', '{"streak_avg": 8, "completion_rate": 0.62, "strongest": "日记"}', '{"openness": 5, "conscientiousness": 6, "neuroticism": 8, "agreeableness": 9, "extraversion": 4}', 4.5, 4.0, 'stable', 'high', 1, '2025-04-08 00:00:00'),
(4, '{"乐观积极": 6.0, "成长导向": 7.2, "韧性成长": 4.5}', '{"primary": "希望", "secondary": "感恩", "positive_ratio": 0.70}', '{"coping_style": "growth_oriented", "avoidance_score": 2, "help_seeking": 8}', '{"streak_avg": 20, "completion_rate": 0.90, "strongest": "运动"}', '{"openness": 8, "conscientiousness": 8, "neuroticism": 3, "agreeableness": 7, "extraversion": 7}', 8.0, 8.5, 'improving', 'low', 1, '2025-04-08 00:00:00'),
(5, '{"焦虑倾向": 8.0, "灾难化思维": 7.0, "情绪化决策": 4.2}', '{"primary": "焦虑", "secondary": "恐惧", "positive_ratio": 0.25}', '{"coping_style": "catastrophizing", "avoidance_score": 6, "help_seeking": 5}', '{"streak_avg": 3, "completion_rate": 0.40, "strongest": "深呼吸"}', '{"openness": 6, "conscientiousness": 4, "neuroticism": 9, "agreeableness": 6, "extraversion": 4}', 3.5, 3.0, 'declining', 'high', 1, '2025-04-08 00:00:00')
ON CONFLICT DO NOTHING;
COMMIT;
