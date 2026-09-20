"""Tests for CLI commands (generate, status, update)."""

from typer.testing import CliRunner

from code_lod.cli import app

runner = CliRunner()


class TestGenerateCommand:
    """Tests for code-lod generate."""

    def test_generate_creates_lod_files(self, tmp_project, sample_file) -> None:
        """Test generate produces descriptions and a .lod file."""
        result = runner.invoke(app, ["generate", str(tmp_project)])
        assert result.exit_code == 0
        assert "Generated 4 descriptions" in result.output
        lod_path = tmp_project / ".code-lod" / ".lod" / "src" / "sample.py.lod"
        assert lod_path.exists()

    def test_generate_second_run_skips_all(self, tmp_project, sample_file) -> None:
        """Test a second generate run skips everything."""
        runner.invoke(app, ["generate", str(tmp_project)])
        result = runner.invoke(app, ["generate", str(tmp_project)])
        assert result.exit_code == 0
        assert "Generated 0 descriptions" in result.output
        assert "Skipped 4 existing descriptions" in result.output

    def test_generate_respects_ignore_patterns(self, tmp_project, sample_file) -> None:
        """Test files matching ignore patterns are not processed."""
        tests_dir = tmp_project / "tests"
        tests_dir.mkdir()
        (tests_dir / "sample_test.py").write_text("def test_x():\n    pass\n")
        result = runner.invoke(app, ["generate", str(tmp_project)])
        assert result.exit_code == 0
        assert "Generated 4 descriptions" in result.output

    def test_generate_requires_initialization(self, tmp_path, monkeypatch) -> None:
        """Test generate fails cleanly on an uninitialized directory."""
        uninit = tmp_path / "uninit"
        uninit.mkdir()
        monkeypatch.chdir(uninit)
        result = runner.invoke(app, ["generate", str(uninit)])
        assert result.exit_code == 1
        assert "not initialized" in result.output + result.stderr


class TestStatusCommand:
    """Tests for code-lod status."""

    def test_status_reports_stale_before_generate(
        self, tmp_project, sample_file
    ) -> None:
        """Test all entities are stale before any generation."""
        result = runner.invoke(app, ["status", str(tmp_project)])
        assert result.exit_code == 1
        assert "Stale: 4" in result.output
        assert "[STALE] function: greet" in result.output

    def test_status_reports_fresh_after_generate(
        self, tmp_project, sample_file
    ) -> None:
        """Test everything is fresh after generation."""
        runner.invoke(app, ["generate", str(tmp_project)])
        result = runner.invoke(app, ["status", str(tmp_project)])
        assert result.exit_code == 0
        assert "Fresh: 4" in result.output
        assert "Stale: 0" in result.output

    def test_status_detects_stale_after_code_change(
        self, tmp_project, sample_file
    ) -> None:
        """Test code changes mark the affected entities stale."""
        runner.invoke(app, ["generate", str(tmp_project)])
        sample_file.write_text(sample_file.read_text().replace("Hello", "Howdy"))
        result = runner.invoke(app, ["status", str(tmp_project)])
        assert result.exit_code == 1
        assert "Stale: 2" in result.output  # module + greet changed

    def test_status_stale_only_hides_fresh_entities(
        self, tmp_project, sample_file
    ) -> None:
        """Test --stale-only omits fresh entries from the listing."""
        runner.invoke(app, ["generate", str(tmp_project)])
        sample_file.write_text(sample_file.read_text().replace("Hello", "Howdy"))
        result = runner.invoke(app, ["status", "--stale-only", str(tmp_project)])
        assert result.exit_code == 1
        assert "[FRESH]" not in result.output
        assert "[STALE]" in result.output

    def test_status_requires_initialization(self, tmp_path, monkeypatch) -> None:
        """Test status fails cleanly on an uninitialized directory."""
        uninit = tmp_path / "uninit"
        uninit.mkdir()
        monkeypatch.chdir(uninit)
        result = runner.invoke(app, ["status", str(uninit)])
        assert result.exit_code == 1
        assert "not initialized" in result.output + result.stderr


class TestUpdateCommand:
    """Tests for code-lod update."""

    def test_update_with_no_stale_descriptions(self, tmp_project, sample_file) -> None:
        """Test update reports nothing to do when everything is fresh."""
        runner.invoke(app, ["generate", str(tmp_project)])
        result = runner.invoke(app, ["update", "-y", str(tmp_project)])
        assert result.exit_code == 0
        assert "No stale descriptions to update" in result.output

    def test_update_regenerates_stale_descriptions(
        self, tmp_project, sample_file
    ) -> None:
        """Test update regenerates only entities affected by code changes."""
        runner.invoke(app, ["generate", str(tmp_project)])
        sample_file.write_text(sample_file.read_text().replace("Hello", "Howdy"))
        result = runner.invoke(app, ["update", "-y", str(tmp_project)])
        assert result.exit_code == 0
        assert "Found 2 stale descriptions" in result.output
        assert "Updated 2 descriptions" in result.output
        assert "Skipped 2 descriptions" in result.output

        status_result = runner.invoke(app, ["status", str(tmp_project)])
        assert status_result.exit_code == 0
        assert "Stale: 0" in status_result.output

    def test_update_requires_confirmation(self, tmp_project, sample_file) -> None:
        """Test update aborts without --auto-approve when declined."""
        runner.invoke(app, ["generate", str(tmp_project)])
        sample_file.write_text(sample_file.read_text().replace("Hello", "Howdy"))
        result = runner.invoke(app, ["update", str(tmp_project)], input="n\n")
        assert result.exit_code == 1
        assert "Update all stale descriptions?" in result.output

    def test_update_requires_initialization(self, tmp_path, monkeypatch) -> None:
        """Test update fails cleanly on an uninitialized directory."""
        uninit = tmp_path / "uninit"
        uninit.mkdir()
        monkeypatch.chdir(uninit)
        result = runner.invoke(app, ["update", str(uninit)])
        assert result.exit_code == 1
        assert "not initialized" in result.output + result.stderr
