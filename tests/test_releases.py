"""Tests for ReleaseGenerator."""

import pytest
from datetime import datetime

from self_healing_agent.releases.generator import (
    ReleaseGenerator,
    ReleaseNote,
    WorkflowStats,
)


class TestReleaseGenerator:
    """Test cases for ReleaseGenerator."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return {
            "releases": {
                "enabled": True,
                "schedule": {
                    "interval_minutes": 10
                },
                "release_notes": {
                    "format": "markdown",
                    "sections": [
                        {
                            "name": "features",
                            "title": "🆕 New Features",
                            "auto_detect": True
                        },
                        {
                            "name": "bug_fixes",
                            "title": "🐛 Bug Fixes",
                            "auto_detect": True
                        }
                    ]
                },
                "changelog": {
                    "path": "TEST_CHANGELOG.md",
                    "git_integration": {
                        "auto_commit": False,
                        "create_tag": False
                    }
                }
            }
        }

    @pytest.fixture
    def generator(self, config, tmp_path):
        """Create a ReleaseGenerator instance."""
        return ReleaseGenerator(config)

    @pytest.fixture
    def stats(self):
        """Create sample workflow stats."""
        return WorkflowStats(
            bugs_detected=5,
            bugs_fixed=3,
            total_runs=10,
            success_rate=75.0,
            avg_fix_time=2.5,
            last_run=datetime.now()
        )

    def test_initialization(self, generator):
        """Test generator initialization."""
        assert generator is not None
        assert generator.config is not None
        assert generator.releases_config is not None

    def test_generate_version_no_fixes(self, generator):
        """Test version generation with no fixes."""
        stats = WorkflowStats(bugs_fixed=0)
        version = generator.generate_version(stats)
        assert version == "1.0.0"

    def test_generate_version_with_fixes(self, generator):
        """Test version generation with fixes."""
        stats = WorkflowStats(bugs_fixed=3)
        version = generator.generate_version(stats)
        assert version == "1.1.0"

    def test_generate_version_many_fixes(self, generator):
        """Test version generation with many fixes."""
        stats = WorkflowStats(bugs_fixed=10)
        version = generator.generate_version(stats)
        assert version == "2.0.0"

    def test_generate_release_notes(self, generator, stats):
        """Test release notes generation."""
        release = generator.generate_release_notes(stats)
        
        assert isinstance(release, ReleaseNote)
        assert release.version is not None
        assert release.content is not None
        assert "1.1.0" in release.content or "1.0.0" in release.content
        assert str(stats.bugs_detected) in release.content
        assert str(stats.bugs_fixed) in release.content

    def test_save_release(self, generator, stats, tmp_path):
        """Test saving release notes."""
        release = generator.generate_release_notes(stats)
        
        # Change artifacts path to temp
        generator.artifacts_path = tmp_path / "releases"
        generator.artifacts_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = generator.save_release(release)
        
        assert "markdown" in saved_files
        assert "json" in saved_files
        assert saved_files["markdown"].exists()
        assert saved_files["json"].exists()

    def test_should_auto_release_true(self, generator):
        """Test auto-release conditions."""
        stats = WorkflowStats(bugs_fixed=5)
        assert generator.should_auto_release(stats) is True

    def test_should_auto_release_false(self, generator):
        """Test auto-release conditions with no fixes."""
        stats = WorkflowStats(bugs_fixed=0)
        # With default config, should still return True if no conditions
        assert generator.should_auto_release(stats) is True

    def test_generate_and_save(self, generator, stats, tmp_path):
        """Test full generate and save flow."""
        generator.artifacts_path = tmp_path / "releases"
        generator.artifacts_path.mkdir(parents=True, exist_ok=True)
        
        result = generator.generate_and_save(stats)
        
        assert result["status"] == "success"
        assert "version" in result
        assert "files" in result
        assert "markdown" in result["files"]
        assert "json" in result["files"]
