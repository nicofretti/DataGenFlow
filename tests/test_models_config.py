"""
Tests for configuration and models
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from config import Settings, settings
from models import (
    Record, RecordStatus, RecordUpdate, SeedInput, 
    GenerationConfig
)


class TestSettings:
    """Test configuration settings"""
    
    def test_settings_defaults(self):
        """Test default configuration values"""
        s = Settings()
        # settings should have values (either from .env or defaults)
        assert s.LLM_ENDPOINT is not None
        assert isinstance(s.LLM_API_KEY, str)
        assert s.LLM_MODEL is not None
        assert s.DATABASE_PATH is not None
        assert s.HOST is not None
        assert isinstance(s.PORT, int)
    
    def test_settings_structure(self):
        """Test settings object structure"""
        s = Settings()
        # verify all required attributes exist
        assert hasattr(s, 'LLM_ENDPOINT')
        assert hasattr(s, 'LLM_API_KEY')
        assert hasattr(s, 'LLM_MODEL')
        assert hasattr(s, 'DATABASE_PATH')
        assert hasattr(s, 'HOST')
        assert hasattr(s, 'PORT')
        assert hasattr(s, 'ensure_data_dir')
    
    def test_ensure_data_dir_creates_directory(self):
        """Test that ensure_data_dir creates the data directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db_path = os.path.join(temp_dir, "subdir", "test.db")
            
            with patch.object(Settings, 'DATABASE_PATH', test_db_path):
                Settings.ensure_data_dir()
                
                # check that parent directory was created
                assert os.path.exists(os.path.dirname(test_db_path))
    
    def test_ensure_data_dir_handles_existing_directory(self):
        """Test that ensure_data_dir works with existing directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_db_path = os.path.join(temp_dir, "test.db")
            
            with patch.object(Settings, 'DATABASE_PATH', test_db_path):
                # call twice - should not fail
                Settings.ensure_data_dir()
                Settings.ensure_data_dir()
                
                assert os.path.exists(temp_dir)
    
    def test_global_settings_instance(self):
        """Test that global settings instance exists"""
        assert settings is not None
        assert isinstance(settings, Settings)


class TestRecordModel:
    """Test Record model validation and behavior"""
    
    def test_record_creation_minimal(self):
        """Test creating a record with minimal fields"""
        record = Record(
            system="test system",
            user="test user", 
            assistant="test assistant"
        )
        
        assert record.system == "test system"
        assert record.user == "test user"
        assert record.assistant == "test assistant"
        assert record.id is None
        assert record.metadata == {}
        assert record.status == RecordStatus.PENDING
        assert record.created_at is None
        assert record.updated_at is None
    
    def test_record_creation_full(self):
        """Test creating a record with all fields"""
        from datetime import datetime
        
        now = datetime.now()
        metadata = {"test": "value", "num": 42}
        
        record = Record(
            id=1,
            system="system",
            user="user",
            assistant="assistant",
            metadata=metadata,
            status=RecordStatus.ACCEPTED,
            created_at=now,
            updated_at=now
        )
        
        assert record.id == 1
        assert record.metadata == metadata
        assert record.status == RecordStatus.ACCEPTED
        assert record.created_at == now
        assert record.updated_at == now
    
    def test_record_status_enum(self):
        """Test RecordStatus enum values"""
        assert RecordStatus.PENDING == "pending"
        assert RecordStatus.ACCEPTED == "accepted"
        assert RecordStatus.REJECTED == "rejected"
        assert RecordStatus.EDITED == "edited"
        
        # test all enum values work in record
        for status in RecordStatus:
            record = Record(
                system="test", user="test", assistant="test",
                status=status
            )
            assert record.status == status
    
    def test_record_metadata_types(self):
        """Test that metadata accepts various types"""
        complex_metadata = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        record = Record(
            system="test", user="test", assistant="test",
            metadata=complex_metadata
        )
        
        assert record.metadata == complex_metadata


class TestRecordUpdateModel:
    """Test RecordUpdate model"""
    
    def test_record_update_all_none(self):
        """Test creating empty update"""
        update = RecordUpdate()
        
        assert update.system is None
        assert update.user is None
        assert update.assistant is None
        assert update.status is None
        assert update.metadata is None
    
    def test_record_update_partial(self):
        """Test partial update"""
        update = RecordUpdate(
            system="new system",
            status=RecordStatus.ACCEPTED
        )
        
        assert update.system == "new system"
        assert update.status == RecordStatus.ACCEPTED
        assert update.user is None
        assert update.assistant is None
        assert update.metadata is None
    
    def test_record_update_metadata(self):
        """Test updating metadata"""
        new_metadata = {"updated": True, "count": 1}
        update = RecordUpdate(metadata=new_metadata)
        
        assert update.metadata == new_metadata


class TestSeedInputModel:
    """Test SeedInput model"""
    
    def test_seed_input_creation(self):
        """Test creating a seed input"""
        seed = SeedInput(
            system="You are {role}",
            user="Explain {topic}",
            metadata={"role": "teacher", "topic": "physics", "num_samples": 5}
        )
        
        assert seed.system == "You are {role}"
        assert seed.user == "Explain {topic}"
        assert seed.metadata["role"] == "teacher"
        assert seed.metadata["topic"] == "physics"
        assert seed.metadata["num_samples"] == 5
    
    def test_seed_input_validation(self):
        """Test seed input validation"""
        # test with missing required fields
        with pytest.raises(Exception):  # pydantic validation error
            SeedInput(system="test")  # missing user and metadata
        
        with pytest.raises(Exception):
            SeedInput(user="test")  # missing system and metadata
    
    def test_seed_input_template_placeholders(self):
        """Test that seed input can contain template placeholders"""
        seed = SeedInput(
            system="You are a {profession} who specializes in {specialty}",
            user="Explain {concept} to a {audience}",
            metadata={
                "profession": "teacher",
                "specialty": "mathematics", 
                "concept": "calculus",
                "audience": "beginner",
                "num_samples": 3
            }
        )
        
        assert "{profession}" in seed.system
        assert "{specialty}" in seed.system
        assert "{concept}" in seed.user
        assert "{audience}" in seed.user


class TestGenerationConfigModel:
    """Test GenerationConfig model"""
    
    def test_generation_config_defaults(self):
        """Test default generation config"""
        config = GenerationConfig()
        
        assert config.model is None
        assert config.endpoint is None
        assert config.temperature == 0.7
        assert config.max_tokens is None
    
    def test_generation_config_custom(self):
        """Test custom generation config"""
        config = GenerationConfig(
            model="custom-model",
            endpoint="http://custom:8080",
            temperature=0.9,
            max_tokens=1000
        )
        
        assert config.model == "custom-model"
        assert config.endpoint == "http://custom:8080"
        assert config.temperature == 0.9
        assert config.max_tokens == 1000
    
    def test_generation_config_validation(self):
        """Test generation config validation"""
        # test temperature bounds
        with pytest.raises(Exception):  # pydantic validation error
            GenerationConfig(temperature=-1.0)
        
        with pytest.raises(Exception):
            GenerationConfig(temperature=3.0)
        
        # test max_tokens validation
        with pytest.raises(Exception):
            GenerationConfig(max_tokens=0)
        
        with pytest.raises(Exception):
            GenerationConfig(max_tokens=-1)
        
        # test valid edge cases
        config1 = GenerationConfig(temperature=0.0)
        assert config1.temperature == 0.0
        
        config2 = GenerationConfig(temperature=2.0)
        assert config2.temperature == 2.0
        
        config3 = GenerationConfig(max_tokens=1)
        assert config3.max_tokens == 1


class TestModelInteractions:
    """Test how models work together"""
    
    def test_record_from_seed_input(self):
        """Test creating a record from seed input (conceptually)"""
        seed = SeedInput(
            system="You are {role}",
            user="Explain {topic}",
            metadata={"role": "teacher", "topic": "AI", "num_samples": 1}
        )
        
        # simulate what the generator would do
        filled_system = seed.system.format(**seed.metadata)
        filled_user = seed.user.format(**seed.metadata)
        
        record = Record(
            system=filled_system,
            user=filled_user,
            assistant="AI is a field of computer science...",
            metadata=seed.metadata
        )
        
        assert record.system == "You are teacher"
        assert record.user == "Explain AI"
        assert record.metadata == seed.metadata
    
    def test_record_update_preserves_unchanged(self):
        """Test that record updates preserve unchanged fields"""
        original = Record(
            system="original system",
            user="original user",
            assistant="original assistant",
            status=RecordStatus.PENDING
        )
        
        update = RecordUpdate(
            assistant="updated assistant",
            status=RecordStatus.ACCEPTED
        )
        
        # simulate what storage.update_record would do
        updated_fields = {}
        if update.system is not None:
            updated_fields["system"] = update.system
        if update.user is not None:
            updated_fields["user"] = update.user
        if update.assistant is not None:
            updated_fields["assistant"] = update.assistant
        if update.status is not None:
            updated_fields["status"] = update.status
        if update.metadata is not None:
            updated_fields["metadata"] = update.metadata
        
        # verify only specified fields would be updated
        assert "assistant" in updated_fields
        assert "status" in updated_fields
        assert "system" not in updated_fields
        assert "user" not in updated_fields
        assert "metadata" not in updated_fields