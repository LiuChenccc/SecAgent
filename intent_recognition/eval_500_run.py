"""
用 eval_500.json（从 test.jsonl 抽取的高质量子集）运行评估。

运行：INTENT_API_KEY=xxx python3 -m intent_recognition.eval_500_run
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intent_recognition.recognizer import IntentRecognizer
from intent_recognition.eval import evaluate

EVAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_500.json")


def main():
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print("=" * 60)
    print("  意图识别评估（500 条高质量测试集）")
    print("=" * 60)

    recognizer = IntentRecognizer(backend="api")
    print(f"  模型: {recognizer.api_model}")
    print(f"  测试集: {len(dataset)} 条")
    print()

    results = evaluate(recognizer, dataset, verbose=True)

    print()
    print("=" * 60)
    print(f"  主意图准确率: {results['main_intent_accuracy']}%")
    print(f"  子意图准确率: {results['sub_intent_accuracy']}%")
    print(f"  多意图召回率: {results['multi_intent_recall']}%")
    print(f"  API错误数: {results['errors']}")
    print("=" * 60)

    # 保存结果
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_500_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {out_path}")


if __name__ == "__main__":
    main()
