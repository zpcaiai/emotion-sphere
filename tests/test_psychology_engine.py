"""
Tests for Psychology Engine
"""

import pytest
from backend.psychology_engine import (
    PersonalityCausalEngine,
    SchemaEngine,
    IdentityReinforcementEngine,
    CognitiveSchema,
    BehavioralExperiment
)


class TestPersonalityCausalEngine:
    """Test L0: Personality Causal Engine"""
    
    @pytest.fixture
    def engine(self):
        return PersonalityCausalEngine()
    
    def test_detect_driver_perfectionism(self, engine):
        """Test detection of perfectionism driver"""
        result = engine.detect_driver("I must be perfect, otherwise I'm a failure")
        assert result.driver_category == "perfectionism"
        assert result.intervention_priority >= 7
        assert result.core_belief is not None
    
    def test_detect_driver_impostor(self, engine):
        """Test detection of impostor syndrome"""
        result = engine.detect_driver("Everyone will find out I don't belong here")
        assert result.driver_category == "impostor"
        assert result.long_term_risk is not None
    
    def test_fallback_behavior(self, engine, monkeypatch):
        """Test fallback when LLM is unavailable"""
        # Mock LLM call to fail
        monkeypatch.setattr(
            'backend.psychology_engine.call_chat',
            lambda *args, **kwargs: exec('raise Exception("API Error")')
        )
        
        result = engine.detect_driver("Test input")
        # Should return fallback result
        assert result.driver_category is not None
        assert result.intervention_priority >= 5


class TestSchemaEngine:
    """Test L1: Schema Engine (CBT)"""
    
    @pytest.fixture
    def engine(self):
        return SchemaEngine()
    
    def test_abc_analysis_structure(self, engine):
        """Test ABC analysis produces correct structure"""
        text = "I failed the test, so I'm completely worthless"
        result = engine.analyze_abc(text)
        
        # Check belief hierarchy
        assert hasattr(result, 'belief_hierarchy')
        assert 'automatic_thought' in result.to_dict()['belief_hierarchy']
        assert 'intermediate_beliefs' in result.to_dict()['belief_hierarchy']
        assert 'core_beliefs' in result.to_dict()['belief_hierarchy']
    
    def test_cognitive_distortion_detection(self, engine):
        """Test detection of cognitive distortions"""
        text = "I always fail at everything I try"
        result = engine.analyze_abc(text)
        
        # Should detect overgeneralization
        assert result.distortion_type is not None
        assert result.severity_score >= 1
    
    def test_behavioral_experiment_generation(self, engine):
        """Test generation of behavioral experiments"""
        text = "I'm too anxious to speak in meetings"
        result = engine.analyze_abc(text)
        
        experiment = result.behavioral_experiment
        if experiment:
            assert experiment.title is not None
            assert experiment.counter_behavioral_action is not None


class TestIdentityReinforcementEngine:
    """Test L3/L4: Identity Reinforcement"""
    
    @pytest.fixture
    def engine(self):
        return IdentityReinforcementEngine()
    
    def test_narrative_type_classification(self, engine):
        """Test narrative type classification"""
        narrative = "I failed, but I learned from it and grew stronger"
        result = engine.analyze_identity(narrative)
        
        assert result.narrative_type in ['redemption', 'contamination', 'turning_point', 'stable']
    
    def test_reinforcement_language_generation(self, engine):
        """Test generation of identity reinforcement language"""
        narrative = "I'm not good enough for this role"
        result = engine.analyze_identity(narrative)
        
        assert result.reinforcement_language is not None
        assert len(result.reinforcement_language) > 0
    
    def test_migration_progress_calculation(self, engine):
        """Test migration progress calculation"""
        narrative = "I'm becoming a more resilient person"
        result = engine.analyze_identity(narrative)
        
        assert 0 <= result.migration_progress <= 100
        assert result.target_identity is not None


class TestCognitiveSchema:
    """Test CognitiveSchema dataclass"""
    
    def test_schema_creation(self):
        """Test creation of cognitive schema"""
        schema = CognitiveSchema(
            schema_id="test_001",
            schema_name="Test Schema",
            automatic_thought="I will fail",
            core_belief_self="I am incompetent",
            consequence_emotional="Anxiety",
            severity_score=8
        )
        
        assert schema.schema_id == "test_001"
        assert schema.severity_score == 8
    
    def test_schema_to_dict(self):
        """Test conversion to dictionary"""
        schema = CognitiveSchema(
            automatic_thought="Test thought",
            intermediate_belief_rules="I must succeed"
        )
        
        data = schema.to_dict()
        assert 'belief_hierarchy' in data
        assert data['belief_hierarchy']['intermediate_beliefs']['rules'] == "I must succeed"


class TestBehavioralExperiment:
    """Test BehavioralExperiment dataclass"""
    
    def test_experiment_creation(self):
        """Test creation of behavioral experiment"""
        exp = BehavioralExperiment(
            experiment_id="exp_001",
            title="Test Experiment",
            hypothesis_to_test="I will be rejected",
            counter_behavioral_action="Speak up once in the meeting"
        )
        
        assert exp.experiment_id == "exp_001"
        assert exp.difficulty_level == 3  # default
    
    def test_experiment_to_dict(self):
        """Test conversion to dictionary"""
        exp = BehavioralExperiment(
            title="Anxiety Test",
            binary_telemetry_metric="Did I speak up? Yes/No"
        )
        
        data = exp.to_dict()
        assert 'title' in data
        assert 'binary_telemetry_metric' in data


# Integration tests (marked as slow)
@pytest.mark.slow
@pytest.mark.integration
class TestPsychologyEngineIntegration:
    """Integration tests requiring LLM"""
    
    @pytest.fixture
    def full_engine(self):
        from backend.psychology_engine import PsychologyEngine
        return PsychologyEngine()
    
    def test_full_analysis_pipeline(self, full_engine):
        """Test full L0-L4 analysis pipeline"""
        text = "I'm feeling overwhelmed and can't focus on my work"
        
        result = full_engine.analyze(text)
        
        # Should have L0 analysis
        assert 'l0' in result or hasattr(result, 'l0')
        # Should have L1 analysis
        assert 'l1' in result or hasattr(result, 'l1')
        # Should have L2 recommendation
        assert 'l2' in result or hasattr(result, 'l2')
