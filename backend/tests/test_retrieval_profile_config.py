import importlib


def test_unknown_profile_falls_back_to_serving(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_PROFILE", "unknown")
    import app.utils.config as config

    importlib.reload(config)
    params = config.get_retrieval_params()

    assert params["candidate_k"] == config.SERVING_RETRIEVER_CANDIDATE_K
    assert params["top_k"] == config.SERVING_RETRIEVER_TOP_K
    assert params["rerank_max_k"] == config.SERVING_RETRIEVER_RERANK_MAX_K


def test_profile_argument_takes_precedence(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_PROFILE", "serving")
    import app.utils.config as config

    importlib.reload(config)
    params = config.get_retrieval_params("evaluation")

    assert params["candidate_k"] == config.EVAL_RETRIEVER_CANDIDATE_K
    assert params["top_k"] == config.EVAL_RETRIEVER_TOP_K
    assert params["rerank_max_k"] == config.EVAL_RETRIEVER_RERANK_MAX_K
