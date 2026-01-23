"""Pipeline for parallel description generation."""

import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Queue

from code_lod.config import Paths, get_model_for_scope
from code_lod.models import ParsedEntity, Scope
from code_lod.parsers.tree_sitter_parser import detect_language, get_parser
from code_lod.staleness import StalenessTracker


@dataclass
class ParsedEntityWithFile:
    """An entity with its file context for pipeline processing."""

    entity: ParsedEntity
    file_path: Path
    language: str
    model: str | None
    needs_generation: bool


@dataclass
class GenerationResult:
    """Result of generating a description for an entity."""

    entity: ParsedEntity
    file_path: Path
    language: str
    description: str | None  # None if skipped/stale
    was_generated: bool


class ProgressCounter:
    """Thread-safe progress counter with live display."""

    def __init__(self, total_files: int, max_workers: int) -> None:
        """Initialize the progress counter.

        Args:
            total_files: Total number of files to process.
            max_workers: Maximum number of parallel workers.
        """
        self._lock = threading.Lock()
        self._files_scanned = 0
        self._total_files = total_files
        self._entities_discovered = 0
        self._entities_to_generate = 0
        self._descriptions_generated = 0
        self._lod_files_written = 0
        self._active_scanners = 0
        self._active_llm_workers = 0
        self._max_workers = max_workers
        self._last_display = ""

    def increment_files_scanned(self) -> None:
        """Increment the files scanned counter."""
        with self._lock:
            self._files_scanned += 1
            self._display()

    def increment_entities_discovered(self, count: int = 1) -> None:
        """Increment the entities discovered counter.

        Args:
            count: Number of entities to add.
        """
        with self._lock:
            self._entities_discovered += count
            self._display()

    def increment_entities_to_generate(self, count: int = 1) -> None:
        """Increment the entities to generate counter.

        Args:
            count: Number of entities to add.
        """
        with self._lock:
            self._entities_to_generate += count
            self._display()

    def increment_descriptions_generated(self) -> None:
        """Increment the descriptions generated counter."""
        with self._lock:
            self._descriptions_generated += 1
            self._display()

    def increment_lod_files_written(self) -> None:
        """Increment the LOD files written counter."""
        with self._lock:
            self._lod_files_written += 1
            self._display()

    def set_active_scanners(self, count: int) -> None:
        """Set the number of active file scanners.

        Args:
            count: Number of active scanners.
        """
        with self._lock:
            self._active_scanners = count
            self._display()

    def set_active_llm_workers(self, count: int) -> None:
        """Set the number of active LLM workers.

        Args:
            count: Number of active LLM workers.
        """
        with self._lock:
            self._active_llm_workers = count
            self._display()

    def _display(self) -> None:
        """Display the current progress."""
        display = (
            f"Files scanned {self._files_scanned}/{self._total_files} [{self._active_scanners}/{self._max_workers}] -> "
            f"Entities discovered {self._entities_discovered} -> "
            f"Descriptions generated {self._descriptions_generated}/{self._entities_to_generate} [{self._active_llm_workers}/{self._max_workers}] -> "
            f"LOD files written {self._lod_files_written}"
        )
        if display != self._last_display:
            # Use \r to overwrite the line
            print(f"\r{display}", end="", file=sys.stderr, flush=True)
            self._last_display = display

    def finalize_display(self) -> None:
        """Finalize the display with a newline."""
        if self._last_display:
            print(file=sys.stderr, flush=True)


class FileCompletionTracker:
    """Track completion of entities per file for LOD writing."""

    def __init__(self) -> None:
        """Initialize the tracker."""
        self._lock = threading.Lock()
        self._pending_per_file: dict[Path, int] = defaultdict(int)
        self._results_per_file: dict[Path, list[GenerationResult]] = defaultdict(list)
        self._module_descriptions: dict[Path, str | None] = {}

    def register_file(self, file_path: Path, entity_count: int) -> None:
        """Register a file with its expected entity count.

        Args:
            file_path: Path to the file.
            entity_count: Number of entities expected for this file.
        """
        with self._lock:
            self._pending_per_file[file_path] = entity_count

    def add_result(self, result: GenerationResult) -> bool:
        """Add a result and check if file is complete.

        Args:
            result: The generation result.

        Returns:
            True if the file is now complete, False otherwise.
        """
        with self._lock:
            file_path = result.file_path
            self._results_per_file[file_path].append(result)
            self._pending_per_file[file_path] -= 1

            # Track module description separately
            if result.entity.scope == Scope.MODULE:
                self._module_descriptions[file_path] = result.description

            return self._pending_per_file[file_path] == 0

    def get_file_results(self, file_path: Path) -> list[GenerationResult]:
        """Get all results for a file.

        Args:
            file_path: Path to the file.

        Returns:
            List of generation results for the file.
        """
        with self._lock:
            return self._results_per_file.get(file_path, [])

    def get_module_description(self, file_path: Path) -> str | None:
        """Get the module description for a file.

        Args:
            file_path: Path to the file.

        Returns:
            Module description or None.
        """
        with self._lock:
            return self._module_descriptions.get(file_path)


def scan_file(
    file_path: Path,
    root_dir: Path,
    config,
    tracker: StalenessTracker,
    force: bool,
) -> tuple[list[ParsedEntityWithFile], str]:
    """Scan a single file and extract entities.

    Args:
        file_path: Path to the file.
        root_dir: Root directory of the project.
        config: Configuration object.
        tracker: Staleness tracker.
        force: Whether to force regeneration.

    Returns:
        Tuple of (list of entities with file context, language).
    """
    file_path = file_path.resolve()

    # Detect language
    lang = detect_language(file_path)
    if not lang:
        return [], ""

    parser = get_parser(lang)
    entities = parser.parse_file(file_path)

    entities_with_context = []
    for entity in entities:
        # Check staleness
        needs_generation = force
        if not force:
            record = tracker.hash_index.get(entity.ast_hash)
            if record is None or record.stale:
                needs_generation = True

        # Get model for this entity's scope
        model = get_model_for_scope(config, config.provider, entity.scope)

        entities_with_context.append(
            ParsedEntityWithFile(
                entity=entity,
                file_path=file_path,
                language=lang,
                model=model,
                needs_generation=needs_generation,
            )
        )

    return entities_with_context, lang


def generate_description(
    entity_with_file: ParsedEntityWithFile,
    generator,
    tracker: StalenessTracker,
) -> GenerationResult:
    """Generate a description for a single entity.

    Args:
        entity_with_file: Entity with file context.
        generator: Description generator.
        tracker: Staleness tracker.

    Returns:
        Generation result.
    """
    entity = entity_with_file.entity

    if not entity_with_file.needs_generation:
        # Get existing description
        record = tracker.hash_index.get(entity.ast_hash)
        description = record.description if record else None
        return GenerationResult(
            entity=entity,
            file_path=entity_with_file.file_path,
            language=entity_with_file.language,
            description=description,
            was_generated=False,
        )

    # Generate new description
    # Only pass model parameter if the generator supports it
    if entity_with_file.model:
        description = generator.generate(entity, model=entity_with_file.model)
    else:
        description = generator.generate(entity)

    # Store in database
    tracker.set_description(entity.ast_hash, description, stale=False)

    return GenerationResult(
        entity=entity,
        file_path=entity_with_file.file_path,
        language=entity_with_file.language,
        description=description,
        was_generated=True,
    )


def pipeline_generate(
    files: list[Path],
    root_dir: Path,
    paths: Paths,
    config,
    generator,
    tracker: StalenessTracker,
    force: bool,
) -> tuple[int, int]:
    """Generate descriptions using a pipeline approach.

    Args:
        files: List of files to process.
        root_dir: Root directory of the project.
        paths: Paths object.
        config: Configuration object.
        generator: Description generator.
        tracker: Staleness tracker.
        force: Whether to force regeneration.

    Returns:
        Tuple of (total_generated, total_skipped).
    """
    from code_lod.lod_file.writer import write_lod_file

    # Initialize shared state
    progress = ProgressCounter(
        total_files=len(files), max_workers=config.max_parallelism
    )
    completion_tracker = FileCompletionTracker()
    entity_queue: Queue[ParsedEntityWithFile] = Queue()
    file_languages: dict[Path, str] = {}
    file_entity_counts: dict[Path, int] = {}

    total_generated = 0
    total_skipped = 0
    active_scanners = 0
    active_llm_workers = 0
    scanner_lock = threading.Lock()
    llm_worker_lock = threading.Lock()

    def scan_with_tracking(file_path: Path) -> None:
        """Scan a file and queue entities directly."""
        nonlocal active_scanners

        with scanner_lock:
            active_scanners += 1
            progress.set_active_scanners(active_scanners)

        try:
            entities_with_context, lang = scan_file(
                file_path, root_dir, config, tracker, force
            )
            if lang and entities_with_context:
                resolved_file_path = entities_with_context[0].file_path

                with scanner_lock:
                    file_languages[resolved_file_path] = lang
                    file_entity_counts[resolved_file_path] = len(entities_with_context)
                    completion_tracker.register_file(
                        resolved_file_path, len(entities_with_context)
                    )

                for ewc in entities_with_context:
                    entity_queue.put(ewc)
                    if ewc.needs_generation:
                        progress.increment_entities_to_generate()
                progress.increment_entities_discovered(len(entities_with_context))
        except Exception as e:
            print(f"\nError scanning {file_path}: {e}", file=sys.stderr)
        finally:
            with scanner_lock:
                active_scanners -= 1
                progress.set_active_scanners(active_scanners)
            progress.increment_files_scanned()

    def llm_worker() -> None:
        """Worker that pulls entities and generates descriptions."""
        nonlocal total_generated, total_skipped, active_llm_workers

        while True:
            ewc = entity_queue.get()
            if ewc is None:
                break

            with llm_worker_lock:
                active_llm_workers += 1
                progress.set_active_llm_workers(active_llm_workers)

            try:
                result = generate_description(ewc, generator, tracker)

                with threading.Lock():
                    if result.was_generated:
                        total_generated += 1
                        progress.increment_descriptions_generated()
                    else:
                        total_skipped += 1

                # Check if file is complete
                if completion_tracker.add_result(result):
                    # File complete, write LOD file
                    file_path = result.file_path
                    results = completion_tracker.get_file_results(file_path)
                    module_desc = completion_tracker.get_module_description(file_path)

                    # Filter out module entity from results
                    entity_desc_pairs = [
                        (r.entity, r.description)
                        for r in results
                        if r.entity.scope != Scope.MODULE
                    ]

                    if entity_desc_pairs or module_desc is not None:
                        lod_path = paths.lod_dir / file_path.relative_to(root_dir)
                        lod_path = lod_path.with_suffix(lod_path.suffix + ".lod")
                        write_lod_file(
                            lod_path,
                            entity_desc_pairs,
                            file_languages[file_path],
                            module_desc,
                        )
                        progress.increment_lod_files_written()

            except Exception as e:
                print(f"\nError generating for {ewc.entity.name}: {e}", file=sys.stderr)

            finally:
                with llm_worker_lock:
                    active_llm_workers -= 1
                    progress.set_active_llm_workers(active_llm_workers)

            entity_queue.task_done()

    # Start LLM workers first
    with ThreadPoolExecutor(max_workers=config.max_parallelism) as llm_executor:
        for _ in range(config.max_parallelism):
            llm_executor.submit(llm_worker)

        # Now start file scanning - LLM workers will process entities as they're queued
        with ThreadPoolExecutor(max_workers=config.max_parallelism) as scanner:
            # Submit all file scanning tasks
            list(scanner.map(scan_with_tracking, files))

        # Signal end of entities to LLM workers
        for _ in range(config.max_parallelism):
            entity_queue.put(None)

    # Signal end of entities
    for _ in range(config.max_parallelism):
        entity_queue.put(None)  # Sentinel values

    # Phase 2: Generate descriptions in parallel
    active_llm_workers = 0
    llm_worker_lock = threading.Lock()

    def llm_worker() -> None:
        """Worker that pulls entities and generates descriptions."""
        nonlocal total_generated, total_skipped, active_llm_workers

        while True:
            ewc = entity_queue.get()
            if ewc is None:
                break

            # Increment active workers
            with llm_worker_lock:
                active_llm_workers += 1
                progress.set_active_llm_workers(active_llm_workers)

            try:
                result = generate_description(ewc, generator, tracker)

                with threading.Lock():
                    if result.was_generated:
                        total_generated += 1
                        progress.increment_descriptions_generated()
                    else:
                        total_skipped += 1

                # Check if file is complete
                if completion_tracker.add_result(result):
                    # File complete, write LOD file
                    file_path = result.file_path
                    results = completion_tracker.get_file_results(file_path)
                    module_desc = completion_tracker.get_module_description(file_path)

                    # Filter out module entity from results
                    entity_desc_pairs = [
                        (r.entity, r.description)
                        for r in results
                        if r.entity.scope != Scope.MODULE
                    ]

                    if entity_desc_pairs or module_desc is not None:
                        lod_path = paths.lod_dir / file_path.relative_to(root_dir)
                        lod_path = lod_path.with_suffix(lod_path.suffix + ".lod")
                        write_lod_file(
                            lod_path,
                            entity_desc_pairs,
                            file_languages[file_path],
                            module_desc,
                        )
                        progress.increment_lod_files_written()

            except Exception as e:
                print(f"\nError generating for {ewc.entity.name}: {e}", file=sys.stderr)

            finally:
                # Decrement active workers
                with llm_worker_lock:
                    active_llm_workers -= 1
                    progress.set_active_llm_workers(active_llm_workers)

            entity_queue.task_done()

    # Start LLM workers
    with ThreadPoolExecutor(max_workers=config.max_parallelism) as llm_executor:
        list(llm_executor.map(lambda _: llm_worker(), range(config.max_parallelism)))

    progress.finalize_display()
    return total_generated, total_skipped
