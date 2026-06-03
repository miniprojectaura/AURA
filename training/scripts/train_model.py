"""
Unsloth QLoRA Finetuning Script — Fashion AI Models.

This script runs on Google Colab (free T4 GPU) or any CUDA machine.
It handles:
1. Loading base model with 4-bit quantization
2. Applying LoRA adapters
3. Training with the SFT trainer
4. Evaluation metrics
5. Exporting to GGUF for Ollama deployment

Usage:
    python train_model.py --config configs/intent_classifier.yaml
    python train_model.py --config configs/design_agent.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml


def load_config(config_path: str) -> dict:
    """Load YAML training config."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def train(config_path: str) -> None:
    """Full training pipeline with Unsloth."""

    config = load_config(config_path)
    model_config = config["model"]
    lora_config = config["lora"]
    train_config = config["training"]
    data_config = config["data"]
    export_config = config.get("export", {})

    print(f"{'='*60}")
    print(f"  Fashion AI — Model Finetuning")
    print(f"  Base Model: {model_config['base_model']}")
    print(f"  Config: {config_path}")
    print(f"{'='*60}")

    # ── Step 1: Load model with Unsloth ──────────────────────────────
    print("\n[1/6] Loading model with Unsloth 4-bit quantization...")
    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_config["base_model"],
        max_seq_length=model_config["max_seq_length"],
        load_in_4bit=model_config.get("load_in_4bit", True),
        dtype=model_config.get("dtype"),
    )
    print(f"  ✅ Model loaded: {model_config['base_model']}")

    # ── Step 2: Apply LoRA adapters ──────────────────────────────────
    print("\n[2/6] Applying LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_config["r"],
        lora_alpha=lora_config["lora_alpha"],
        lora_dropout=lora_config["lora_dropout"],
        target_modules=lora_config["target_modules"],
        bias=lora_config["bias"],
        use_gradient_checkpointing="unsloth",  # Unsloth optimized
        random_state=train_config.get("seed", 42),
    )
    print(f"  ✅ LoRA applied: r={lora_config['r']}, alpha={lora_config['lora_alpha']}")

    # ── Step 3: Load and format dataset ──────────────────────────────
    print("\n[3/6] Loading training data...")
    from datasets import load_dataset
    from unsloth.chat_templates import get_chat_template

    tokenizer = get_chat_template(
        tokenizer,
        chat_template=data_config.get("chat_template", "llama-3"),
    )

    def format_conversations(examples):
        """Convert ShareGPT conversations to model input format."""
        texts = []
        for convos in examples["conversations"]:
            messages = []
            for turn in convos:
                role_map = {"system": "system", "human": "user", "gpt": "assistant"}
                messages.append({
                    "role": role_map.get(turn["from"], turn["from"]),
                    "content": turn["value"],
                })
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            texts.append(text)
        return {"text": texts}

    # Load JSONL datasets
    train_file = data_config["train_file"]
    eval_file = data_config.get("eval_file")

    train_dataset = load_dataset("json", data_files=train_file, split="train")
    train_dataset = train_dataset.map(format_conversations, batched=True)

    eval_dataset = None
    if eval_file and Path(eval_file).exists():
        eval_dataset = load_dataset("json", data_files=eval_file, split="train")
        eval_dataset = eval_dataset.map(format_conversations, batched=True)

    print(f"  ✅ Train: {len(train_dataset)} samples")
    if eval_dataset:
        print(f"  ✅ Eval: {len(eval_dataset)} samples")

    # ── Step 4: Configure trainer ────────────────────────────────────
    print("\n[4/6] Configuring SFT Trainer...")
    from trl import SFTTrainer
    from transformers import TrainingArguments

    training_args = TrainingArguments(
        output_dir=train_config["output_dir"],
        num_train_epochs=train_config["num_train_epochs"],
        per_device_train_batch_size=train_config["per_device_train_batch_size"],
        gradient_accumulation_steps=train_config["gradient_accumulation_steps"],
        learning_rate=float(train_config["learning_rate"]),
        weight_decay=train_config["weight_decay"],
        warmup_ratio=train_config["warmup_ratio"],
        lr_scheduler_type=train_config["lr_scheduler_type"],
        max_grad_norm=train_config["max_grad_norm"],
        fp16=train_config.get("fp16", False),
        bf16=train_config.get("bf16", True),
        logging_steps=train_config["logging_steps"],
        save_strategy=train_config["save_strategy"],
        eval_strategy=train_config.get("eval_strategy", "no"),
        seed=train_config.get("seed", 42),
        optim=train_config.get("optim", "adamw_8bit"),
        group_by_length=train_config.get("group_by_length", False),
        report_to="none",  # Set to "wandb" or "mlflow" if configured
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        dataset_text_field="text",
        max_seq_length=model_config["max_seq_length"],
        packing=data_config.get("packing", False),
        args=training_args,
    )

    # ── Step 5: Train ────────────────────────────────────────────────
    print("\n[5/6] Starting training...")
    print(f"  Epochs: {train_config['num_train_epochs']}")
    print(f"  Batch size: {train_config['per_device_train_batch_size']}")
    print(f"  Gradient accumulation: {train_config['gradient_accumulation_steps']}")
    print(f"  Effective batch: {train_config['per_device_train_batch_size'] * train_config['gradient_accumulation_steps']}")
    print(f"  Learning rate: {train_config['learning_rate']}")

    train_result = trainer.train()

    # Log metrics
    metrics = train_result.metrics
    print(f"\n  Training Results:")
    print(f"    Loss: {metrics.get('train_loss', 'N/A'):.4f}")
    print(f"    Runtime: {metrics.get('train_runtime', 0):.0f}s")
    print(f"    Samples/sec: {metrics.get('train_samples_per_second', 0):.1f}")

    # Evaluate
    if eval_dataset:
        eval_metrics = trainer.evaluate()
        print(f"\n  Evaluation Results:")
        print(f"    Eval Loss: {eval_metrics.get('eval_loss', 'N/A'):.4f}")

    # Save model
    trainer.save_model()
    print(f"  ✅ Model saved to {train_config['output_dir']}")

    # ── Step 6: Export to GGUF ───────────────────────────────────────
    if export_config.get("gguf_quantizations"):
        print("\n[6/6] Exporting to GGUF format...")

        if export_config.get("merge_adapters", True):
            model.save_pretrained_merged(
                train_config["output_dir"] + "/merged",
                tokenizer,
                save_method="merged_16bit",
            )

        for quant in export_config["gguf_quantizations"]:
            gguf_path = f"{train_config['output_dir']}/gguf"
            print(f"  Exporting {quant}...")
            model.save_pretrained_gguf(
                gguf_path,
                tokenizer,
                quantization_method=quant,
            )
            print(f"  ✅ GGUF ({quant}) → {gguf_path}")

    print(f"\n{'='*60}")
    print(f"  Training complete!")
    print(f"  Output: {train_config['output_dir']}")
    print(f"{'='*60}")

    # Save training report
    report = {
        "config": config_path,
        "model": model_config["base_model"],
        "metrics": {k: float(v) if isinstance(v, (int, float)) else str(v) for k, v in metrics.items()},
        "output_dir": train_config["output_dir"],
    }
    report_path = Path(train_config["output_dir"]) / "training_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Fashion AI Model Finetuning")
    parser.add_argument("--config", required=True, help="Path to YAML training config")
    args = parser.parse_args()

    if not Path(args.config).exists():
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    train(args.config)


if __name__ == "__main__":
    main()
