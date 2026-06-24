from infer import IntentAnalyzer
import pandas as pd
from tqdm import tqdm
import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def normalize_intents(intent_list):
    if not isinstance(intent_list, list):
        return set(), set(), set()

    pair_set = set()
    main_set = set()
    sub_set = set()

    for item in intent_list:
        if not isinstance(item, dict):
            continue
        main_id = item.get("main_intent_id")
        sub_id = item.get("sub_intent_id")

        if main_id is not None:
            main_set.add(int(main_id))
        if sub_id is not None:
            sub_set.add(int(sub_id))
        if main_id is not None and sub_id is not None:
            pair_set.add((int(main_id), int(sub_id)))

    return pair_set, main_set, sub_set


def compute_metrics(y_true_pairs, y_pred_pairs):
    total = len(y_true_pairs)
    if total == 0:
        return {}

    main_correct = 0
    sub_correct = 0
    overall_correct = 0

    multi_total = 0
    multi_correct = 0

    for true_pairs, pred_pairs in zip(y_true_pairs, y_pred_pairs):
        true_main = {m for m, s in true_pairs}
        pred_main = {m for m, s in pred_pairs}

        true_sub = {s for m, s in true_pairs}
        pred_sub = {s for m, s in pred_pairs}

        if true_main == pred_main:
            main_correct += 1

        if true_sub == pred_sub:
            sub_correct += 1

        if true_pairs == pred_pairs:
            overall_correct += 1

        if len(true_pairs) > 1:
            multi_total += 1
            if true_sub == pred_sub:
                multi_correct += 1

    return {
        "main_intent_accuracy": round(main_correct / total, 4),
        "sub_intent_accuracy": round(sub_correct / total, 4),
        "multi_intent_accuracy": round(multi_correct / multi_total, 4) if multi_total > 0 else None,
        "overall_accuracy": round(overall_correct / total, 4),
        "total_samples": total,
        "multi_intent_samples": multi_total,
    }


class IntentEvaluator:
    def __init__(self):
        model_id = "Qwen/Qwen3-8B"
        adapter_dir = '/mlx_devbox/users/wuchuncheng/playground/security_intent/output/v1/v2-20260312-002920/checkpoint-132'
        self.analyzer = IntentAnalyzer(model_id, adapter_dir)

    def _process_one(self, idx, row):
        messages = row['messages']
        user_content = messages[1]['content']

        true_raw = messages[-1]['content']
        true_intents = json.loads(true_raw)

        response = self.analyzer.predict(user_content)
        pred_intents = json.loads(response)

        true_pairs, true_main, true_sub = normalize_intents(true_intents)
        pred_pairs, pred_main, pred_sub = normalize_intents(pred_intents)

        return idx, {
            "messages": messages,
            "ground_truth": true_intents,
            "prediction": pred_intents,
            "true_main_set": sorted(list(true_main)),
            "pred_main_set": sorted(list(pred_main)),
            "true_sub_set": sorted(list(true_sub)),
            "pred_sub_set": sorted(list(pred_sub)),
            "main_correct": true_main == pred_main,
            "sub_correct": true_sub == pred_sub,
            "overall_correct": true_pairs == pred_pairs,
            "is_multi_intent": len(true_pairs) > 1,
            "_true_pairs": true_pairs,
            "_pred_pairs": pred_pairs,
        }

    def run(self, input_file, output_file, max_workers=8):
        df = pd.read_json(input_file, lines=True)

        results = [None] * len(df)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._process_one, idx, row): idx
                for idx, row in df.iterrows()
            }

            for future in tqdm(as_completed(futures), total=len(futures), desc="评估进度"):
                idx = futures[future]
                try:
                    _, result = future.result()
                    results[idx] = result
                except Exception as e:
                    logging.exception(f"样本 idx={idx} 处理失败: {e}")
                    results[idx] = {
                        "messages": df.iloc[idx]["messages"],
                        "ground_truth": None,
                        "prediction": None,
                        "true_main_set": [],
                        "pred_main_set": [],
                        "true_sub_set": [],
                        "pred_sub_set": [],
                        "main_correct": False,
                        "sub_correct": False,
                        "overall_correct": False,
                        "is_multi_intent": False,
                        "_true_pairs": set(),
                        "_pred_pairs": set(),
                        "error": str(e),
                    }

        y_true_pairs = [item["_true_pairs"] for item in results]
        y_pred_pairs = [item["_pred_pairs"] for item in results]
        metrics = compute_metrics(y_true_pairs, y_pred_pairs)

        for item in results:
            item.pop("_true_pairs", None)
            item.pop("_pred_pairs", None)

        result_df = pd.DataFrame(results)
        result_df.to_json(output_file, lines=True, orient='records', force_ascii=False)

        metrics_file = output_file.replace(".jsonl", "_metrics.json")
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)

        logging.info(f"评估完成，结果已保存到 {output_file}")
        logging.info(f"指标: {json.dumps(metrics, ensure_ascii=False)}")


if __name__ == '__main__':
    input_file = 'data/test.jsonl'
    output_file = 'data/test_output.jsonl'
    evaluator = IntentEvaluator()
    evaluator.run(input_file, output_file, max_workers=8)