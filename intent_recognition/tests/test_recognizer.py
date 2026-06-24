from intent_recognition.recognizer import IntentRecognizer


def test_parse_valid_json():
    r = IntentRecognizer(backend="api")
    raw = '[{"main_intent_id": 1, "main_intent_name": "威胁检测与识别", "sub_intent_id": 1, "sub_intent_name": "恶意代码分析"}]'
    result = r._parse_response(raw)
    assert len(result) == 1
    assert result[0]["main_intent_id"] == 1


def test_parse_multi_intent():
    r = IntentRecognizer(backend="api")
    raw = '[{"main_intent_id": 1, "main_intent_name": "A", "sub_intent_id": 1, "sub_intent_name": "B"}, {"main_intent_id": 6, "main_intent_name": "C", "sub_intent_id": 1, "sub_intent_name": "D"}]'
    result = r._parse_response(raw)
    assert len(result) == 2


def test_parse_noisy_json():
    r = IntentRecognizer(backend="api")
    raw = '一些前缀\n[{"main_intent_id": 2, "main_intent_name": "X", "sub_intent_id": 1, "sub_intent_name": "Y"}]\n后缀'
    result = r._parse_response(raw)
    assert len(result) == 1
    assert result[0]["main_intent_id"] == 2


def test_parse_single_dict():
    r = IntentRecognizer(backend="api")
    raw = '{"main_intent_id": 3, "main_intent_name": "A", "sub_intent_id": 1, "sub_intent_name": "B"}'
    result = r._parse_response(raw)
    assert len(result) == 1


def test_parse_empty():
    r = IntentRecognizer(backend="api")
    assert r._parse_response("") == []
    assert r._parse_response(None) == []


def test_parse_invalid():
    r = IntentRecognizer(backend="api")
    assert r._parse_response("not json at all") == []


def test_format_intents_for_display():
    r = IntentRecognizer(backend="api")
    intents = [
        {"main_intent_id": 1, "main_intent_name": "威胁检测与识别", "sub_intent_id": 1, "sub_intent_name": "恶意代码分析"},
    ]
    display = r.format_intents_for_display(intents)
    assert "威胁检测与识别" in display
    assert "恶意代码分析" in display


def test_format_empty():
    r = IntentRecognizer(backend="api")
    assert "未识别" in r.format_intents_for_display([])


def test_build_enhanced_prompt():
    r = IntentRecognizer(backend="api")
    prompt = r._build_enhanced_prompt(
        "测试输入",
        skill_context="候选Skills: ...",
        few_shot_context="案例1: ...",
    )
    assert "JSON" in prompt
    assert "候选Skills" in prompt
    assert "案例1" in prompt
