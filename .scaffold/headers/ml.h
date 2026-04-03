// .scaffold/headers/ml.h
// Machine learning pipeline contract.
// Declares the ML workflow: data → model → train → eval → deploy.

#ifndef ML_H
#define ML_H

#include "project.h"
#include "deps.h"

// ─── Framework ───────────────────────────────────────────────────────

#ml_framework {
    name: "{{ml.framework}}",       // pytorch, tensorflow, jax
    version: "",
    device: "{{ml.default_device}}" // auto, cpu, cuda, mps
}

// ─── Data Pipeline ───────────────────────────────────────────────────
// How data flows from raw → processed → batched → model

#data_pipeline {
    raw_dir:       "{{ml.data_dir}}/raw",
    processed_dir: "{{ml.data_dir}}/processed",
    loader:        "ml/datasets/dataloader.py",
    transforms: [
        // "normalize",
        // "augment",
        // "tokenize"
    ]
}

// ─── Model Architecture ─────────────────────────────────────────────
// Available model templates in ml/models/

#models {
    base:        "ml/models/base_model.py",     // nn.Module base
    classifier:  "ml/models/classifier.py",     // Classification head
    transformer: "ml/models/transformer.py",    // Transformer block
    cnn:         "ml/models/cnn.py",            // Convolutional net
    // Add custom architectures as needed
}

// ─── Training ────────────────────────────────────────────────────────

#training {
    trainer:        "ml/training/trainer.py",
    config:         "ml/training/config.toml",
    checkpoint_dir: "{{ml.checkpoint_dir}}",
    log_dir:        "{{ml.log_dir}}",
    logger:         "tensorboard",      // "tensorboard", "wandb", "mlflow"
}

// ─── Evaluation ──────────────────────────────────────────────────────

#evaluation {
    evaluator: "ml/training/evaluate.py",
    metrics: [
        // "accuracy",
        // "loss",
        // "f1",
        // "precision",
        // "recall"
    ]
}

// ─── Deployment ──────────────────────────────────────────────────────

#deployment {
    format: "",         // "onnx", "torchscript", "tflite", "coreml"
    target: "",         // "server", "mobile", "edge", "browser"
    quantize: false
}

#endif // ML_H
