from pathlib import Path
from agentic_pr.repo_instructions import load_repo_instructions


def test_missing_folder(tmp_path: Path) -> None:
    result = load_repo_instructions(tmp_path, max_bytes=1000)
    assert result.instructions_text is None
    assert result.safety_text is None
    assert result.examples_text is None
    assert result.commands == {}
    assert result.files_found == []


def test_loads_files(tmp_path: Path) -> None:
    agent_dir = tmp_path / ".agentic-pr"
    agent_dir.mkdir()
    (agent_dir / "instructions.md").write_text("Test instructions")
    (agent_dir / "safety.md").write_text("Test safety")
    (agent_dir / "examples.md").write_text("Test examples")
    (agent_dir / "commands.env").write_text("TEST_CMD=pytest\nLINT_CMD=flake8")
    
    result = load_repo_instructions(tmp_path, max_bytes=1000)
    
    assert result.instructions_text == "Test instructions"
    assert result.safety_text == "Test safety"
    assert result.examples_text == "Test examples"
    assert result.commands == {"TEST_CMD": "pytest", "LINT_CMD": "flake8"}
    assert set(result.files_found) == {"instructions.md", "safety.md", "examples.md", "commands.env"}


def test_max_bytes_limit(tmp_path: Path) -> None:
    agent_dir = tmp_path / ".agentic-pr"
    agent_dir.mkdir()
    (agent_dir / "instructions.md").write_text("A" * 1500)
    
    result = load_repo_instructions(tmp_path, max_bytes=1000)
    
    assert result.instructions_text is not None
    assert result.instructions_text.startswith("A" * 1000)
    assert "[Warning" in result.instructions_text
    assert len(result.instructions_text) > 1000


def test_unknown_files_ignored(tmp_path: Path) -> None:
    agent_dir = tmp_path / ".agentic-pr"
    agent_dir.mkdir()
    (agent_dir / "instructions.md").write_text("Test instructions")
    (agent_dir / "unknown.txt").write_text("Should be ignored")
    
    result = load_repo_instructions(tmp_path, max_bytes=1000)
    
    assert "unknown.txt" not in result.files_found
