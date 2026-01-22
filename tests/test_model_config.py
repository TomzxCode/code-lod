"""Tests for model configuration."""

import json


from code_lod.config import Config, get_model_for_scope
from code_lod.llm.description_generator.generator import Provider
from code_lod.models import ModelConfig, Scope


class TestModelConfig:
    """Tests for ModelConfig."""

    def test_create_empty_model_config(self) -> None:
        """Test creating an empty ModelConfig."""
        config = ModelConfig()
        assert config.default is None
        assert config.project is None
        assert config.package is None
        assert config.module is None
        assert config.class_ is None
        assert config.function is None

    def test_create_model_config_with_values(self) -> None:
        """Test creating ModelConfig with values."""
        config = ModelConfig(
            default="gpt-4o",
            project="gpt-4-turbo",
            function="gpt-3.5-turbo",
        )
        assert config.default == "gpt-4o"
        assert config.project == "gpt-4-turbo"
        assert config.function == "gpt-3.5-turbo"

    def test_get_model_for_scope_returns_specific_model(self) -> None:
        """Test get_model_for_scope returns scope-specific model."""
        config = ModelConfig(
            default="gpt-4o",
            function="gpt-3.5-turbo",
        )
        assert config.get_model_for_scope(Scope.FUNCTION) == "gpt-3.5-turbo"

    def test_get_model_for_scope_falls_back_to_default(self) -> None:
        """Test get_model_for_scope falls back to default."""
        config = ModelConfig(default="gpt-4o")
        assert config.get_model_for_scope(Scope.CLASS) == "gpt-4o"
        assert config.get_model_for_scope(Scope.FUNCTION) == "gpt-4o"

    def test_get_model_for_scope_returns_none_when_not_set(self) -> None:
        """Test get_model_for_scope returns None when nothing configured."""
        config = ModelConfig()
        assert config.get_model_for_scope(Scope.CLASS) is None
        assert config.get_model_for_scope(Scope.FUNCTION) is None

    def test_serialize_model_config(self) -> None:
        """Test serializing ModelConfig to JSON."""
        config = ModelConfig(
            default="gpt-4o",
            function="gpt-3.5-turbo",
        )
        data = config.model_dump()
        assert data["default"] == "gpt-4o"
        assert data["function"] == "gpt-3.5-turbo"
        assert data["class_"] is None  # Field is renamed


class TestConfigModelSettings:
    """Tests for Config.model_settings."""

    def test_config_with_empty_model_settings(self) -> None:
        """Test Config with empty model_settings."""
        config = Config()
        assert config.model_settings == {}

    def test_config_with_model_settings(self) -> None:
        """Test Config with model_settings."""
        config = Config(
            provider=Provider.OPENAI,
            model_settings={
                Provider.OPENAI: ModelConfig(default="gpt-4o"),
                Provider.ANTHROPIC: ModelConfig(default="claude-sonnet-4-5-20250929"),
            },
        )
        assert Provider.OPENAI in config.model_settings
        assert Provider.ANTHROPIC in config.model_settings
        assert config.model_settings[Provider.OPENAI].default == "gpt-4o"

    def test_serialize_config_with_model_settings(self, tmp_path) -> None:
        """Test serializing Config with model_settings to JSON."""

        config = Config(
            provider=Provider.OPENAI,
            model_settings={
                Provider.OPENAI: ModelConfig(
                    default="gpt-4o", function="gpt-3.5-turbo"
                ),
            },
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(config.model_dump_json(indent=2))

        # Verify JSON structure
        data = json.loads(config_file.read_text())
        assert data["provider"] == "openai"
        assert "openai" in data["model_settings"]
        assert data["model_settings"]["openai"]["default"] == "gpt-4o"
        assert data["model_settings"]["openai"]["function"] == "gpt-3.5-turbo"

    def test_deserialize_config_with_model_settings(self, tmp_path) -> None:
        """Test deserializing Config with model_settings from JSON."""

        config_data = {
            "provider": "openai",
            "languages": ["python"],
            "auto_update": False,
            "fail_on_stale": False,
            "model_settings": {
                "openai": {
                    "default": "gpt-4o",
                    "function": "gpt-3.5-turbo",
                }
            },
        }

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data, indent=2))

        config = Config(**json.loads(config_file.read_text()))
        assert config.provider == Provider.OPENAI
        assert Provider.OPENAI in config.model_settings
        assert config.model_settings[Provider.OPENAI].default == "gpt-4o"
        assert config.model_settings[Provider.OPENAI].function == "gpt-3.5-turbo"


class TestGetModelForScope:
    """Tests for get_model_for_scope function."""

    def test_returns_none_when_provider_not_configured(self) -> None:
        """Test returns None when provider not in model_settings."""
        config = Config()
        model = get_model_for_scope(config, Provider.OPENAI, Scope.FUNCTION)
        assert model is None

    def test_returns_none_when_scope_not_configured(self) -> None:
        """Test returns None when scope not configured."""
        config = Config(
            model_settings={
                Provider.OPENAI: ModelConfig(),
            }
        )
        model = get_model_for_scope(config, Provider.OPENAI, Scope.FUNCTION)
        assert model is None

    def test_returns_scope_specific_model(self) -> None:
        """Test returns scope-specific model."""
        config = Config(
            model_settings={
                Provider.OPENAI: ModelConfig(function="gpt-3.5-turbo"),
            }
        )
        model = get_model_for_scope(config, Provider.OPENAI, Scope.FUNCTION)
        assert model == "gpt-3.5-turbo"

    def test_returns_default_when_scope_not_set(self) -> None:
        """Test returns default model when scope-specific not set."""
        config = Config(
            model_settings={
                Provider.OPENAI: ModelConfig(default="gpt-4o"),
            }
        )
        model = get_model_for_scope(config, Provider.OPENAI, Scope.FUNCTION)
        assert model == "gpt-4o"

    def test_returns_default_when_scope_is_none(self) -> None:
        """Test returns default model when scope is None."""
        config = Config(
            model_settings={
                Provider.OPENAI: ModelConfig(default="gpt-4o"),
            }
        )
        model = get_model_for_scope(config, Provider.OPENAI, None)
        assert model == "gpt-4o"

    def test_scope_specific_overrides_default(self) -> None:
        """Test scope-specific model overrides default."""
        config = Config(
            model_settings={
                Provider.OPENAI: ModelConfig(
                    default="gpt-4o",
                    function="gpt-3.5-turbo",
                ),
            }
        )
        model = get_model_for_scope(config, Provider.OPENAI, Scope.FUNCTION)
        assert model == "gpt-3.5-turbo"

    def test_returns_none_for_other_provider(self) -> None:
        """Test returns None for different provider."""
        config = Config(
            model_settings={
                Provider.OPENAI: ModelConfig(default="gpt-4o"),
            }
        )
        model = get_model_for_scope(config, Provider.ANTHROPIC, Scope.FUNCTION)
        assert model is None
