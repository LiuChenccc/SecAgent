from agent.agent import SecurityAgent


class DummySkillsRetriever:
    def __init__(self, skills_dir):
        self.skills_dir = skills_dir

    def load_all(self, extra_dirs=None):
        return 0


class DummyMemorySystem:
    def __init__(self, memory_path):
        self.memory_path = memory_path

    def load(self):
        return 0


def test_security_agent_uses_separate_intent_and_executor_config(monkeypatch):
    monkeypatch.setattr("agent.agent.SkillsRetriever", DummySkillsRetriever)
    monkeypatch.setattr("agent.agent.MemorySystem", DummyMemorySystem)

    agent = SecurityAgent(
        intent_api_base="https://intent.example/v1",
        intent_api_key="intent-key",
        intent_model="intent-model",
        executor_api_base="https://executor.example/v1",
        executor_api_key="executor-key",
        executor_model="executor-model",
    )

    assert agent.intent_recognizer.api_base == "https://intent.example/v1"
    assert agent.intent_recognizer.api_key == "intent-key"
    assert agent.intent_recognizer.api_model == "intent-model"

    assert agent.executor.api_base == "https://executor.example/v1"
    assert agent.executor.api_key == "executor-key"
    assert agent.executor.api_model == "executor-model"


def test_security_agent_legacy_api_config_still_configures_both(monkeypatch):
    monkeypatch.setattr("agent.agent.SkillsRetriever", DummySkillsRetriever)
    monkeypatch.setattr("agent.agent.MemorySystem", DummyMemorySystem)

    agent = SecurityAgent(
        api_base="https://legacy.example/v1",
        api_key="legacy-key",
        api_model="legacy-model",
    )

    assert agent.intent_recognizer.api_base == "https://legacy.example/v1"
    assert agent.intent_recognizer.api_key == "legacy-key"
    assert agent.intent_recognizer.api_model == "legacy-model"

    assert agent.executor.api_base == "https://legacy.example/v1"
    assert agent.executor.api_key == "legacy-key"
    assert agent.executor.api_model == "legacy-model"


def test_security_agent_defaults_split_env_groups(monkeypatch):
    monkeypatch.setattr("agent.agent.SkillsRetriever", DummySkillsRetriever)
    monkeypatch.setattr("agent.agent.MemorySystem", DummyMemorySystem)
    monkeypatch.setenv("INTENT_API_BASE", "https://intent-env.example/v1")
    monkeypatch.setenv("INTENT_API_KEY", "intent-env-key")
    monkeypatch.setenv("INTENT_MODEL", "intent-env-model")
    monkeypatch.setenv("DASHSCOPE_API_BASE", "https://executor-env.example/v1")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "executor-env-key")
    monkeypatch.setenv("DASHSCOPE_MODEL", "executor-env-model")

    agent = SecurityAgent()

    assert agent.intent_recognizer.api_base == "https://intent-env.example/v1"
    assert agent.intent_recognizer.api_key == "intent-env-key"
    assert agent.intent_recognizer.api_model == "intent-env-model"

    assert agent.executor.api_base == "https://executor-env.example/v1"
    assert agent.executor.api_key == "executor-env-key"
    assert agent.executor.api_model == "executor-env-model"
