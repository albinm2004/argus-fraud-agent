"""End-to-end smoke test for the LangGraph orchestration. Requires the
trained model (models/pattern_analyst*.joblib) and the local graph
(data/processed/entity_graph.gpickle) to exist -- skipped if not, so this
doesn't block a fresh clone from running its other tests."""
from pathlib import Path

import pytest

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "entity_graph.gpickle"

requires_artifacts = pytest.mark.skipif(
    not (MODELS_DIR / "pattern_analyst.joblib").exists() or not GRAPH_PATH.exists(),
    reason="requires trained model + built graph (run scripts/train_baseline.py and "
           "agents.graph_builder.build_and_save() first)",
)


@requires_artifacts
def test_pipeline_runs_end_to_end():
    from agents.features import build_dataset
    from agents.pipeline import investigate

    df, feature_cols, split_idx = build_dataset()
    test_df = df.iloc[split_idx:]
    row = test_df.iloc[0]

    result = investigate(row["TransactionID"], row, run_red_team=False)

    assert "verdict_result" in result
    assert result["verdict_result"]["verdict"] in {"block", "flag", "allow"}
    assert "graph_features" in result
    assert isinstance(result["verdict_result"]["evidence"], list)
    assert len(result["verdict_result"]["evidence"]) > 0
