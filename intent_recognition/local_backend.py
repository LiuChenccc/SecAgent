import os
from typing import Optional


class LocalBackend:
    def __init__(self, model_id: str = "Qwen/Qwen3-8B", adapter_dir: Optional[str] = None):
        if not adapter_dir:
            raise RuntimeError("本地模式需要指定 adapter_dir 参数")
        self.model_id = model_id
        self.adapter_dir = adapter_dir
        self._analyzer = None

    def predict(self, user_input: str, max_new_tokens: int = 512) -> str:
        if self._analyzer is None:
            self._init()
        return self._analyzer.predict(user_input, max_new_tokens)

    def _init(self):
        import sys
        lora_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ytsb_intent_lora", "security_intent",
        )
        if lora_dir not in sys.path:
            sys.path.insert(0, lora_dir)
        from infer import IntentAnalyzer
        self._analyzer = IntentAnalyzer(
            model_id=self.model_id,
            adapter_dir=self.adapter_dir,
        )
