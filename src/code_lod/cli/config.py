"""Config command for code-lod."""

import typer

from code_lod.config import get_paths, load_config, save_config
from code_lod.llm.description_generator.generator import Provider
from code_lod.models import ModelConfig, Scope


def config(
    action: str = typer.Argument(
        ...,
        help="Action to perform: get, set, list, or set-model",
    ),
    key: str = typer.Argument(
        None,
        help="Configuration key (e.g., 'provider', 'auto_update', or for models: 'anthropic', 'openai')",
    ),
    value: str = typer.Argument(
        None,
        help="Configuration value",
    ),
) -> None:
    """Get or set configuration values.

    Actions:
      - get <key>: Get a configuration value
      - set <key> <value>: Set a configuration value
      - list: List all configuration
      - set-model <provider> <scope> <model>: Set model for provider and scope

    Examples:
      code-lod config get provider
      code-lod config set provider openai
      code-lod config list
      code-lod config set-model anthropic function claude-sonnet-4-5-20250929
      code-lod config set-model openai default gpt-4o
    """
    from code_lod.cli import app

    log = app.log  # type: ignore[attr-defined]

    try:
        paths = get_paths()
    except FileNotFoundError:
        typer.echo(
            "Error: code-lod not initialized. Run 'code-lod init' first.", err=True
        )
        raise typer.Exit(1)

    config_obj = load_config(paths)

    if action == "list":
        _list_config(config_obj)
    elif action == "get":
        if not key:
            typer.echo("Error: 'get' requires a key argument", err=True)
            raise typer.Exit(1)
        _get_config(config_obj, key)
    elif action == "set":
        if not key or not value:
            typer.echo("Error: 'set' requires key and value arguments", err=True)
            raise typer.Exit(1)
        _set_config(config_obj, key, value, paths, log)
    elif action == "set-model":
        # set-model <provider> <scope|default> <model>
        if not key or not value:
            typer.echo(
                "Error: 'set-model' requires provider and scope arguments",
                err=True,
            )
            raise typer.Exit(1)
        # For set-model, we need the model name as a third arg
        # But typer's arg handling makes this tricky, so we'll use a different approach
        typer.echo(
            "Error: Please use: code-lod config set-model <provider> <scope> <model>",
            err=True,
        )
        raise typer.Exit(1)
    else:
        typer.echo(f"Error: Unknown action '{action}'", err=True)
        typer.echo("Valid actions: get, set, list", err=True)
        raise typer.Exit(1)


def config_set_model(
    provider: str = typer.Argument(..., help="Provider (openai, anthropic, mock)"),
    scope: str = typer.Argument(
        ...,
        help="Scope (default, project, package, module, class, function)",
    ),
    model: str = typer.Argument(..., help="Model name"),
) -> None:
    """Set model for a specific provider and scope.

    Examples:
      code-lod config-set-model anthropic function claude-sonnet-4-5-20250929
      code-lod config-set-model openai default gpt-4o
    """
    from code_lod.cli import app

    log = app.log  # type: ignore[attr-defined]

    try:
        paths = get_paths()
    except FileNotFoundError:
        typer.echo(
            "Error: code-lod not initialized. Run 'code-lod init' first.", err=True
        )
        raise typer.Exit(1)

    # Validate provider
    try:
        provider_enum = Provider(provider.lower())
    except ValueError:
        typer.echo(
            f"Error: Invalid provider '{provider}'. Valid options: {[p.value for p in Provider]}",
            err=True,
        )
        raise typer.Exit(1)

    # Validate scope
    if scope.lower() == "default":
        scope_key = None  # Will use default field
    else:
        try:
            scope_enum = Scope(scope.lower())
            scope_key = scope_enum
        except ValueError:
            typer.echo(
                f"Error: Invalid scope '{scope}'. Valid options: default, project, package, module, class, function",
                err=True,
            )
            raise typer.Exit(1)

    config_obj = load_config(paths)

    # Get or create model config for this provider
    if provider_enum not in config_obj.model_settings:
        config_obj.model_settings[provider_enum] = ModelConfig()

    model_config = config_obj.model_settings[provider_enum]

    # Set the model for the scope
    if scope_key is None:
        model_config.default = model
        log.info("model_set", provider=provider, scope="default", model=model)
        typer.echo(f"Set default model for {provider} to '{model}'")
    else:
        if scope_key == Scope.CLASS:
            model_config.class_ = model
        elif scope_key == Scope.FUNCTION:
            model_config.function = model
        elif scope_key == Scope.MODULE:
            model_config.module = model
        elif scope_key == Scope.PACKAGE:
            model_config.package = model
        elif scope_key == Scope.PROJECT:
            model_config.project = model
        log.info("model_set", provider=provider, scope=scope_key.value, model=model)
        typer.echo(f"Set {scope_key.value} model for {provider} to '{model}'")

    save_config(config_obj, paths)


def _list_config(config_obj) -> None:
    """List all configuration."""
    typer.echo("Configuration:")
    typer.echo(f"  languages: {config_obj.languages}")
    typer.echo(f"  auto_update: {config_obj.auto_update}")
    typer.echo(f"  fail_on_stale: {config_obj.fail_on_stale}")
    typer.echo(f"  provider: {config_obj.provider.value}")
    typer.echo("\nModel settings:")
    if not config_obj.model_settings:
        typer.echo("  (none configured)")
    for provider, model_config in config_obj.model_settings.items():
        typer.echo(f"  {provider.value}:")
        if model_config.default:
            typer.echo(f"    default: {model_config.default}")
        if model_config.project:
            typer.echo(f"    project: {model_config.project}")
        if model_config.package:
            typer.echo(f"    package: {model_config.package}")
        if model_config.module:
            typer.echo(f"    module: {model_config.module}")
        if model_config.class_:
            typer.echo(f"    class: {model_config.class_}")
        if model_config.function:
            typer.echo(f"    function: {model_config.function}")


def _get_config(config_obj, key: str) -> None:
    """Get a configuration value."""
    if key == "provider":
        typer.echo(config_obj.provider.value)
    elif key == "languages":
        typer.echo(", ".join(config_obj.languages))
    elif key == "auto_update":
        typer.echo(str(config_obj.auto_update).lower())
    elif key == "fail_on_stale":
        typer.echo(str(config_obj.fail_on_stale).lower())
    elif key in ["model_settings", "models"]:
        for provider, model_config in config_obj.model_settings.items():
            typer.echo(f"{provider.value}:")
            if model_config.default:
                typer.echo(f"  default: {model_config.default}")
            if model_config.project:
                typer.echo(f"  project: {model_config.project}")
            if model_config.package:
                typer.echo(f"  package: {model_config.package}")
            if model_config.module:
                typer.echo(f"  module: {model_config.module}")
            if model_config.class_:
                typer.echo(f"  class: {model_config.class_}")
            if model_config.function:
                typer.echo(f"  function: {model_config.function}")
    else:
        typer.echo(f"Error: Unknown key '{key}'", err=True)
        typer.echo(
            "Valid keys: provider, languages, auto_update, fail_on_stale, models",
            err=True,
        )
        raise typer.Exit(1)


def _set_config(config_obj, key: str, value: str, paths, log) -> None:
    """Set a configuration value."""
    if key == "provider":
        try:
            config_obj.provider = Provider(value.lower())
            log.info("config_set", key=key, value=value)
        except ValueError:
            typer.echo(
                f"Error: Invalid provider '{value}'. Valid options: {[p.value for p in Provider]}",
                err=True,
            )
            raise typer.Exit(1)
    elif key == "languages":
        config_obj.languages = [lang.strip() for lang in value.split(",")]
        log.info("config_set", key=key, value=config_obj.languages)
    elif key == "auto_update":
        config_obj.auto_update = value.lower() in ["true", "1", "yes", "on"]
        log.info("config_set", key=key, value=config_obj.auto_update)
    elif key == "fail_on_stale":
        config_obj.fail_on_stale = value.lower() in ["true", "1", "yes", "on"]
        log.info("config_set", key=key, value=config_obj.fail_on_stale)
    else:
        typer.echo(f"Error: Unknown key '{key}'", err=True)
        typer.echo(
            "Valid keys: provider, languages, auto_update, fail_on_stale", err=True
        )
        typer.echo(
            "For model settings, use: code-lod config-set-model <provider> <scope> <model>",
            err=True,
        )
        raise typer.Exit(1)

    save_config(config_obj, paths)
    typer.echo(f"Set {key} to '{value}'")
