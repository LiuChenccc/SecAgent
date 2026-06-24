CUDA_VISIBLE_DEVICES=0 \
swift sft \
    --model Qwen/Qwen3-8B \
    --train_type lora \
    --dataset '/mlx_devbox/users/wuchuncheng/playground/security_intent/data/train.jsonl' \
    --split_dataset_ratio 0.05 \
    --loss_scale ignore_empty_think \
    --torch_dtype float16 \
    --num_train_epochs 2 \
    --per_device_train_batch_size 16 \
    --per_device_eval_batch_size 16 \
    --learning_rate 1e-4 \
    --lora_rank 8 \
    --lora_alpha 32 \
    --target_modules all-linear \
    --gradient_accumulation_steps 16 \
    --eval_steps 50 \
    --save_steps 50 \
    --save_total_limit 10 \
    --logging_steps 5 \
    --max_length 2048 \
    --output_dir /mlx_devbox/users/wuchuncheng/playground/security_intent/output/v1 \
    --warmup_ratio 0.05 \
    --dataloader_num_workers 4 \
    --model_author swift \
    --model_name swift-robot \
    # --report_to wandb 

# bash train.sh > train.log 2>&1