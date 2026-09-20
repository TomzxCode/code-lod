"""Tests for the parallel generation pipeline."""

from code_lod.config import Config, Paths
from code_lod.llm.description_generator.mock import MockDescriptionGenerator
from code_lod.pipeline import pipeline_generate
from code_lod.staleness import StalenessTracker


class TestPipelineGenerate:
    """Tests for pipeline_generate."""

    def _run(self, tmp_project, sample_file, force: bool = False):
        """Run the pipeline once over the sample file."""
        return pipeline_generate(
            files=[sample_file],
            root_dir=tmp_project,
            paths=Paths(tmp_project),
            config=Config(),
            generator=MockDescriptionGenerator(),
            tracker=StalenessTracker(tmp_project),
            force=force,
            max_parallelism=2,
        )

    def test_generates_descriptions_and_writes_lod(
        self, tmp_project, sample_file
    ) -> None:
        """Test the first run generates every entity and writes a .lod file."""
        generated, skipped = self._run(tmp_project, sample_file)
        assert generated == 4  # module, greet, Greeter, greet_all
        assert skipped == 0

        lod_path = tmp_project / ".code-lod" / ".lod" / "src" / "sample.py.lod"
        assert lod_path.exists()
        content = lod_path.read_text()
        assert content.count("@lod hash:") == 3  # non-module entities
        assert "Module sample" in content
        assert "def greet" in content
        assert "class Greeter" in content

    def test_second_run_skips_fresh_entities(self, tmp_project, sample_file) -> None:
        """Test unchanged sources are skipped on the next run."""
        first_generated, first_skipped = self._run(tmp_project, sample_file)
        assert (first_generated, first_skipped) == (4, 0)
        second_generated, second_skipped = self._run(tmp_project, sample_file)
        assert (second_generated, second_skipped) == (0, 4)

    def test_force_regenerates_all(self, tmp_project, sample_file) -> None:
        """Test force regeneration bypasses the freshness check."""
        self._run(tmp_project, sample_file)
        generated, skipped = self._run(tmp_project, sample_file, force=True)
        assert (generated, skipped) == (4, 0)

    def test_records_are_fresh_after_run(self, tmp_project, sample_file) -> None:
        """Test stored records are marked fresh once generated."""
        self._run(tmp_project, sample_file)
        tracker = StalenessTracker(tmp_project)
        from code_lod.parsers.tree_sitter_parser import get_parser

        entities = get_parser("python").parse_file(sample_file)
        status = tracker.check_entities(entities)
        assert status.total_entities == 4
        assert status.stale_count == 0
        assert status.fresh_count == 4
