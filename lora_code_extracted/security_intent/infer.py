import time
import torch
from modelscope import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

class IntentAnalyzer:
    def __init__(self, model_id='Qwen/Qwen3-8B', adapter_dir=None):
        """
        初始化分析器，加载模型和分词器
        """
        print("正在加载模型和适配器，请稍候...")
        # 下载/获取模型路径
        self.model_dir = snapshot_download(model_id)
        self.adapter_dir = adapter_dir
        
        # 加载基础模型
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_dir, 
            torch_dtype='auto', 
            device_map='auto', 
            trust_remote_code=True
        )
        
        # 加载 LoRA 适配器
        if self.adapter_dir:
            self.model = PeftModel.from_pretrained(self.model, self.adapter_dir)
            print(f"成功加载适配器: {self.adapter_dir}")
        
        # 加载分词器
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, trust_remote_code=True)
        self.system_prompt = "你是一个专业的意图识别助手。请根据对话上下文识别用户意图。输出格式必须为 JSON 数组，包含：main_intent_id, main_intent_name, sub_intent_id, sub_intent_name。"
        # self.system_prompt = "你是一个搜索意图分析专家，判断用户是否寻找用户意图获取可能在官网中出现的信息。，如果是输出1,否则输出0."

    def predict(self, content, max_new_tokens=512):
        """
        对输入内容进行意图预测
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": content}
        ]
        
        # 应用模板转换
        text = self.tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True,
            enable_thinking=False
        )
        
        print([text])
        # 准备输入
        model_inputs = self.tokenizer([text], return_tensors='pt', add_special_tokens=False).to(self.model.device)
        
        # 执行推理
        with torch.no_grad():
            generated_ids = self.model.generate(
                **model_inputs, 
                max_new_tokens=max_new_tokens, 
                do_sample=False
            )
        
        # 裁剪掉输入部分的 tokens，只保留生成的回复
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response.strip()

# --- 使用示例 ---
if __name__ == "__main__":
    # 配置路径
    ADAPTER_PATH = '/mlx_devbox/users/wuchuncheng/playground/security_intent/output/v1/v2-20260312-002920/checkpoint-132'
    # <|im_start|>system\n你是一个搜索意图分析专家，判断用户是否寻找某个实体的官方入口，或获取只有官网/官方渠道才能提供的权威信息，如果是输出1,否则输出0.<|im_end|>\n<|im_start|>user\n字节跳动<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n
    # <|im_start|>system\n你是一个搜索意图分析专家，判断用户是否寻找某个实体的官方入口，或获取只有官网/官方渠道才能提供的权威信息，如果是输出1, 否则输出0。<|im_end|>\n<|im_start|>user\n字节跳动<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n
    # 实例化类
    analyzer = IntentAnalyzer(adapter_dir=ADAPTER_PATH)

    while True:
        try:
            user_input = input('请输入 (输入 q 退出): ')
            if user_input.lower() == 'q':
                break
        except Exception as e:
            print(f"输入处理失败: {e}")
            continue
        result = analyzer.predict(user_input)
        print(f"意图分类结果: {result}")