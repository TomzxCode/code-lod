"""Generate command for code-lod."""

from pathlib import Path

import typer

from code_lod.config import get_model_for_scope, get_paths, load_config
from code_lod.models import Scope
from code_lod.parsers.tree_sitter_parser import get_parser
from code_lod.staleness import StalenessTracker


def generate(
    path: Path = typer.Argument(Path.cwd(), help="Path to generate descriptions for"),
    scope: Scope = typer.Option(
        None, "--scope", "-s", help="Hierarchical level to generate"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Regenerate even if fresh"),
) -> None:
    """Generate descriptions for code entities."""
    from code_lod.cli import app

    log = app.log  # type: ignore[attr-defined]

    try:
        paths = get_paths(path)
    except FileNotFoundError:
        typer.error("code-lod not initialized. Run 'code-lod init' first.")
        raise typer.Exit(1)

    typer.echo(f"Generating descriptions for {path}...")

    # Load configuration
    config = load_config(paths)
    log.info("config_loaded", provider=config.provider)

    # For now, simple implementation for Python files
    python_files = list(path.rglob("*.py")) if path.is_dir() else [path]
    log.info("files_found", count=len(python_files))

    tracker = StalenessTracker(paths.root_dir)
    from code_lod.llm.description_generator.generator import get_generator

    generator = get_generator(config.provider)

    total_generated = 0
    total_skipped = 0

    for file_path in python_files:
        if not file_path.is_file():
            continue

        # Resolve to absolute path for relative_to calculation
        file_path = file_path.resolve()

        # Detect language and get parser
        from code_lod.parsers.tree_sitter_parser import detect_language

        lang = detect_language(file_path)
        if not lang:
            log.debug("skipping_file", path=str(file_path), reason="unknown language")
            continue

        log.info("processing_file", path=str(file_path), language=lang)

        parser = get_parser(lang)
        entities = parser.parse_file(file_path)
        log.info("entities_found", count=len(entities))

        # Generate descriptions and write to .lod files
        from code_lod.lod_file.writer import write_lod_file

        lod_path = paths.lod_dir / file_path.relative_to(paths.root_dir)
        lod_path = lod_path.with_suffix(lod_path.suffix + ".lod")

        descriptions: list[tuple[str, str]] = []
        module_description = None
        file_generated = 0
        file_skipped = 0

        for entity in entities:
            # Check if we need to regenerate
            if not force:
                record = tracker.hash_index.get(entity.ast_hash)
                if record and not record.stale:
                    total_skipped += 1
                    file_skipped += 1
                    log.debug(
                        "skipping_entity",
                        name=entity.name,
                        scope=entity.scope.value,
                        reason="fresh_description_exists",
                    )
                    if entity.scope == Scope.MODULE:
                        module_description = record.description
                    else:
                        descriptions.append((entity.name, record.description))
                    continue

            # Generate new description
            # Resolve model for this entity's scope
            model = get_model_for_scope(config, config.provider, entity.scope)
            log.info(
                "generating",
                name=entity.name,
                scope=entity.scope.value,
                model=model or "default",
            )
            description = generator.generate(entity, model=model)
            total_generated += 1
            file_generated += 1

            # Store in database
            tracker.set_description(entity.ast_hash, description, stale=False)

            if entity.scope == Scope.MODULE:
                module_description = description
            else:
                descriptions.append((entity.name, description))

        log.info(
            "file_complete",
            path=str(file_path),
            generated=file_generated,
            skipped=file_skipped,
        )

        # Write .lod file
        if descriptions or module_description:
            # Filter out module entity since it's handled separately
            non_module_entities = [e for e in entities if e.scope != Scope.MODULE]
            entity_desc_pairs = [
                (e, d)
                for e, d in zip(non_module_entities, [d for _, d in descriptions])
            ]
            write_lod_file(
                lod_path,
                entity_desc_pairs,
                lang,
                module_description,
            )

    typer.echo(f"Generated {total_generated} descriptions")
    typer.echo(f"Skipped {total_skipped} existing descriptions")
