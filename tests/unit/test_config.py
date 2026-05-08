"""Tests for Config class"""

import os
import pytest
from unittest.mock import patch

from kagent.core.config import Config, ConfigError, load_config


class TestConfigDefaults:
    """Test default values"""

    def test_default_provider(self):
        config = Config()
        assert config.default_provider == "openai"

    def test_default_model(self):
        config = Config()
        assert config.default_model == "gpt-4o"

    def test_default_temperature(self):
        config = Config()
        assert config.temperature == 0.0

    def test_default_debug_false(self):
        config = Config()
        assert config.debug is False

    def test_default_log_level(self):
        config = Config()
        assert config.log_level == "INFO"

    def test_default_max_history_length(self):
        config = Config()
        assert config.max_history_length == 50

    def test_default_max_steps(self):
        config = Config()
        assert config.max_steps == 5

    def test_default_trace_enabled(self):
        config = Config()
        assert config.trace_enabled is True

    def test_default_trace_export(self):
        config = Config()
        assert config.trace_export == "console"


class TestConfigFromEnv:
    """Test Config.from_env()"""

    def test_from_env_with_defaults(self):
        """Test loading from env with no vars set uses defaults"""
        env = {"LLM_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()
            assert config.default_provider == "openai"
            assert config.default_model == "gpt-4o"

    def test_from_env_custom_values(self):
        """Test loading custom values from env"""
        env_vars = {
            "LLM_PROVIDER": "ollama",
            "LLM_MODEL_ID": "llama3",
            "LLM_TEMPERATURE": "0.7",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "MAX_HISTORY_LENGTH": "100",
            "MAX_STEPS": "10",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
            assert config.default_provider == "ollama"
            assert config.default_model == "llama3"
            assert config.temperature == 0.7
            assert config.debug is True
            assert config.log_level == "DEBUG"
            assert config.max_history_length == 100
            assert config.max_steps == 10

    def test_from_env_returns_config_instance(self):
        """Test from_env returns Config instance"""
        env = {"LLM_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()
            assert isinstance(config, Config)

    def test_from_env_reads_api_key(self):
        """Test from_env reads API key into model field"""
        env = {"LLM_API_KEY": "sk-test-123"}
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()
            assert config.api_key == "sk-test-123"

    def test_from_env_reads_base_url(self):
        """Test from_env reads base URL"""
        env = {
            "LLM_API_KEY": "sk-test",
            "LLM_BASE_URL": "https://api.example.com/v1"
        }
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()
            assert config.base_url == "https://api.example.com/v1"

    def test_from_env_reads_timeout(self):
        env = {"LLM_API_KEY": "sk-test", "LLM_TIMEOUT": "123"}
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()
            assert config.timeout == 123

    def test_from_env_malformed_temperature(self):
        """Test malformed LLM_TEMPERATURE raises ValueError"""
        env = {"LLM_TEMPERATURE": "abc", "LLM_API_KEY": "sk-test"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError):
                Config.from_env()

    def test_from_env_malformed_max_steps(self):
        """Test malformed MAX_STEPS raises ValueError"""
        env = {"MAX_STEPS": "xyz", "LLM_API_KEY": "sk-test"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError):
                Config.from_env()


class TestConfigValidation:
    """Test Config.validate_config()"""

    def test_missing_api_key_raises_error(self):
        """Test missing api_key for non-ollama provider raises ConfigError"""
        config = Config(default_provider="openai", api_key=None)
        with pytest.raises(ConfigError, match="LLM_API_KEY is required"):
            config.validate_config()

    def test_empty_api_key_raises_error(self):
        """Test empty string api_key raises ConfigError"""
        config = Config(default_provider="openai", api_key="")
        with pytest.raises(ConfigError, match="LLM_API_KEY is required"):
            config.validate_config()

    def test_ollama_no_api_key_required(self):
        """Test ollama provider doesn't require API key"""
        config = Config(default_provider="ollama", api_key=None)
        # Should not raise
        config.validate_config()

    def test_vllm_no_api_key_required(self):
        """Test vllm provider doesn't require API key"""
        config = Config(default_provider="vllm", api_key=None)
        # Should not raise
        config.validate_config()

    def test_valid_api_key_passes(self):
        """Test valid api_key passes validation"""
        config = Config(default_provider="openai", api_key="sk-test-123")
        # Should not raise
        config.validate_config()

    def test_from_env_with_openai_key(self):
        """Test from_env reads OPENAI_API_KEY as fallback"""
        env = {"OPENAI_API_KEY": "sk-fallback"}
        with patch.dict(os.environ, env, clear=True):
            config = Config.from_env()
            assert config.api_key == "sk-fallback"


class TestConfigModelDump:
    """Test Config.model_dump()"""

    def test_model_dump_returns_dict(self):
        config = Config()
        dumped = config.model_dump()
        assert isinstance(dumped, dict)

    def test_model_dump_contains_all_fields(self):
        config = Config()
        dumped = config.model_dump()
        expected_fields = [
            "default_provider", "default_model", "api_key", "base_url",
            "timeout", "temperature", "max_tokens", "debug", "log_level",
            "max_history_length", "max_steps", "trace_enabled", "trace_export"
        ]
        for field in expected_fields:
            assert field in dumped

    def test_model_dump_values_match(self):
        config = Config(default_provider="ollama", debug=True)
        dumped = config.model_dump()
        assert dumped["default_provider"] == "ollama"
        assert dumped["debug"] is True


class TestLoadConfig:
    """Test load_config convenience function"""

    def test_load_config_returns_config(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=False):
            config = load_config()
            assert isinstance(config, Config)
