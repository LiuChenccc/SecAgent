from intent_recognition.taxonomy import MAIN_INTENT_NAMES, SUB_INTENT_NAMES


def test_main_intent_count():
    assert len(MAIN_INTENT_NAMES) == 6


def test_main_intent_ids():
    assert set(MAIN_INTENT_NAMES.keys()) == {1, 2, 3, 4, 5, 6}


def test_sub_intent_count():
    assert len(SUB_INTENT_NAMES) == 43


def test_sub_intents_have_valid_main_ids():
    for (main_id, _) in SUB_INTENT_NAMES.keys():
        assert main_id in MAIN_INTENT_NAMES
