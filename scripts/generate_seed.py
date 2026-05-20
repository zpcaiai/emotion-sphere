#!/usr/bin/env python3
"""Generate seed_all.sql with all schemas + relational test data."""
import uuid, textwrap
from pathlib import Path

R = Path(__file__).resolve().parent.parent
OU = R / "backend" / "seed_all.sql"

def uid(n): return f"'{str(uuid.UUID(int=n))}'"

# pre-generate UUIDs so FKs line up
uids = [uid(i) for i in range(1, 400)]

# shorthand builders
def ins(tbl, rows):
    if not rows: return ""
    cols = list(rows[0].keys())
    lines = ["INSERT INTO " + tbl + " (" + ", ".join(cols) + ") VALUES"]
    for r in rows:
        vs = []
        for c in cols:
            v = r[c]
            if v is None: vs.append("NULL")
            elif isinstance(v, bool): vs.append("TRUE" if v else "FALSE")
            elif isinstance(v, (int, float)): vs.append(str(v))
            else: vs.append("'" + str(v).replace("'", "''") + "'")
        lines.append("(" + ", ".join(vs) + "),")
    lines[-1] = lines[-1].rstrip(",") + ";"
    return "\n".join(lines) + "\n"

out = []

def a(s): out.append(s)

a("""-- ============================================================
-- Emotion Sphere — full schema + linked test data
-- psql $DATABASE_URL -f backend/seed_all.sql
-- ============================================================
BEGIN;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END;$$ LANGUAGE plpgsql;
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$BEGIN NEW.updated_at = CURRENT_TIMESTAMP; RETURN NEW; END;$$ LANGUAGE plpgsql;
""")

# ---------- base tables ----------
BASE = """
CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, email VARCHAR(255) UNIQUE, nickname VARCHAR(100) NOT NULL DEFAULT '', avatar VARCHAR(500) DEFAULT '', openid VARCHAR(255) UNIQUE, unionid VARCHAR(255) UNIQUE, login_type VARCHAR(20) NOT NULL DEFAULT 'email', password_hash VARCHAR(255) DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users (LOWER(email)) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_openid ON users(openid) WHERE openid IS NOT NULL;
DROP TRIGGER IF EXISTS trg_users_updated_at ON users; CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS security_audit (id SERIAL PRIMARY KEY, event_type VARCHAR(50) NOT NULL, email VARCHAR(255), ip_address INET, user_agent TEXT DEFAULT '', details JSONB DEFAULT '{}', success BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_security_audit_email ON security_audit(email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_security_audit_created ON security_audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_security_audit_event_type ON security_audit(event_type);

CREATE TABLE IF NOT EXISTS user_tokens (token VARCHAR(255) PRIMARY KEY, email VARCHAR(255) NOT NULL, data JSONB NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, ip_address INET);
CREATE INDEX IF NOT EXISTS idx_user_tokens_email ON user_tokens(email);
CREATE INDEX IF NOT EXISTS idx_user_tokens_expires ON user_tokens(expires_at);

CREATE TABLE IF NOT EXISTS prayers (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL, nickname VARCHAR(100) DEFAULT '', content TEXT NOT NULL, is_anonymous BOOLEAN DEFAULT FALSE, amen_count INTEGER DEFAULT 0, is_deleted BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_prayers_user ON prayers(user_id);
CREATE INDEX IF NOT EXISTS idx_prayers_created ON prayers(created_at DESC);

CREATE TABLE IF NOT EXISTS prayer_amens (prayer_id INTEGER REFERENCES prayers(id) ON DELETE CASCADE, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (prayer_id, user_id));

CREATE TABLE IF NOT EXISTS evangelism_prayers (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL, nickname VARCHAR(100) DEFAULT '', content TEXT NOT NULL, is_anonymous BOOLEAN DEFAULT FALSE, amen_count INTEGER DEFAULT 0, is_deleted BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_evangelism_user ON evangelism_prayers(user_id);
CREATE INDEX IF NOT EXISTS idx_evangelism_created ON evangelism_prayers(created_at DESC);

CREATE TABLE IF NOT EXISTS evangelism_amens (prayer_id INTEGER REFERENCES evangelism_prayers(id) ON DELETE CASCADE, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (prayer_id, user_id));

CREATE TABLE IF NOT EXISTS devotion_journals (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, date DATE NOT NULL, title VARCHAR(200) DEFAULT '', content TEXT DEFAULT '', verse VARCHAR(200) DEFAULT '', reflection TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE (user_id, date));
CREATE INDEX IF NOT EXISTS idx_devotion_user ON devotion_journals(user_id);
CREATE INDEX IF NOT EXISTS idx_devotion_date ON devotion_journals(user_id, date DESC);

CREATE TABLE IF NOT EXISTS sermon_journals (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, date DATE NOT NULL, title VARCHAR(200) DEFAULT '', preacher VARCHAR(100) DEFAULT '', verse VARCHAR(200) DEFAULT '', content TEXT DEFAULT '', reflection TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE (user_id, date));
CREATE INDEX IF NOT EXISTS idx_sermon_user ON sermon_journals(user_id);
CREATE INDEX IF NOT EXISTS idx_sermon_date ON sermon_journals(user_id, date DESC);

CREATE TABLE IF NOT EXISTS personal_notes (id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, date DATE NOT NULL, title VARCHAR(200) DEFAULT '', content TEXT DEFAULT '', mood VARCHAR(50) DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE (user_id, date));
CREATE INDEX IF NOT EXISTS idx_personal_user ON personal_notes(user_id);

CREATE TABLE IF NOT EXISTS checkins (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL, nickname VARCHAR(100) DEFAULT '', emotion_label VARCHAR(100) DEFAULT '', emotion_key VARCHAR(200) DEFAULT '', note TEXT DEFAULT '', is_anonymous BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_checkins_user ON checkins(user_id);
CREATE INDEX IF NOT EXISTS idx_checkins_created ON checkins(created_at DESC);
"""

a(BASE)

PSY = """
CREATE TABLE IF NOT EXISTS emotion_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, raw_text TEXT NOT NULL, emotion_tags TEXT[], intensity INTEGER CHECK (intensity BETWEEN 1 AND 10), occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, context_json JSONB DEFAULT '{}', source VARCHAR(50) DEFAULT 'web', CONSTRAINT uq_emotion_logs_user_time UNIQUE (user_id, occurred_at, id));
CREATE INDEX IF NOT EXISTS idx_emotion_logs_user_id ON emotion_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_emotion_logs_occurred_at ON emotion_logs(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_emotion_logs_emotion_tags ON emotion_logs USING GIN(emotion_tags);

CREATE TABLE IF NOT EXISTS personality_drivers (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, log_id UUID REFERENCES emotion_logs(id) ON DELETE CASCADE, surface_problem TEXT, deep_emotion TEXT, hidden_dynamics TEXT, behavioral_cycle JSONB, personality_traits JSONB, long_term_risk TEXT, intervention_priority INTEGER, driver_category VARCHAR(50), core_belief TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_personality_drivers_user_id ON personality_drivers(user_id);
CREATE INDEX IF NOT EXISTS idx_personality_drivers_log_id ON personality_drivers(log_id);
CREATE INDEX IF NOT EXISTS idx_personality_drivers_category ON personality_drivers(driver_category);

CREATE TABLE IF NOT EXISTS behavioral_triggers (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, trigger_name VARCHAR(200) NOT NULL, trigger_type VARCHAR(50), trigger_pattern TEXT, activating_event TEXT, belief_system JSONB, consequence JSONB, frequency_count INTEGER DEFAULT 1, last_triggered_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_behavioral_triggers_user_id ON behavioral_triggers(user_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_triggers_type ON behavioral_triggers(trigger_type);

CREATE TABLE IF NOT EXISTS cognitive_schemas (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, schema_name VARCHAR(100) NOT NULL, distortion_type VARCHAR(50), activating_event TEXT, consequence_emotional TEXT, consequence_behavioral TEXT, core_belief TEXT, latent_schema JSONB, cognitive_reframing_patch TEXT, reframing_evidence JSONB, is_active BOOLEAN DEFAULT TRUE, severity_score INTEGER CHECK (severity_score BETWEEN 1 AND 10), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, resolved_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_user_id ON cognitive_schemas(user_id);
CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_distortion ON cognitive_schemas(distortion_type);
CREATE INDEX IF NOT EXISTS idx_cognitive_schemas_active ON cognitive_schemas(user_id, is_active);
DROP TRIGGER IF EXISTS trg_cognitive_schemas_updated ON cognitive_schemas; CREATE TRIGGER trg_cognitive_schemas_updated BEFORE UPDATE ON cognitive_schemas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS behavioral_experiments (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, schema_id UUID REFERENCES cognitive_schemas(id) ON DELETE SET NULL, experiment_id VARCHAR(100) UNIQUE, title VARCHAR(200) NOT NULL, hypothesis_to_test TEXT, counter_behavioral_action TEXT, difficulty_level INTEGER CHECK (difficulty_level BETWEEN 1 AND 5), estimated_duration_minutes INTEGER, binary_telemetry_metric TEXT, success_criteria JSONB, status VARCHAR(20) DEFAULT 'pending', scheduled_at TIMESTAMP, completed_at TIMESTAMP, actual_outcome JSONB, hypothesis_falsified BOOLEAN, user_reflection TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reminder_sent BOOLEAN DEFAULT FALSE);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_user_id ON behavioral_experiments(user_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_schema ON behavioral_experiments(schema_id);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_status ON behavioral_experiments(status);
CREATE INDEX IF NOT EXISTS idx_behavioral_experiments_scheduled ON behavioral_experiments(scheduled_at);

CREATE TABLE IF NOT EXISTS psychological_states (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, state_name VARCHAR(50) NOT NULL, state_level INTEGER CHECK (state_level BETWEEN 0 AND 4), arousal_level INTEGER CHECK (arousal_level BETWEEN 1 AND 10), valence_score INTEGER CHECK (valence_score BETWEEN -10 AND 10), focus_capacity INTEGER CHECK (focus_capacity BETWEEN 1 AND 10), triggering_factors JSONB[], protective_factors JSONB[], recommended_action TEXT, escalation_protocol TEXT, captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, previous_state_id UUID REFERENCES psychological_states(id), state_duration_seconds INTEGER);
CREATE INDEX IF NOT EXISTS idx_psychological_states_user_id ON psychological_states(user_id);
CREATE INDEX IF NOT EXISTS idx_psychological_states_captured ON psychological_states(captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_psychological_states_level ON psychological_states(state_level);

CREATE TABLE IF NOT EXISTS intervention_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, state_id UUID REFERENCES psychological_states(id) ON DELETE SET NULL, experiment_id UUID REFERENCES behavioral_experiments(id) ON DELETE SET NULL, intervention_type VARCHAR(50), intervention_layer INTEGER CHECK (intervention_layer BETWEEN 0 AND 4), prompt_text TEXT, technique_used VARCHAR(100), was_delivered BOOLEAN DEFAULT FALSE, user_response TEXT, effectiveness_score INTEGER CHECK (effectiveness_score BETWEEN 1 AND 10), delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, responded_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_intervention_logs_user_id ON intervention_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_intervention_logs_delivered ON intervention_logs(delivered_at DESC);

CREATE TABLE IF NOT EXISTS identity_narratives (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, narrative_type VARCHAR(50), narrative_title VARCHAR(200), narrative_text TEXT, identity_themes JSONB[], core_values JSONB[], narrative_period_start DATE, narrative_period_end DATE, is_current BOOLEAN DEFAULT FALSE, coherence_score INTEGER CHECK (coherence_score BETWEEN 1 AND 10), agency_score INTEGER CHECK (agency_score BETWEEN 1 AND 10), redemption_score INTEGER CHECK (redemption_score BETWEEN 1 AND 10), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, CONSTRAINT unique_current_narrative UNIQUE (user_id, is_current) DEFERRABLE INITIALLY DEFERRED);
CREATE INDEX IF NOT EXISTS idx_identity_narratives_user_id ON identity_narratives(user_id);
CREATE INDEX IF NOT EXISTS idx_identity_narratives_current ON identity_narratives(user_id, is_current) WHERE is_current = TRUE;
DROP TRIGGER IF EXISTS trg_identity_narratives_updated ON identity_narratives; CREATE TRIGGER trg_identity_narratives_updated BEFORE UPDATE ON identity_narratives FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS self_concept_models (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, self_efficacy INTEGER CHECK (self_efficacy BETWEEN 1 AND 10), self_worth INTEGER CHECK (self_worth BETWEEN 1 AND 10), self_stability INTEGER CHECK (self_stability BETWEEN 1 AND 10), ideal_self JSONB, actual_self JSONB, discrepancy_score INTEGER CHECK (discrepancy_score BETWEEN 0 AND 10), identity_commitments JSONB[], assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, next_assessment_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_self_concept_user_id ON self_concept_models(user_id);
CREATE INDEX IF NOT EXISTS idx_self_concept_assessed ON self_concept_models(assessed_at DESC);

CREATE TABLE IF NOT EXISTS growth_trajectories (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, period_type VARCHAR(20), period_start DATE NOT NULL, period_end DATE NOT NULL, emotional_regulation_score INTEGER CHECK (emotional_regulation_score BETWEEN 1 AND 100), cognitive_flexibility_score INTEGER CHECK (cognitive_flexibility_score BETWEEN 1 AND 100), behavioral_activation_score INTEGER CHECK (behavioral_activation_score BETWEEN 1 AND 100), interpersonal_effectiveness_score INTEGER CHECK (interpersonal_effectiveness_score BETWEEN 1 AND 100), self_concept_clarity_score INTEGER CHECK (self_concept_clarity_score BETWEEN 1 AND 100), change_from_last_period JSONB, significant_events JSONB[], generated_insights TEXT[], recommended_focus_areas TEXT[], calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_growth_trajectories_user_id ON growth_trajectories(user_id);
CREATE INDEX IF NOT EXISTS idx_growth_trajectories_period ON growth_trajectories(user_id, period_type, period_start DESC);

CREATE TABLE IF NOT EXISTS pattern_recognitions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, pattern_type VARCHAR(50), pattern_name VARCHAR(200), pattern_description TEXT, detected_in_logs UUID[], time_range_start TIMESTAMP, time_range_end TIMESTAMP, frequency_pattern JSONB, trigger_pattern JSONB, response_pattern JSONB, predictability_score INTEGER CHECK (predictability_score BETWEEN 1 AND 10), next_occurrence_prediction TIMESTAMP, breaking_strategy TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_active BOOLEAN DEFAULT TRUE);
CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_user_id ON pattern_recognitions(user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_recognitions_type ON pattern_recognitions(pattern_type);

CREATE TABLE IF NOT EXISTS memory_consolidations (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, memory_type VARCHAR(50), memory_title VARCHAR(200), memory_content TEXT, emotional_valence INTEGER CHECK (emotional_valence BETWEEN -10 AND 10), emotional_arousal INTEGER CHECK (emotional_arousal BETWEEN 1 AND 10), related_logs UUID[], related_schemas UUID[], related_narratives UUID[], memory_strength INTEGER CHECK (memory_strength BETWEEN 1 AND 100), last_accessed_at TIMESTAMP, access_count INTEGER DEFAULT 1, original_event_at TIMESTAMP, consolidated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_archived BOOLEAN DEFAULT FALSE);
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_user_id ON memory_consolidations(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_type ON memory_consolidations(memory_type);
CREATE INDEX IF NOT EXISTS idx_memory_consolidations_strength ON memory_consolidations(user_id, memory_strength DESC);

CREATE TABLE IF NOT EXISTS behavior_regulation_sessions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, session_type VARCHAR(50), target_habit VARCHAR(200), motivation_level INTEGER CHECK (motivation_level BETWEEN 1 AND 10), ability_level INTEGER CHECK (ability_level BETWEEN 1 AND 10), trigger_strength INTEGER CHECK (trigger_strength BETWEEN 1 AND 10), energy_level INTEGER CHECK (energy_level BETWEEN 1 AND 5), behavioral_resistance INTEGER CHECK (behavioral_resistance BETWEEN 1 AND 10), cognitive_load INTEGER CHECK (cognitive_load BETWEEN 1 AND 10), emotional_stability INTEGER CHECK (emotional_stability BETWEEN 1 AND 10), attention_state VARCHAR(20), procrastination_level INTEGER CHECK (procrastination_level BETWEEN 1 AND 10), selected_tier VARCHAR(10), min_executable_action TEXT, task_downgrade TEXT, emotional_compensation TEXT, continuity_advice TEXT, was_executed BOOLEAN DEFAULT FALSE, execution_duration_seconds INTEGER, completion_percentage INTEGER CHECK (completion_percentage BETWEEN 0 AND 100), started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP, shame_mitigation_applied BOOLEAN DEFAULT FALSE, continuity_preserved BOOLEAN DEFAULT TRUE);
CREATE INDEX IF NOT EXISTS idx_behavior_sessions_user ON behavior_regulation_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_behavior_sessions_time ON behavior_regulation_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_behavior_sessions_energy ON behavior_regulation_sessions(user_id, energy_level);

CREATE TABLE IF NOT EXISTS habit_state_machines (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, habit_name VARCHAR(200) NOT NULL, habit_description TEXT, category VARCHAR(50), deterministic_anchor VARCHAR(200), trigger_anchor_time TIME, tier_green_config JSONB, tier_yellow_config JSONB, tier_red_config JSONB, token_green_yield INTEGER DEFAULT 10, token_yellow_yield INTEGER DEFAULT 5, token_red_yield INTEGER DEFAULT 1, is_active BOOLEAN DEFAULT TRUE, current_streak_days INTEGER DEFAULT 0, max_streak_days INTEGER DEFAULT 0, total_executions INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_execution_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_habit_machines_user ON habit_state_machines(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_machines_active ON habit_state_machines(user_id, is_active);
DROP TRIGGER IF EXISTS trg_habit_machines_updated ON habit_state_machines; CREATE TRIGGER trg_habit_machines_updated BEFORE UPDATE ON habit_state_machines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE IF NOT EXISTS habit_execution_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, habit_id UUID REFERENCES habit_state_machines(id) ON DELETE CASCADE, energy_level_at_execution INTEGER CHECK (energy_level_at_execution BETWEEN 1 AND 5), selected_tier VARCHAR(10), action_taken TEXT, execution_duration_seconds INTEGER, tokens_earned INTEGER, was_completed BOOLEAN DEFAULT FALSE, completion_percentage INTEGER CHECK (completion_percentage BETWEEN 0 AND 100), circuit_breaker_triggered BOOLEAN DEFAULT FALSE, anti_guilt_message_shown BOOLEAN DEFAULT FALSE, mood_before INTEGER CHECK (mood_before BETWEEN 1 AND 10), mood_after INTEGER CHECK (mood_after BETWEEN 1 AND 10), executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_habit_logs_user ON habit_execution_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs_habit ON habit_execution_logs(habit_id);
CREATE INDEX IF NOT EXISTS idx_habit_logs_time ON habit_execution_logs(executed_at DESC);

CREATE TABLE IF NOT EXISTS user_token_ledgers (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, current_balance INTEGER DEFAULT 0, lifetime_earned INTEGER DEFAULT 0, lifetime_spent INTEGER DEFAULT 0, green_tier_count INTEGER DEFAULT 0, yellow_tier_count INTEGER DEFAULT 0, red_tier_count INTEGER DEFAULT 0, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_token_ledger_user ON user_token_ledgers(user_id);

CREATE TABLE IF NOT EXISTS token_transactions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, transaction_type VARCHAR(20), amount INTEGER, balance_after INTEGER, habit_id UUID REFERENCES habit_state_machines(id) ON DELETE SET NULL, habit_log_id UUID REFERENCES habit_execution_logs(id) ON DELETE SET NULL, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_token_tx_user ON token_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_token_tx_time ON token_transactions(created_at DESC);

CREATE TABLE IF NOT EXISTS execution_paralysis_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, paralysis_type VARCHAR(50), detected_signals JSONB[], raw_backlog_task TEXT, edge_context JSONB, tab_switch_count INTEGER, idle_duration_seconds INTEGER, window_thrashing BOOLEAN DEFAULT FALSE, intervention_triggered BOOLEAN DEFAULT FALSE, ignition_sequence_delivered TEXT, user_responded BOOLEAN DEFAULT FALSE, response_latency_seconds INTEGER, ignition_completed BOOLEAN DEFAULT FALSE, task_restarted BOOLEAN DEFAULT FALSE, post_intervention_mood INTEGER CHECK (post_intervention_mood BETWEEN 1 AND 10), detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, intervened_at TIMESTAMP, completed_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_paralysis_logs_user ON execution_paralysis_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_paralysis_logs_time ON execution_paralysis_logs(detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_paralysis_logs_type ON execution_paralysis_logs(paralysis_type);

CREATE TABLE IF NOT EXISTS micro_scheduler_sessions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, paralysis_log_id UUID REFERENCES execution_paralysis_logs(id) ON DELETE SET NULL, session_status VARCHAR(20) DEFAULT 'active', original_task TEXT, decoupled_chain JSONB[], current_step_index INTEGER DEFAULT 0, context_isolation JSONB, noise_floor_level INTEGER CHECK (noise_floor_level BETWEEN 1 AND 10), telemetry_signals JSONB[], last_user_signal_at TIMESTAMP, steps_completed INTEGER DEFAULT 0, total_steps INTEGER, micro_momentum_score INTEGER CHECK (micro_momentum_score BETWEEN 1 AND 100), started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_step_at TIMESTAMP, completed_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_micro_scheduler_user ON micro_scheduler_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_micro_scheduler_status ON micro_scheduler_sessions(session_status);

CREATE TABLE IF NOT EXISTS implementation_intentions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, intention_name VARCHAR(200), if_trigger TEXT, then_action TEXT, applicable_contexts JSONB, usage_count INTEGER DEFAULT 0, success_rate INTEGER CHECK (success_rate BETWEEN 0 AND 100), avg_completion_time_seconds INTEGER, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_used_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_intentions_user ON implementation_intentions(user_id);
CREATE INDEX IF NOT EXISTS idx_intentions_active ON implementation_intentions(user_id, is_active);

CREATE TABLE IF NOT EXISTS edge_intervention_analytics (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, period_type VARCHAR(20), period_start DATE, period_end DATE, paralysis_events_count INTEGER DEFAULT 0, avg_detection_latency_seconds INTEGER, interventions_triggered INTEGER DEFAULT 0, ignition_completion_rate INTEGER CHECK (ignition_completion_rate BETWEEN 0 AND 100), task_restart_success_rate INTEGER CHECK (task_restart_success_rate BETWEEN 0 AND 100), micro_momentum_avg INTEGER CHECK (micro_momentum_avg BETWEEN 1 AND 100), continuity_preservation_score INTEGER CHECK (continuity_preservation_score BETWEEN 1 AND 100), top_paralysis_triggers TEXT[], most_effective_ignitions JSONB[], recommended_adjustments TEXT[], calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_edge_analytics_user ON edge_intervention_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_edge_analytics_period ON edge_intervention_analytics(user_id, period_type, period_start DESC);

CREATE TABLE IF NOT EXISTS identity_reinforcement_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, current_narrative TEXT, narrative_type VARCHAR(50), negative_identity_labels TEXT[], target_identity TEXT, identity_category VARCHAR(50), reinforcement_language TEXT, user_reflection TEXT, reinforcement_strength INTEGER CHECK (reinforcement_strength BETWEEN 1 AND 10), user_resonance INTEGER CHECK (user_resonance BETWEEN 1 AND 10), migration_direction VARCHAR(50), migration_progress INTEGER CHECK (migration_progress BETWEEN 0 AND 100), related_emotion_log_id UUID REFERENCES emotion_logs(id) ON DELETE SET NULL, related_habit_id UUID REFERENCES habit_state_machines(id) ON DELETE SET NULL, related_intervention_id UUID REFERENCES execution_paralysis_logs(id) ON DELETE SET NULL, reinforced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_identity_logs_user ON identity_reinforcement_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_identity_logs_time ON identity_reinforcement_logs(reinforced_at DESC);
CREATE INDEX IF NOT EXISTS idx_identity_logs_category ON identity_reinforcement_logs(identity_category);

CREATE TABLE IF NOT EXISTS personality_migrations (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, migration_dimension VARCHAR(50), starting_identity TEXT, target_identity TEXT, migration_path JSONB[], current_stage INTEGER DEFAULT 0, supporting_evidence JSONB[], migration_status VARCHAR(20) DEFAULT 'in_progress', progress_percentage INTEGER CHECK (progress_percentage BETWEEN 0 AND 100), started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, estimated_completion TIMESTAMP, achieved_at TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_migration_user ON personality_migrations(user_id);
CREATE INDEX IF NOT EXISTS idx_migration_dimension ON personality_migrations(user_id, migration_dimension);

CREATE TABLE IF NOT EXISTS system_state_definitions (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), state_name VARCHAR(50) UNIQUE NOT NULL, state_code VARCHAR(20) UNIQUE NOT NULL, arousal_range JSONB, valence_range JSONB, energy_level_range JSONB, trigger_conditions JSONB[], behavior_strategy TEXT, task_intensity VARCHAR(20), social_interaction VARCHAR(20), prompt_tone VARCHAR(20), prompt_focus TEXT[], is_active BOOLEAN DEFAULT TRUE);

CREATE TABLE IF NOT EXISTS user_system_states (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE, current_state_code VARCHAR(20) DEFAULT 'NORMAL', previous_state_code VARCHAR(20), state_entered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, state_duration_seconds INTEGER DEFAULT 0, state_transition_reason TEXT, current_arousal INTEGER CHECK (current_arousal BETWEEN 1 AND 10), current_valence INTEGER CHECK (current_valence BETWEEN -10 AND 10), current_energy_level INTEGER CHECK (current_energy_level BETWEEN 1 AND 5), auto_regulation_enabled BOOLEAN DEFAULT TRUE, system_energy_override INTEGER, psychology_layer_active BOOLEAN DEFAULT TRUE, behavior_layer_active BOOLEAN DEFAULT TRUE, execution_layer_active BOOLEAN DEFAULT TRUE, identity_layer_active BOOLEAN DEFAULT TRUE, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_user_states_current ON user_system_states(user_id, current_state_code);

CREATE TABLE IF NOT EXISTS state_transition_logs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, from_state_code VARCHAR(20), to_state_code VARCHAR(20), transition_trigger TEXT, arousal_at_transition INTEGER, valence_at_transition INTEGER, energy_at_transition INTEGER, auto_interventions JSONB[], signals_broadcast JSONB[], transitioned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_state_transitions_user ON state_transition_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_state_transitions_time ON state_transition_logs(transitioned_at DESC);

CREATE TABLE IF NOT EXISTS data_bus_events (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), event_type VARCHAR(50), event_source VARCHAR(50), event_target VARCHAR(50), event_payload JSONB, priority INTEGER DEFAULT 5, ttl_seconds INTEGER DEFAULT 300, is_processed BOOLEAN DEFAULT FALSE, processed_at TIMESTAMP, processed_by VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_bus_events_unprocessed ON data_bus_events(is_processed, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS idx_bus_events_target ON data_bus_events(event_target, is_processed);

CREATE TABLE IF NOT EXISTS dynamic_load_configs (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, cognitive_load_score INTEGER CHECK (cognitive_load_score BETWEEN 1 AND 10), emotional_load_score INTEGER CHECK (emotional_load_score BETWEEN 1 AND 10), behavioral_load_score INTEGER CHECK (behavioral_load_score BETWEEN 1 AND 10), auto_override_enabled BOOLEAN DEFAULT TRUE, red_tier_threshold INTEGER DEFAULT 2, current_system_energy_level INTEGER DEFAULT 3, current_task_intensity VARCHAR(20) DEFAULT 'full', current_prompt_tone VARCHAR(20) DEFAULT 'supportive', last_circuit_breaker_at TIMESTAMP, circuit_breaker_count_7d INTEGER DEFAULT 0, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE UNIQUE INDEX IF NOT EXISTS idx_load_config_user ON dynamic_load_configs(user_id);
"""

a(PSY)

# ---------- data ----------

# users
a(ins("users", [
    {"id":1,"email":"alice@example.com","nickname":"Alice","avatar":"https://i.pravatar.cc/150?u=alice","login_type":"email","password_hash":"bcrypt:xxx","created_at":"2025-01-10 08:00:00"},
    {"id":2,"email":"bob@example.com","nickname":"Bob","avatar":"https://i.pravatar.cc/150?u=bob","login_type":"email","password_hash":"bcrypt:xxx","created_at":"2025-01-15 10:30:00"},
    {"id":3,"email":"charlie@example.com","nickname":"Charlie","avatar":"","login_type":"wxapp","password_hash":"","created_at":"2025-02-01 14:00:00"},
    {"id":4,"email":"diana@example.com","nickname":"Diana","avatar":"https://i.pravatar.cc/150?u=diana","login_type":"email","password_hash":"bcrypt:xxx","created_at":"2025-02-20 09:00:00"},
    {"id":5,"email":"eve@example.com","nickname":"Eve","avatar":"","login_type":"email","password_hash":"bcrypt:xxx","created_at":"2025-03-05 11:00:00"},
]))

# security_audit
a(ins("security_audit", [
    {"event_type":"LOGIN_SUCCESS","email":"alice@example.com","ip_address":"192.168.1.10","details":'{"device": "chrome"}',"success":True,"created_at":"2025-01-10 08:05:00"},
    {"event_type":"REGISTER_SUCCESS","email":"bob@example.com","ip_address":"192.168.1.11","details":'{"source": "web"}',"success":True,"created_at":"2025-01-15 10:30:00"},
    {"event_type":"LOGIN_FAILED","email":"eve@example.com","ip_address":"10.0.0.5","details":'{"reason": "wrong_password"}',"success":False,"created_at":"2025-03-05 12:00:00"},
    {"event_type":"WXAPP_LOGIN_SUCCESS","email":None,"ip_address":"172.16.0.3","details":'{"openid": "oxxx"}',"success":True,"created_at":"2025-02-01 14:00:00"},
    {"event_type":"PASSWORD_RESET_SUCCESS","email":"alice@example.com","ip_address":"192.168.1.10","details":'{}',"success":True,"created_at":"2025-04-01 09:00:00"},
    {"event_type":"LOGOUT","email":"bob@example.com","ip_address":"192.168.1.11","details":'{}',"success":True,"created_at":"2025-01-20 18:00:00"},
    {"event_type":"EMAIL_SEND_CODE","email":"diana@example.com","ip_address":"192.168.1.12","details":'{"type": "register"}',"success":True,"created_at":"2025-02-20 09:01:00"},
    {"event_type":"PRAYER_SUBMIT","email":"alice@example.com","ip_address":"192.168.1.10","details":'{"prayer_id": 1}',"success":True,"created_at":"2025-01-12 20:00:00"},
    {"event_type":"SESSION_EXPIRED","email":"eve@example.com","ip_address":"10.0.0.5","details":'{"token_age_days": 31}',"success":False,"created_at":"2025-04-10 08:00:00"},
    {"event_type":"PROFILE_UPDATE","email":"charlie@example.com","ip_address":"172.16.0.3","details":'{"field": "nickname"}',"success":True,"created_at":"2025-03-01 15:00:00"},
]))

# prayers
a(ins("prayers", [
    {"user_id":1,"nickname":"Alice","content":"为家人健康祷告，求主保守。","is_anonymous":False,"amen_count":3,"created_at":"2025-01-12 20:00:00"},
    {"user_id":2,"nickname":"Bob","content":"工作中遇到困难，求主赐智慧。","is_anonymous":False,"amen_count":5,"created_at":"2025-01-18 08:30:00"},
    {"user_id":1,"nickname":"Alice","content":"为考试顺利通过祈求。","is_anonymous":False,"amen_count":2,"created_at":"2025-02-05 14:00:00"},
    {"user_id":None,"nickname":"匿名","content":"心里很难过，求主安慰。","is_anonymous":True,"amen_count":7,"created_at":"2025-02-14 22:00:00"},
    {"user_id":3,"nickname":"Charlie","content":"刚信主，求主坚固信心。","is_anonymous":False,"amen_count":4,"created_at":"2025-02-20 10:00:00"},
    {"user_id":4,"nickname":"Diana","content":"求职面试，求主带领。","is_anonymous":False,"amen_count":1,"created_at":"2025-03-01 09:00:00"},
    {"user_id":2,"nickname":"Bob","content":"为远方的朋友代祷。","is_anonymous":False,"amen_count":2,"created_at":"2025-03-10 19:00:00"},
    {"user_id":5,"nickname":"Eve","content":"求主医治我的失眠。","is_anonymous":False,"amen_count":6,"created_at":"2025-03-15 23:00:00"},
    {"user_id":1,"nickname":"Alice","content":"感恩主，今天顺利完成了项目。","is_anonymous":False,"amen_count":0,"created_at":"2025-04-01 17:00:00"},
    {"user_id":None,"nickname":"匿名","content":"请不要为我祷告，只是来倾诉。","is_anonymous":True,"amen_count":0,"created_at":"2025-04-10 21:00:00"},
]))

a(ins("prayer_amens", [
    {"prayer_id":1,"user_id":2,"created_at":"2025-01-13 08:00:00"},
    {"prayer_id":1,"user_id":3,"created_at":"2025-01-13 09:00:00"},
    {"prayer_id":2,"user_id":1,"created_at":"2025-01-18 10:00:00"},
    {"prayer_id":2,"user_id":4,"created_at":"2025-01-19 11:00:00"},
    {"prayer_id":3,"user_id":2,"created_at":"2025-02-06 08:00:00"},
    {"prayer_id":5,"user_id":1,"created_at":"2025-02-21 07:00:00"},
    {"prayer_id":5,"user_id":2,"created_at":"2025-02-21 08:00:00"},
    {"prayer_id":7,"user_id":3,"created_at":"2025-03-11 10:00:00"},
]))

a(ins("evangelism_prayers", [
    {"user_id":1,"nickname":"Alice","content":"求主预备传道的机会给公司同事。","is_anonymous":False,"amen_count":2,"created_at":"2025-01-20 12:00:00"},
    {"user_id":2,"nickname":"Bob","content":"为不信主的父母祷告，soften their hearts.","is_anonymous":False,"amen_count":4,"created_at":"2025-01-25 18:00:00"},
    {"user_id":None,"nickname":"匿名","content":"求主赐胆量向室友传福音。","is_anonymous":True,"amen_count":3,"created_at":"2025-02-10 20:00:00"},
    {"user_id":4,"nickname":"Diana","content":"为教会的布道会预备祷告。","is_anonymous":False,"amen_count":1,"created_at":"2025-03-05 07:00:00"},
    {"user_id":3,"nickname":"Charlie","content":"刚向同学分享了福音，求主浇灌。","is_anonymous":False,"amen_count":5,"created_at":"2025-03-20 16:00:00"},
]))

a(ins("evangelism_amens", [
    {"prayer_id":1,"user_id":3,"created_at":"2025-01-21 08:00:00"},
    {"prayer_id":2,"user_id":1,"created_at":"2025-01-26 09:00:00"},
    {"prayer_id":2,"user_id":4,"created_at":"2025-01-27 10:00:00"},
    {"prayer_id":5,"user_id":1,"created_at":"2025-03-21 08:00:00"},
    {"prayer_id":5,"user_id":2,"created_at":"2025-03-21 09:00:00"},
]))

a(ins("devotion_journals", [
    {"user_id":1,"date":"2025-01-12","title":"登山宝训心得","content":"今天读了马太福音5章...","verse":"马太福音 5:3-10","reflection":"虚心的人有福了，因为天国是他们的。","created_at":"2025-01-12 21:00:00"},
    {"user_id":1,"date":"2025-01-19","title":"好撒玛利亚人","content":"路加福音10章的故事让我深思...","verse":"路加福音 10:25-37","reflection":"爱邻舍如同自己，不仅限于认识的人。","created_at":"2025-01-19 22:00:00"},
    {"user_id":2,"date":"2025-01-20","title":"初信读经","content":"第一次完整读完一卷书...","verse":"约翰福音 3:16","reflection":"神爱世人，这是何等大的爱。","created_at":"2025-01-20 20:30:00"},
    {"user_id":3,"date":"2025-02-05","title":"腓立比书4:6","content":"凡事藉着祷告、祈求...","verse":"腓立比书 4:6-7","reflection":"在焦虑中学习交托，是每天的功课。","created_at":"2025-02-05 21:00:00"},
    {"user_id":4,"date":"2025-03-01","title":"诗篇23篇","content":"耶和华是我的牧者...","verse":"诗篇 23:1-4","reflection":"在低谷中神的同在是最真实的安慰。","created_at":"2025-03-01 20:00:00"},
    {"user_id":1,"date":"2025-03-15","title":"罗马书8章","content":"圣灵与我们的软弱...","verse":"罗马书 8:26","reflection":"不知道如何祷告时，圣灵亲自代求。","created_at":"2025-03-15 21:30:00"},
    {"user_id":2,"date":"2025-04-01","title":"复活节默想","content":"基督从死里复活的意义...","verse":"哥林多前书 15:4","reflection":"因祂活着，我能面对明天。","created_at":"2025-04-01 19:00:00"},
    {"user_id":5,"date":"2025-04-10","title":"雅各书1章","content":"试炼生忍耐...","verse":"雅各书 1:2-4","reflection":"在困难中看见成长的契机。","created_at":"2025-04-10 20:00:00"},
    {"user_id":3,"date":"2025-04-15","title":"以弗所书6章","content":"属灵军装...","verse":"以弗所书 6:10-18","reflection":"每天都要穿戴神所赐的全副军装。","created_at":"2025-04-15 21:00:00"},
    {"user_id":4,"date":"2025-04-20","title":"箴言3章","content":"专心仰赖耶和华...","verse":"箴言 3:5-6","reflection":"承认祂，祂必指引我的路。","created_at":"2025-04-20 20:00:00"},
]))

a(ins("sermon_journals", [
    {"user_id":1,"date":"2025-01-12","title":"新年的盼望","preacher":"张牧师","verse":"耶利米书 29:11","content":"今天的信息讲到了神对百姓的计划...","reflection":"我也要在新的一年里更多信靠祂的计划。","created_at":"2025-01-12 14:00:00"},
    {"user_id":2,"date":"2025-01-19","title":"信心的一小步","preacher":"李传道","verse":"马太福音 14:29","content":"彼得在水面上行走的故事...","reflection":"信心不需要很大，只要愿意跨出一步。","created_at":"2025-01-19 14:30:00"},
    {"user_id":1,"date":"2025-02-02","title":"爱的真谛","preacher":"王牧师","verse":"哥林多前书 13:4-8","content":"爱是恒久忍耐，又有恩慈...","reflection":"需要在生活中更多操练对家人的爱。","created_at":"2025-02-02 14:00:00"},
    {"user_id":3,"date":"2025-02-16","title":"初信造就","preacher":"陈长老","verse":"约翰福音 1:12","content":"凡接待祂的，就是神的儿女...","reflection":"确信自己已经是神的儿女，这带来平安。","created_at":"2025-02-16 13:00:00"},
    {"user_id":4,"date":"2025-03-02","title":"圣灵的果子","preacher":"赵牧师","verse":"加拉太书 5:22-23","content":"仁爱、喜乐、和平、忍耐、恩慈...","reflection":"需要在忍耐和节制上更多成长。","created_at":"2025-03-02 14:00:00"},
    {"user_id":2,"date":"2025-03-16","title":"饶恕的力量","preacher":"孙传道","verse":"马太福音 18:21-22","content":"彼得问主饶恕几次...","reflection":"饶恕不是感觉，而是选择释放对方。","created_at":"2025-03-16 14:00:00"},
    {"user_id":1,"date":"2025-04-06","title":"复活节的清晨","preacher":"张牧师","verse":"马可福音 16:6","content":"基督已经复活了...","reflection":"因祂复活，我的信仰有确据。","created_at":"2025-04-06 14:00:00"},
    {"user_id":5,"date":"2025-04-13","title":"祷告的生活","preacher":"李牧师","verse":"帖撒罗尼迦前书 5:17","content":"要常常祷告...","reflection":"需要在忙碌中也不忽略与神的交通。","created_at":"2025-04-13 14:00:00"},
    {"user_id":3,"date":"2025-04-20","title":"初信答疑","preacher":"陈长老","verse":"罗马书 10:9","content":"口里承认，心里相信...","reflection":"对因信称义有了更深的理解。","created_at":"2025-04-20 13:30:00"},
    {"user_id":4,"date":"2025-04-27","title":"管家职分","preacher":"王牧师","verse":"路加福音 16:10","content":"在最小的事上忠心...","reflection":"要管理好神所赐的时间和才干。","created_at":"2025-04-27 14:00:00"},
]))

a(ins("personal_notes", [
    {"user_id":1,"date":"2025-01-11","title":"周一感悟","content":"新的一周开始了，求主加力。","mood":"平静","created_at":"2025-01-11 07:00:00"},
    {"user_id":2,"date":"2025-01-22","title":"工作压力大","content":"项目deadline快到了，有点焦虑。","mood":"焦虑","created_at":"2025-01-22 22:00:00"},
    {"user_id":1,"date":"2025-02-14","title":"情人节独处","content":"一个人也挺好，神的爱足够。","mood":"感恩","created_at":"2025-02-14 23:00:00"},
    {"user_id":3,"date":"2025-03-01","title":"搬家","content":"搬到新城市，一切重新开始。","mood":"期待","created_at":"2025-03-01 20:00:00"},
    {"user_id":4,"date":"2025-03-20","title":"失业第7天","content":"投了几十份简历没有回音，心很慌。","mood":"沮丧","created_at":"2025-03-20 21:00:00"},
    {"user_id":5,"date":"2025-04-05","title":"失眠夜","content":"凌晨3点还睡不着，起来祷告。","mood":"疲惫","created_at":"2025-04-05 03:00:00"},
    {"user_id":1,"date":"2025-04-12","title":"收到好消息","content":"面试通过了！感谢主。","mood":"喜乐","created_at":"2025-04-12 10:00:00"},
    {"user_id":2,"date":"2025-04-18","title":"与好友和好","content":"冷战一周的室友终于说话了。","mood":"轻松","created_at":"2025-04-18 21:00:00"},
    {"user_id":3,"date":"2025-04-25","title":"第一次带领查经","content":"紧张但感恩，神赐下属灵的智慧。","mood":"满足","created_at":"2025-04-25 20:30:00"},
    {"user_id":4,"date":"2025-05-01","title":"新的开始","content":"入职新公司第一天，感恩主的带领。","mood":"感恩","created_at":"2025-05-01 22:00:00"},
]))

a(ins("checkins", [
    {"user_id":1,"nickname":"Alice","emotion_label":"感恩","emotion_key":"gratitude","note":"今天天气很好，读完了一章圣经。","is_anonymous":False,"created_at":"2025-01-10 09:00:00"},
    {"user_id":2,"nickname":"Bob","emotion_label":"焦虑","emotion_key":"anxiety","note":"明天有重要汇报，有点紧张。","is_anonymous":False,"created_at":"2025-01-16 22:00:00"},
    {"user_id":3,"nickname":"Charlie","emotion_label":"喜乐","emotion_key":"joy","note":"刚受洗一周，每天都充满感恩。","is_anonymous":False,"created_at":"2025-02-10 08:00:00"},
    {"user_id":None,"nickname":"匿名","emotion_label":"悲伤","emotion_key":"sadness","note":"失去了亲人，心里很痛。","is_anonymous":True,"created_at":"2025-02-14 20:00:00"},
    {"user_id":4,"nickname":"Diana","emotion_label":"迷茫","emotion_key":"confusion","note":"不知道未来在哪里，求主指引。","is_anonymous":False,"created_at":"2025-03-10 21:00:00"},
    {"user_id":1,"nickname":"Alice","emotion_label":"平静","emotion_key":"peace","note":"在祷告中找到了内心的安宁。","is_anonymous":False,"created_at":"2025-03-20 07:00:00"},
    {"user_id":5,"nickname":"Eve","emotion_label":"愤怒","emotion_key":"anger","note":"被人误解了，心里很不舒服。","is_anonymous":False,"created_at":"2025-04-05 18:00:00"},
    {"user_id":2,"nickname":"Bob","emotion_label":"希望","emotion_key":"hope","note":"收到了一个好消息，感谢主。","is_anonymous":False,"created_at":"2025-04-15 10:00:00"},
    {"user_id":3,"nickname":"Charlie","emotion_label":"谦卑","emotion_key":"humility","note":"认识到自己的不足，需要更多恩典。","is_anonymous":False,"created_at":"2025-04-25 20:00:00"},
    {"user_id":4,"nickname":"Diana","emotion_label":"信心","emotion_key":"faith","note":"虽然看不见前路，但选择信靠。","is_anonymous":False,"created_at":"2025-05-05 06:00:00"},
]))

# ---------- psychology engine data ----------

# emotion_logs (15 rows)
for i, uid in enumerate(uids[:15]):
    out.append(f"INSERT INTO emotion_logs (id, user_id, raw_text, emotion_tags, intensity, occurred_at, context_json, source) VALUES ({uid}, {(i%5)+1}, 'sample text {i}', '{{\"tag{i}\"}}', { (i%8)+2 }, '2025-03-{(i+1):02d} 18:00:00', '{{\"scene\": \"test\"}}', 'web');\n")

# personality_drivers (8 rows, FK to emotion_logs)
for i in range(8):
    out.append(f"INSERT INTO personality_drivers (user_id, log_id, surface_problem, deep_emotion, hidden_dynamics, driver_category, core_belief, created_at) VALUES ({(i%5)+1}, {uids[i]}, 'problem{i}', 'deep{i}', 'hidden{i}', 'perfectionism', 'belief{i}', '2025-03-{(i+1):02d} 19:00:00');\n")

# behavioral_triggers (6 rows)
for i in range(6):
    out.append(f"INSERT INTO behavioral_triggers (user_id, trigger_name, trigger_type, trigger_pattern, activating_event, frequency_count, created_at) VALUES ({(i%5)+1}, 'trigger{i}', 'situational', 'pattern{i}', 'event{i}', {i+1}, '2025-02-{(i+1):02d} 10:00:00');\n")

# cognitive_schemas (8 rows, user_id only)
for i in range(8):
    out.append(f"INSERT INTO cognitive_schemas (id, user_id, schema_name, distortion_type, core_belief, severity_score, created_at) VALUES ({uids[50+i]}, {(i%5)+1}, 'schema{i}', 'perfectionism', 'belief{i}', {(i%8)+2}, '2025-01-{(i+1):02d} 12:00:00');\n")

# behavioral_experiments (6 rows, FK to cognitive_schemas)
for i in range(6):
    out.append(f"INSERT INTO behavioral_experiments (id, user_id, schema_id, experiment_id, title, hypothesis_to_test, difficulty_level, status, created_at) VALUES ({uids[60+i]}, {(i%5)+1}, {uids[50+i]}, 'exp_2025_{i:03d}', 'experiment {i}', 'hypothesis{i}', {(i%5)+1}, 'pending', '2025-02-{(i+1):02d} 09:00:00');\n")

# psychological_states (10 rows, self-referencing previous_state_id)
for i in range(10):
    prev = f"{uids[70+i-1]}" if i > 0 else "NULL"
    out.append(f"INSERT INTO psychological_states (id, user_id, state_name, state_level, arousal_level, valence_score, focus_capacity, recommended_action, previous_state_id, captured_at) VALUES ({uids[70+i]}, {(i%5)+1}, 'regulated', {(i%5)}, {(i%8)+2}, {((i%10)-5)}, {(i%8)+2}, 'breathe', {prev}, '2025-03-{(i+1):02d} 08:00:00');\n")

# intervention_logs (8 rows, FK to psychological_states + behavioral_experiments)
for i in range(8):
    out.append(f"INSERT INTO intervention_logs (user_id, state_id, experiment_id, intervention_type, intervention_layer, prompt_text, technique_used, was_delivered, effectiveness_score, delivered_at) VALUES ({(i%5)+1}, {uids[70+i]}, {uids[60+(i%6)]}, 'micro_skill', {(i%5)}, 'prompt{i}', 'grounding', TRUE, {(i%8)+2}, '2025-03-{(i+1):02d} 09:00:00');\n")

# identity_narratives (6 rows)
for i in range(6):
    out.append(f"INSERT INTO identity_narratives (id, user_id, narrative_type, narrative_title, narrative_text, is_current, coherence_score, agency_score, redemption_score, created_at) VALUES ({uids[80+i]}, {(i%5)+1}, 'redemption', 'title{i}', 'text{i}', {str(i==0).upper()}, {(i%8)+2}, {(i%8)+2}, {(i%8)+2}, '2025-01-{(i+1):02d} 10:00:00');\n")

# self_concept_models (5 rows)
for i in range(5):
    out.append(f"INSERT INTO self_concept_models (user_id, self_efficacy, self_worth, self_stability, discrepancy_score, assessed_at) VALUES ({i+1}, {(i%8)+2}, {(i%8)+2}, {(i%8)+2}, {i%10}, '2025-02-{(i+1):02d} 11:00:00');\n")

# growth_trajectories (6 rows)
for i in range(6):
    out.append(f"INSERT INTO growth_trajectories (user_id, period_type, period_start, period_end, emotional_regulation_score, cognitive_flexibility_score, behavioral_activation_score, interpersonal_effectiveness_score, self_concept_clarity_score, calculated_at) VALUES ({(i%5)+1}, 'weekly', '2025-03-01', '2025-03-07', {(i*10)+20}, {(i*10)+25}, {(i*10)+30}, {(i*10)+35}, {(i*10)+40}, '2025-03-08 00:00:00');\n")

# pattern_recognitions (5 rows)
for i in range(5):
    out.append(f"INSERT INTO pattern_recognitions (user_id, pattern_type, pattern_name, pattern_description, predictability_score, created_at) VALUES ({(i%5)+1}, 'cyclical', 'pattern{i}', 'desc{i}', {(i%8)+2}, '2025-04-{(i+1):02d} 12:00:00');\n")

# memory_consolidations (6 rows)
for i in range(6):
    out.append(f"INSERT INTO memory_consolidations (user_id, memory_type, memory_title, memory_content, emotional_valence, emotional_arousal, memory_strength, original_event_at, consolidated_at) VALUES ({(i%5)+1}, 'episodic', 'memory{i}', 'content{i}', {((i%10)-5)}, {(i%8)+2}, {(i*10)+20}, '2024-06-{(i+1):02d} 10:00:00', '2025-01-{(i+1):02d} 10:00:00');\n")

# behavior_regulation_sessions (8 rows)
for i in range(8):
    out.append(f"INSERT INTO behavior_regulation_sessions (user_id, session_type, target_habit, motivation_level, ability_level, energy_level, behavioral_resistance, cognitive_load, selected_tier, was_executed, completion_percentage, started_at) VALUES ({(i%5)+1}, 'habit_task', 'habit{i}', {(i%8)+2}, {(i%8)+2}, {(i%5)+1}, {(i%8)+2}, {(i%8)+2}, 'Green', TRUE, {(i*10)+20}, '2025-03-{(i+1):02d} 07:00:00');\n")

# habit_state_machines (6 rows)
for i in range(6):
    out.append(f"INSERT INTO habit_state_machines (id, user_id, habit_name, habit_description, category, deterministic_anchor, token_green_yield, current_streak_days, total_executions, created_at) VALUES ({uids[100+i]}, {(i%5)+1}, 'habit{i}', 'desc{i}', 'health', 'anchor{i}', 10, {i}, {i*5}, '2025-01-{(i+1):02d} 08:00:00');\n")

# habit_execution_logs (10 rows, FK to habit_state_machines)
for i in range(10):
    out.append(f"INSERT INTO habit_execution_logs (user_id, habit_id, energy_level_at_execution, selected_tier, tokens_earned, was_completed, completion_percentage, mood_before, mood_after, executed_at) VALUES ({(i%5)+1}, {uids[100+(i%6)]}, {(i%5)+1}, 'Green', 10, TRUE, 100, {(i%8)+2}, {(i%8)+3}, '2025-03-{(i+1):02d} 08:00:00');\n")

# user_token_ledgers (5 rows)
for i in range(5):
    out.append(f"INSERT INTO user_token_ledgers (user_id, current_balance, lifetime_earned, lifetime_spent, green_tier_count, yellow_tier_count, red_tier_count, last_updated) VALUES ({i+1}, {(i+1)*50}, {(i+1)*80}, {(i+1)*30}, {i+5}, {i+2}, {i}, '2025-04-01 00:00:00');\n")

# token_transactions (8 rows, FK to habit_state_machines)
for i in range(8):
    out.append(f"INSERT INTO token_transactions (user_id, transaction_type, amount, balance_after, habit_id, description, created_at) VALUES ({(i%5)+1}, 'earn', 10, {(i+1)*50}, {uids[100+(i%6)]}, 'completed habit', '2025-03-{(i+1):02d} 08:05:00');\n")

# execution_paralysis_logs (8 rows)
for i in range(8):
    out.append(f"INSERT INTO execution_paralysis_logs (id, user_id, paralysis_type, detected_signals, raw_backlog_task, intervention_triggered, ignition_completed, detected_at) VALUES ({uids[110+i]}, {(i%5)+1}, 'procrastination', '{{}}', 'task{i}', TRUE, TRUE, '2025-03-{(i+1):02d} 14:00:00');\n")

# micro_scheduler_sessions (6 rows, FK to execution_paralysis_logs)
for i in range(6):
    out.append(f"INSERT INTO micro_scheduler_sessions (user_id, paralysis_log_id, session_status, original_task, total_steps, steps_completed, micro_momentum_score, started_at) VALUES ({(i%5)+1}, {uids[110+i]}, 'completed', 'big task {i}', 5, 5, {(i*10)+50}, '2025-03-{(i+1):02d} 14:05:00');\n")

# implementation_intentions (6 rows)
for i in range(6):
    out.append(f"INSERT INTO implementation_intentions (user_id, intention_name, if_trigger, then_action, usage_count, success_rate, is_active, created_at) VALUES ({(i%5)+1}, 'intention{i}', 'if {i}', 'then {i}', {i*3}, {(i*10)+50}, TRUE, '2025-02-{(i+1):02d} 10:00:00');\n")

# edge_intervention_analytics (5 rows)
for i in range(5):
    out.append(f"INSERT INTO edge_intervention_analytics (user_id, period_type, period_start, period_end, paralysis_events_count, interventions_triggered, ignition_completion_rate, task_restart_success_rate, calculated_at) VALUES ({(i%5)+1}, 'weekly', '2025-03-01', '2025-03-07', {i+2}, {i+1}, {(i*10)+60}, {(i*10)+50}, '2025-03-08 00:00:00');\n")

# identity_reinforcement_logs (8 rows, FK to emotion_logs + habit_state_machines + execution_paralysis_logs)
for i in range(8):
    out.append(f"INSERT INTO identity_reinforcement_logs (user_id, current_narrative, narrative_type, target_identity, identity_category, reinforcement_strength, user_resonance, migration_progress, related_emotion_log_id, related_habit_id, related_intervention_id, reinforced_at) VALUES ({(i%5)+1}, 'I am growing', 'redemption', 'I am resilient', 'growth_continuity', {(i%8)+2}, {(i%8)+2}, {(i*10)+20}, {uids[i]}, {uids[100+(i%6)]}, {uids[110+(i%8)]}, '2025-04-{(i+1):02d} 10:00:00');\n")

# personality_migrations (5 rows)
for i in range(5):
    out.append(f"INSERT INTO personality_migrations (user_id, migration_dimension, starting_identity, target_identity, current_stage, migration_status, progress_percentage, started_at) VALUES ({(i%5)+1}, 'resilience', 'I am fragile', 'I am strong', {i}, 'in_progress', {(i*10)+20}, '2025-01-{(i+1):02d} 09:00:00');\n")

# system_state_definitions (seed standard states)
out.append("""INSERT INTO system_state_definitions (state_name, state_code, arousal_range, valence_range, energy_level_range, trigger_conditions, behavior_strategy, task_intensity, social_interaction, prompt_tone, prompt_focus) VALUES
('STATE_NORMAL', 'NORMAL', '{"min": 3, "max": 6}', '{"min": 0, "max": 7}', '{"min": 3, "max": 5}', '[{"condition": "energy >= 3", "threshold": 3}]', '标准执行模式', 'full', 'encouraged', 'supportive', ARRAY['常规任务', '习惯维护', '成长追踪']),
('STATE_LOW_ENERGY', 'LOW_ENERGY', '{"min": 2, "max": 4}', '{"min": -3, "max": 3}', '{"min": 1, "max": 2}', '[{"condition": "energy <= 2", "threshold": 2}]', '低功耗模式 - 熔断保护', 'minimal', 'neutral', 'gentle', ARRAY['最小动作', '连续性保持', '休息许可']),
('STATE_ANXIETY_ESCAPE', 'ANXIETY_ESCAPE', '{"min": 6, "max": 9}', '{"min": -7, "max": -2}', '{"min": 1, "max": 3}', '[{"condition": "anxiety_peak", "threshold": 7}]', '焦虑应对模式 - grounding优先', 'reduced', 'minimized', 'gentle', ARRAY[' grounding', '呼吸调节', '小步启动']),
('STATE_SHAME_COLLAPSE', 'SHAME_COLLAPSE', '{"min": 4, "max": 8}', '{"min": -9, "max": -5}', '{"min": 1, "max": 2}', '[{"condition": "self_negation", "threshold": 8}]', '羞耻恢复模式 - 重建安全基地', 'paused', 'minimized', 'gentle', ARRAY['身份强化', '负面标签解构', '自我慈悲']),
('STATE_RECOVERY', 'RECOVERY', '{"min": 3, "max": 6}', '{"min": -2, "max": 4}', '{"min": 2, "max": 4}', '[{"condition": "post_crisis", "threshold": 5}]', '恢复期 - 渐进式重启', 'reduced', 'neutral', 'supportive', ARRAY['渐进任务', '成功经验', '动量积累']),
('STATE_FLOW', 'FLOW', '{"min": 5, "max": 8}', '{"min": 5, "max": 10}', '{"min": 4, "max": 5}', '[{"condition": "momentum > 80", "threshold": 80}]', '心流模式 - 最大化产出', 'full', 'neutral', 'neutral', ARRAY['深度工作', '保持节奏', '避免打断'])
ON CONFLICT (state_name) DO NOTHING;
""")

# user_system_states (5 rows)
for i in range(5):
    out.append(f"INSERT INTO user_system_states (user_id, current_state_code, previous_state_code, current_arousal, current_valence, current_energy_level, last_updated) VALUES ({i+1}, 'NORMAL', NULL, {(i%8)+2}, {((i%10)-5)}, {(i%5)+1}, '2025-05-01 00:00:00');\n")

# state_transition_logs (10 rows)
for i in range(10):
    out.append(f"INSERT INTO state_transition_logs (user_id, from_state_code, to_state_code, transition_trigger, arousal_at_transition, valence_at_transition, energy_at_transition, transitioned_at) VALUES ({(i%5)+1}, 'NORMAL', 'RECOVERY', 'trigger{i}', {(i%8)+2}, {((i%10)-5)}, {(i%5)+1}, '2025-03-{(i+1):02d} 10:00:00');\n")

# data_bus_events (10 rows)
for i in range(10):
    out.append(f"INSERT INTO data_bus_events (event_type, event_source, event_target, event_payload, priority, is_processed, created_at) VALUES ('telemetry', 'psychology', 'all', '{{\"user_id\": {(i%5)+1}, \"metric\": \"arousal\"}}', {(i%10)+1}, FALSE, '2025-04-{(i+1):02d} 12:00:00');\n")

# dynamic_load_configs (5 rows)
for i in range(5):
    out.append(f"INSERT INTO dynamic_load_configs (user_id, cognitive_load_score, emotional_load_score, behavioral_load_score, current_system_energy_level, updated_at) VALUES ({i+1}, {(i%8)+2}, {(i%8)+2}, {(i%8)+2}, {(i%5)+1}, '2025-05-01 00:00:00');\n")

a("""
COMMIT;
""")

with open(OU, 'w', encoding='utf-8') as f:
    f.write("\n".join(out))

print(f"Generated {OU} ({len(out)} lines)")
