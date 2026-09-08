"""
Deterministic skill extraction via regex + canonical dictionary.
No LLM inference — only explicit phrase matching with word boundaries.

Design principle: specific beats generic.
  - "AWS SageMaker" is its own entry, not an alias of "AWS"
  - "LoRA" is its own entry, not an alias of "Fine-tuning"
  - "medspaCy" is its own entry, not an alias of "Clinical NLP"
This gives meaningful frequency signals instead of blurred buckets.
"""

import re
import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class SkillMatch(NamedTuple):
    canonical: str
    category: str
    subcategory: str


# ---------------------------------------------------------------------------
# Canonical Skills Dictionary
# key   = lowercase primary term
# value = {canonical, category, subcategory, aliases}
#
# Rules:
#  - Each specific tool/service gets its OWN entry
#  - Broad parent (e.g. "AWS") only aliases generic phrases like
#    "amazon web services" — NOT specific services
#  - Aliases must be unambiguous (avoid single common words)
# ---------------------------------------------------------------------------

SKILLS_DICT: dict[str, dict] = {

    # =========================================================
    # LLM FRAMEWORKS & ORCHESTRATION
    # =========================================================
    "langchain": {
        "canonical": "LangChain", "category": "LLM Stack", "subcategory": "Orchestration",
        "aliases": ["lang chain", "lang-chain"],
    },
    "langgraph": {
        "canonical": "LangGraph", "category": "LLM Stack", "subcategory": "Orchestration",
        "aliases": ["lang graph", "lang-graph"],
    },
    "langsmith": {
        "canonical": "LangSmith", "category": "LLM Stack", "subcategory": "Observability",
        "aliases": ["lang smith"],
    },
    "llamaindex": {
        "canonical": "LlamaIndex", "category": "LLM Stack", "subcategory": "Orchestration",
        "aliases": ["llama index", "llama-index", "gpt index"],
    },
    "dspy": {
        "canonical": "DSPy", "category": "LLM Stack", "subcategory": "Orchestration",
        "aliases": [],
    },
    "haystack": {
        "canonical": "Haystack", "category": "LLM Stack", "subcategory": "Orchestration",
        "aliases": ["deepset haystack"],
    },
    "semantic kernel": {
        "canonical": "Semantic Kernel", "category": "LLM Stack", "subcategory": "Orchestration",
        "aliases": ["microsoft semantic kernel"],
    },
    "instructor": {
        "canonical": "Instructor", "category": "LLM Stack", "subcategory": "Structured Output",
        "aliases": [],
    },
    "guardrails ai": {
        "canonical": "Guardrails AI", "category": "LLM Stack", "subcategory": "Safety",
        "aliases": ["guardrails", "guardrails-ai"],
    },
    "autogen": {
        "canonical": "AutoGen", "category": "LLM Stack", "subcategory": "Multi-Agent",
        "aliases": ["microsoft autogen", "auto-gen"],
    },
    "crewai": {
        "canonical": "CrewAI", "category": "LLM Stack", "subcategory": "Multi-Agent",
        "aliases": ["crew ai", "crew-ai"],
    },
    "pydantic ai": {
        "canonical": "Pydantic AI", "category": "LLM Stack", "subcategory": "Structured Output",
        "aliases": ["pydantic-ai"],
    },

    # =========================================================
    # LLM TECHNIQUES
    # =========================================================
    "rag": {
        "canonical": "RAG", "category": "LLM Stack", "subcategory": "Retrieval",
        "aliases": [
            "retrieval augmented generation", "retrieval-augmented generation",
            "rag pipeline", "rag system", "rag framework", "rag architecture",
            "retrieval-augmented", "retrieval augment",
        ],
    },
    "agentic rag": {
        "canonical": "Agentic RAG", "category": "LLM Stack", "subcategory": "Retrieval",
        "aliases": ["agentic retrieval", "agent-based rag"],
    },
    "graphrag": {
        "canonical": "GraphRAG", "category": "LLM Stack", "subcategory": "Retrieval",
        "aliases": ["graph rag", "graph-based rag", "knowledge graph rag"],
    },
    "prompt engineering": {
        "canonical": "Prompt Engineering", "category": "LLM Stack", "subcategory": "Techniques",
        "aliases": [
            "prompt design", "prompt optimization", "few-shot prompting",
            "chain-of-thought", "chain of thought", "cot prompting",
            "system prompt", "prompt templates",
        ],
    },
    "function calling": {
        "canonical": "Function Calling", "category": "LLM Stack", "subcategory": "Techniques",
        "aliases": ["tool calling", "tool use", "tool call"],
    },
    "multi-agent systems": {
        "canonical": "Multi-Agent Systems", "category": "LLM Stack", "subcategory": "Architecture",
        "aliases": ["multi agent", "agentic systems", "agentic workflows", "agent orchestration", "ai agents"],
    },
    "context window": {
        "canonical": "Context Window Management", "category": "LLM Stack", "subcategory": "Techniques",
        "aliases": ["long context", "context compression", "context management", "long-context"],
    },
    "embeddings": {
        "canonical": "Embeddings", "category": "LLM Stack", "subcategory": "Retrieval",
        "aliases": ["text embeddings", "sentence embeddings", "vector embeddings", "embedding models", "semantic embeddings"],
    },
    "vector search": {
        "canonical": "Vector Search", "category": "LLM Stack", "subcategory": "Retrieval",
        "aliases": [
            "semantic search", "dense retrieval", "approximate nearest neighbor",
            "ann search", "knn search", "nearest neighbor search", "similarity search",
        ],
    },
    "reranking": {
        "canonical": "Reranking", "category": "LLM Stack", "subcategory": "Retrieval",
        "aliases": ["re-ranking", "cross-encoder reranking", "cohere rerank", "reranker"],
    },
    "mcp": {
        "canonical": "Model Context Protocol", "category": "LLM Stack", "subcategory": "Protocols",
        "aliases": ["model context protocol", "mcp server", "mcp tools"],
    },
    "structured generation": {
        "canonical": "Structured Generation", "category": "LLM Stack", "subcategory": "Techniques",
        "aliases": [
            "constrained decoding", "structured output generation", "json mode",
            "guided generation", "outlines library", "grammar-based decoding",
        ],
    },
    "react agent": {
        "canonical": "ReAct", "category": "LLM Stack", "subcategory": "Techniques",
        "aliases": ["react prompting", "reason and act", "reasoning and acting"],
    },
    "synthetic data generation": {
        "canonical": "Synthetic Data Generation", "category": "LLM Stack", "subcategory": "Techniques",
        "aliases": [
            "synthetic dataset generation", "data synthesis", "synthetic training data",
            "llm data generation", "synthetic annotation",
        ],
    },

    # =========================================================
    # LLM FINE-TUNING (each technique is its own entry)
    # =========================================================
    "lora": {
        "canonical": "LoRA", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["low-rank adaptation", "low rank adaptation", "lora fine-tuning"],
    },
    "qlora": {
        "canonical": "QLoRA", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["quantized lora", "q-lora"],
    },
    "rlhf": {
        "canonical": "RLHF", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["reinforcement learning from human feedback", "rlhf training"],
    },
    "dpo": {
        "canonical": "DPO", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["direct preference optimization", "direct preference optimisation"],
    },
    "peft": {
        "canonical": "PEFT", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["parameter efficient fine-tuning", "parameter-efficient fine-tuning"],
    },
    "instruction tuning": {
        "canonical": "Instruction Tuning", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["instruction following", "supervised fine-tuning", "sft"],
    },
    "constitutional ai": {
        "canonical": "Constitutional AI / RLAIF", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["rlaif", "rl from ai feedback", "reinforcement learning from ai feedback", "constitutional ai"],
    },
    "reward modeling": {
        "canonical": "Reward Modeling", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["reward model training", "preference learning", "preference modeling"],
    },
    "knowledge distillation": {
        "canonical": "Knowledge Distillation", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["model distillation", "teacher student training", "teacher-student model"],
    },
    "orpo": {
        "canonical": "ORPO / KTO", "category": "LLM Stack", "subcategory": "Fine-tuning",
        "aliases": ["odds ratio preference optimization", "kto", "kahneman-tversky optimization", "simpo"],
    },

    # =========================================================
    # LLM EVALUATION & OBSERVABILITY
    # =========================================================
    "ragas": {
        "canonical": "RAGAS", "category": "LLM Stack", "subcategory": "Evaluation",
        "aliases": ["rag evaluation", "rag assessment"],
    },
    "arize ai": {
        "canonical": "Arize AI", "category": "LLM Stack", "subcategory": "Observability",
        "aliases": ["arize", "arize phoenix", "phoenix tracing"],
    },
    "helicone": {
        "canonical": "Helicone", "category": "LLM Stack", "subcategory": "Observability",
        "aliases": [],
    },
    "langfuse": {
        "canonical": "LangFuse", "category": "LLM Stack", "subcategory": "Observability",
        "aliases": ["langfuse tracing", "langfuse monitoring"],
    },
    "llm evaluation": {
        "canonical": "LLM Evaluation", "category": "LLM Stack", "subcategory": "Evaluation",
        "aliases": ["llm evals", "llm benchmarking", "model evaluation", "evals"],
    },
    "deepeval": {
        "canonical": "DeepEval", "category": "LLM Stack", "subcategory": "Evaluation",
        "aliases": ["deep eval"],
    },
    "trulens": {
        "canonical": "TruLens", "category": "LLM Stack", "subcategory": "Evaluation",
        "aliases": ["trulens eval"],
    },
    "promptfoo": {
        "canonical": "PromptFoo", "category": "LLM Stack", "subcategory": "Evaluation",
        "aliases": ["prompt foo", "prompt testing framework"],
    },
    "braintrust": {
        "canonical": "Braintrust", "category": "LLM Stack", "subcategory": "Evaluation",
        "aliases": [],
    },
    "giskard": {
        "canonical": "Giskard", "category": "LLM Stack", "subcategory": "Evaluation",
        "aliases": [],
    },
    "opentelemetry": {
        "canonical": "OpenTelemetry", "category": "LLM Stack", "subcategory": "Observability",
        "aliases": ["otel", "open telemetry"],
    },

    # =========================================================
    # LLM MODEL APIS & OPEN MODELS
    # =========================================================
    "openai api": {
        "canonical": "OpenAI API", "category": "LLM Stack", "subcategory": "Model APIs",
        "aliases": ["openai", "gpt-4", "gpt4", "gpt-4o", "gpt4o", "chatgpt api", "openai models", "gpt-4 api", "o1", "o3"],
    },
    "claude api": {
        "canonical": "Claude API", "category": "LLM Stack", "subcategory": "Model APIs",
        "aliases": ["anthropic api", "anthropic claude", "claude 3", "claude-3", "claude models", "claude sonnet", "claude haiku", "claude 3.5"],
    },
    "gemini api": {
        "canonical": "Gemini API", "category": "LLM Stack", "subcategory": "Model APIs",
        "aliases": ["google gemini", "gemini pro", "gemini ultra", "gemini models", "gemini 1.5", "gemini 2.0"],
    },
    "amazon bedrock": {
        "canonical": "Amazon Bedrock", "category": "LLM Stack", "subcategory": "Model APIs",
        "aliases": ["aws bedrock", "bedrock api", "bedrock models", "bedrock claude", "bedrock llm"],
    },
    "azure openai": {
        "canonical": "Azure OpenAI", "category": "LLM Stack", "subcategory": "Model APIs",
        "aliases": ["azure openai service", "azure openai api", "azure gpt"],
    },
    "llama": {
        "canonical": "LLaMA", "category": "LLM Stack", "subcategory": "Open Models",
        "aliases": ["llama 2", "llama2", "llama 3", "llama3", "meta llama", "llama models"],
    },
    "mistral": {
        "canonical": "Mistral", "category": "LLM Stack", "subcategory": "Open Models",
        "aliases": ["mistral ai", "mixtral", "mistral-7b", "mixtral-8x7b"],
    },
    "gemma": {
        "canonical": "Gemma", "category": "LLM Stack", "subcategory": "Open Models",
        "aliases": ["google gemma", "gemma 2", "gemma2"],
    },
    "phi": {
        "canonical": "Phi (Microsoft)", "category": "LLM Stack", "subcategory": "Open Models",
        "aliases": ["phi-3", "phi-4", "microsoft phi", "phi model"],
    },
    "qwen": {
        "canonical": "Qwen", "category": "LLM Stack", "subcategory": "Open Models",
        "aliases": ["qwen2", "alibaba qwen"],
    },
    "falcon": {
        "canonical": "Falcon", "category": "LLM Stack", "subcategory": "Open Models",
        "aliases": ["tii falcon", "falcon llm"],
    },
    "whisper": {
        "canonical": "Whisper", "category": "LLM Stack", "subcategory": "Open Models",
        "aliases": ["openai whisper", "whisper asr", "whisper transcription"],
    },
    "clip": {
        "canonical": "CLIP", "category": "LLM Stack", "subcategory": "Open Models",
        "aliases": ["openai clip", "contrastive language image pretraining"],
    },

    # =========================================================
    # ML / DEEP LEARNING FRAMEWORKS
    # =========================================================
    "pytorch": {
        "canonical": "PyTorch", "category": "ML/DL", "subcategory": "Frameworks",
        "aliases": ["torch", "pytorch lightning"],
    },
    "pytorch geometric": {
        "canonical": "PyTorch Geometric", "category": "ML/DL", "subcategory": "Frameworks",
        "aliases": ["pyg", "torch geometric", "graph neural network pytorch"],
    },
    "tensorflow": {
        "canonical": "TensorFlow", "category": "ML/DL", "subcategory": "Frameworks",
        "aliases": ["tf2", "tensorflow 2", "tensorflow2", "keras"],
    },
    "jax": {
        "canonical": "JAX", "category": "ML/DL", "subcategory": "Frameworks",
        "aliases": ["google jax", "jax/flax", "flax", "jax numpy"],
    },
    "scikit-learn": {
        "canonical": "Scikit-learn", "category": "ML/DL", "subcategory": "Frameworks",
        "aliases": ["sklearn", "scikit learn", "scikit_learn"],
    },
    "xgboost": {
        "canonical": "XGBoost", "category": "ML/DL", "subcategory": "Gradient Boosting",
        "aliases": ["xgb", "extreme gradient boosting"],
    },
    "lightgbm": {
        "canonical": "LightGBM", "category": "ML/DL", "subcategory": "Gradient Boosting",
        "aliases": ["light gbm", "lgbm"],
    },
    "catboost": {
        "canonical": "CatBoost", "category": "ML/DL", "subcategory": "Gradient Boosting",
        "aliases": ["cat boost"],
    },
    "hugging face": {
        "canonical": "Hugging Face", "category": "ML/DL", "subcategory": "Platforms",
        "aliases": ["huggingface", "hf transformers", "hugging face transformers", "huggingface hub", "hf hub"],
    },

    # =========================================================
    # ML TECHNIQUES & DOMAINS
    # =========================================================
    "deep learning": {
        "canonical": "Deep Learning", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["neural network", "neural networks", "deep neural network", "dnn"],
    },
    "transformers": {
        "canonical": "Transformer Architecture", "category": "ML/DL", "subcategory": "Architectures",
        "aliases": ["transformer model", "transformer architecture", "attention mechanism", "self-attention"],
    },
    "bert": {
        "canonical": "BERT", "category": "ML/DL", "subcategory": "Models",
        "aliases": ["roberta", "distilbert", "bert model", "bert-based", "bert embeddings"],
    },
    "computer vision": {
        "canonical": "Computer Vision", "category": "ML/DL", "subcategory": "Domains",
        "aliases": ["image recognition", "object detection", "image segmentation", "image classification"],
    },
    "nlp": {
        "canonical": "NLP", "category": "ML/DL", "subcategory": "Domains",
        "aliases": [
            "natural language processing", "natural language understanding", "nlu",
            "natural language generation", "nlg", "text mining", "text analytics",
        ],
    },
    "time series": {
        "canonical": "Time Series Analysis", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["time series analysis", "time series forecasting", "time-series", "temporal modeling"],
    },
    "bayesian": {
        "canonical": "Bayesian Methods", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["bayesian inference", "bayesian statistics", "probabilistic modeling", "bayesian networks"],
    },
    "causal inference": {
        "canonical": "Causal Inference", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["causal ai", "causal modeling", "counterfactual", "causal reasoning"],
    },
    "survival analysis": {
        "canonical": "Survival Analysis", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["time-to-event", "cox regression", "kaplan-meier", "hazard modeling"],
    },
    "generative ai": {
        "canonical": "Generative AI", "category": "ML/DL", "subcategory": "Domains",
        "aliases": ["genai", "gen ai", "generative models"],
    },
    "diffusion models": {
        "canonical": "Diffusion Models", "category": "ML/DL", "subcategory": "Architectures",
        "aliases": ["stable diffusion", "denoising diffusion", "ddpm", "latent diffusion"],
    },
    "multimodal": {
        "canonical": "Multimodal AI", "category": "ML/DL", "subcategory": "Domains",
        "aliases": ["multimodal learning", "vision language model", "vlm", "vision-language model", "multi-modal"],
    },
    "reinforcement learning": {
        "canonical": "Reinforcement Learning", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["rl", "deep reinforcement learning", "drl", "policy gradient", "q-learning", "ppo"],
    },
    "graph neural networks": {
        "canonical": "Graph Neural Networks", "category": "ML/DL", "subcategory": "Architectures",
        "aliases": ["gnn", "graph neural network", "graph ml", "gnns"],
    },
    "statistical modeling": {
        "canonical": "Statistical Modeling", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["regression analysis", "hypothesis testing", "statistical inference", "mixed effects model"],
    },
    "self-supervised learning": {
        "canonical": "Self-Supervised Learning", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["self supervised learning", "contrastive learning", "ssl pretraining", "masked language modeling"],
    },
    "active learning": {
        "canonical": "Active Learning", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["active learning annotation", "human in the loop labeling"],
    },
    "unet": {
        "canonical": "U-Net", "category": "ML/DL", "subcategory": "Architectures",
        "aliases": ["u-net", "u net", "unet architecture", "encoder decoder architecture"],
    },
    "vision transformer": {
        "canonical": "Vision Transformer", "category": "ML/DL", "subcategory": "Architectures",
        "aliases": ["vit", "vision-transformer", "image transformer"],
    },
    "yolo": {
        "canonical": "YOLO", "category": "ML/DL", "subcategory": "Architectures",
        "aliases": ["yolov8", "yolov9", "yolo detection", "ultralytics yolo"],
    },
    "propensity score": {
        "canonical": "Propensity Score Matching", "category": "ML/DL", "subcategory": "Techniques",
        "aliases": ["propensity score matching", "psm", "inverse probability weighting", "ipw"],
    },

    # =========================================================
    # INFERENCE OPTIMIZATION & SERVING
    # =========================================================
    "vllm": {
        "canonical": "vLLM", "category": "Inference", "subcategory": "Serving Frameworks",
        "aliases": ["v-llm", "vllm serving", "vllm inference"],
    },
    "triton inference server": {
        "canonical": "Triton Inference Server", "category": "Inference", "subcategory": "Serving Frameworks",
        "aliases": ["nvidia triton", "triton server", "triton serving"],
    },
    "torchserve": {
        "canonical": "TorchServe", "category": "Inference", "subcategory": "Serving Frameworks",
        "aliases": ["torch serve", "pytorch serve"],
    },
    "bentoml": {
        "canonical": "BentoML", "category": "Inference", "subcategory": "Serving Frameworks",
        "aliases": ["bento ml", "bento serving"],
    },
    "tensorrt": {
        "canonical": "TensorRT", "category": "Inference", "subcategory": "Optimization",
        "aliases": ["tensor rt", "tensorrt-llm", "trt", "trt-llm"],
    },
    "onnx": {
        "canonical": "ONNX", "category": "Inference", "subcategory": "Optimization",
        "aliases": ["open neural network exchange", "onnxruntime", "onnx runtime"],
    },
    "quantization": {
        "canonical": "Model Quantization", "category": "Inference", "subcategory": "Optimization",
        "aliases": ["int8 quantization", "int4 quantization", "model compression", "weight quantization", "bitsandbytes"],
    },
    "llama.cpp": {
        "canonical": "llama.cpp", "category": "Inference", "subcategory": "Serving Frameworks",
        "aliases": ["llamacpp", "llama cpp"],
    },
    "cuda": {
        "canonical": "CUDA", "category": "Inference", "subcategory": "GPU Programming",
        "aliases": ["cuda programming", "cuda kernels", "cuda optimization", "nvidia cuda"],
    },
    "gpu computing": {
        "canonical": "GPU Computing", "category": "Inference", "subcategory": "Hardware",
        "aliases": ["gpu cluster", "a100", "h100", "h200", "nvidia gpu", "gpu optimization", "gpu infrastructure", "accelerated computing"],
    },
    "tpu": {
        "canonical": "TPU", "category": "Inference", "subcategory": "Hardware",
        "aliases": ["tensor processing unit", "google tpu", "cloud tpu", "tpu training"],
    },

    # =========================================================
    # MLOPS / PLATFORM
    # =========================================================
    "kubernetes": {
        "canonical": "Kubernetes", "category": "MLOps", "subcategory": "Orchestration",
        "aliases": ["k8s", "kube"],
    },
    "helm": {
        "canonical": "Helm", "category": "MLOps", "subcategory": "Kubernetes Tools",
        "aliases": ["helm charts", "helm chart"],
    },
    "argocd": {
        "canonical": "ArgoCD", "category": "MLOps", "subcategory": "GitOps",
        "aliases": ["argo cd", "argo-cd"],
    },
    "argo workflows": {
        "canonical": "Argo Workflows", "category": "MLOps", "subcategory": "Orchestration",
        "aliases": ["argo workflow"],
    },
    "docker": {
        "canonical": "Docker", "category": "MLOps", "subcategory": "Containerization",
        "aliases": ["dockerfile", "docker container", "docker-compose", "containerization"],
    },
    "apache airflow": {
        "canonical": "Apache Airflow", "category": "MLOps", "subcategory": "Orchestration",
        "aliases": ["airflow", "airflow dags", "airflow pipeline", "airflow dag"],
    },
    "prefect": {
        "canonical": "Prefect", "category": "MLOps", "subcategory": "Orchestration",
        "aliases": ["prefect cloud", "prefect orion"],
    },
    "dagster": {
        "canonical": "Dagster", "category": "MLOps", "subcategory": "Orchestration",
        "aliases": [],
    },
    "temporal": {
        "canonical": "Temporal", "category": "MLOps", "subcategory": "Orchestration",
        "aliases": ["temporal workflow", "temporal.io"],
    },
    "mlflow": {
        "canonical": "MLflow", "category": "MLOps", "subcategory": "Experiment Tracking",
        "aliases": ["ml flow", "mlflow tracking", "mlflow registry"],
    },
    "kubeflow": {
        "canonical": "Kubeflow", "category": "MLOps", "subcategory": "ML Platform",
        "aliases": ["kubeflow pipelines", "kfp"],
    },
    "wandb": {
        "canonical": "Weights & Biases", "category": "MLOps", "subcategory": "Experiment Tracking",
        "aliases": ["weights and biases", "weights & biases", "wandb"],
    },
    "dvc": {
        "canonical": "DVC", "category": "MLOps", "subcategory": "Data Versioning",
        "aliases": ["data version control"],
    },
    "feast": {
        "canonical": "Feast", "category": "MLOps", "subcategory": "Feature Stores",
        "aliases": ["feast feature store"],
    },
    "tecton": {
        "canonical": "Tecton", "category": "MLOps", "subcategory": "Feature Stores",
        "aliases": ["tecton feature store"],
    },
    "feature store": {
        "canonical": "Feature Store", "category": "MLOps", "subcategory": "Feature Stores",
        "aliases": ["feature stores", "feature platform"],
    },
    "terraform": {
        "canonical": "Terraform", "category": "MLOps", "subcategory": "Infrastructure as Code",
        "aliases": ["hashicorp terraform", "terraform iac"],
    },
    "pulumi": {
        "canonical": "Pulumi", "category": "MLOps", "subcategory": "Infrastructure as Code",
        "aliases": ["pulumi iac", "pulumi infrastructure"],
    },
    "ansible": {
        "canonical": "Ansible", "category": "MLOps", "subcategory": "Infrastructure as Code",
        "aliases": ["ansible playbooks", "ansible automation"],
    },
    "github actions": {
        "canonical": "GitHub Actions", "category": "MLOps", "subcategory": "CI/CD",
        "aliases": ["gh actions", "github ci", "github workflows"],
    },
    "ci/cd": {
        "canonical": "CI/CD", "category": "MLOps", "subcategory": "CI/CD",
        "aliases": ["cicd", "continuous integration", "continuous deployment", "continuous delivery", "gitlab ci", "jenkins"],
    },
    "seldon": {
        "canonical": "Seldon Core", "category": "MLOps", "subcategory": "Model Serving",
        "aliases": ["seldon core", "seldon deploy"],
    },
    "datadog": {
        "canonical": "Datadog", "category": "MLOps", "subcategory": "Monitoring",
        "aliases": [],
    },
    "prometheus": {
        "canonical": "Prometheus", "category": "MLOps", "subcategory": "Monitoring",
        "aliases": ["prometheus monitoring"],
    },
    "grafana": {
        "canonical": "Grafana", "category": "MLOps", "subcategory": "Monitoring",
        "aliases": ["grafana dashboard"],
    },
    "model monitoring": {
        "canonical": "Model Monitoring", "category": "MLOps", "subcategory": "Monitoring",
        "aliases": ["ml monitoring", "data drift", "concept drift", "model observability", "model performance monitoring"],
    },
    "istio": {
        "canonical": "Istio", "category": "MLOps", "subcategory": "Service Mesh",
        "aliases": ["istio service mesh"],
    },
    "ray": {
        "canonical": "Ray", "category": "MLOps", "subcategory": "Distributed Computing",
        "aliases": ["ray framework", "anyscale ray"],
    },
    "ray serve": {
        "canonical": "Ray Serve", "category": "MLOps", "subcategory": "Model Serving",
        "aliases": ["rayserve"],
    },
    "ray train": {
        "canonical": "Ray Train", "category": "MLOps", "subcategory": "Distributed Training",
        "aliases": ["raytrain"],
    },
    "distributed training": {
        "canonical": "Distributed Training", "category": "MLOps", "subcategory": "Distributed Computing",
        "aliases": ["distributed ml", "data parallel", "model parallel", "ddp", "fsdp", "fully sharded data parallel", "horovod", "deepspeed"],
    },
    "deepspeed": {
        "canonical": "DeepSpeed", "category": "MLOps", "subcategory": "Distributed Training",
        "aliases": ["microsoft deepspeed", "deep speed"],
    },
    "federated learning": {
        "canonical": "Federated Learning", "category": "MLOps", "subcategory": "Privacy-Preserving ML",
        "aliases": ["federated ml", "federated training", "privacy-preserving ml", "on-device training", "federated machine learning"],
    },
    "differential privacy": {
        "canonical": "Differential Privacy", "category": "MLOps", "subcategory": "Privacy-Preserving ML",
        "aliases": ["dp-sgd", "noise injection privacy", "formal privacy guarantees", "opacus"],
    },

    # =========================================================
    # AWS — specific services only (generic "AWS" handled separately)
    # =========================================================
    "aws": {
        "canonical": "AWS", "category": "Cloud", "subcategory": "Providers",
        "aliases": ["amazon web services", "amazon cloud", "aws cloud"],
    },
    "aws sagemaker": {
        "canonical": "AWS SageMaker", "category": "Cloud", "subcategory": "AWS ML Services",
        "aliases": ["sagemaker", "amazon sagemaker", "sagemaker studio", "sagemaker pipelines", "sagemaker endpoints"],
    },
    "aws glue": {
        "canonical": "AWS Glue", "category": "Cloud", "subcategory": "AWS Data Services",
        "aliases": ["amazon glue", "glue etl", "glue catalog", "glue data catalog"],
    },
    "amazon redshift": {
        "canonical": "Amazon Redshift", "category": "Cloud", "subcategory": "AWS Data Services",
        "aliases": ["aws redshift", "redshift spectrum"],
    },
    "amazon s3": {
        "canonical": "Amazon S3", "category": "Cloud", "subcategory": "AWS Storage",
        "aliases": ["aws s3", "s3 bucket", "s3 storage"],
    },
    "amazon kinesis": {
        "canonical": "Amazon Kinesis", "category": "Cloud", "subcategory": "AWS Streaming",
        "aliases": ["aws kinesis", "kinesis streams", "kinesis data streams", "kinesis firehose"],
    },
    "amazon eks": {
        "canonical": "Amazon EKS", "category": "Cloud", "subcategory": "AWS Compute",
        "aliases": ["aws eks", "elastic kubernetes service"],
    },
    "aws lambda": {
        "canonical": "AWS Lambda", "category": "Cloud", "subcategory": "AWS Compute",
        "aliases": ["amazon lambda", "lambda function", "aws serverless"],
    },
    "aws step functions": {
        "canonical": "AWS Step Functions", "category": "Cloud", "subcategory": "AWS Orchestration",
        "aliases": ["step functions", "aws stepfunctions"],
    },
    "aws batch": {
        "canonical": "AWS Batch", "category": "Cloud", "subcategory": "AWS Compute",
        "aliases": ["amazon batch"],
    },
    "amazon athena": {
        "canonical": "Amazon Athena", "category": "Cloud", "subcategory": "AWS Data Services",
        "aliases": ["aws athena", "athena sql"],
    },
    "aws iam": {
        "canonical": "AWS IAM", "category": "Cloud", "subcategory": "AWS Security",
        "aliases": ["iam policies", "iam roles", "aws identity and access management"],
    },

    # =========================================================
    # AZURE — specific services
    # =========================================================
    "azure": {
        "canonical": "Azure", "category": "Cloud", "subcategory": "Providers",
        "aliases": ["microsoft azure", "azure cloud"],
    },
    "azure machine learning": {
        "canonical": "Azure Machine Learning", "category": "Cloud", "subcategory": "Azure ML Services",
        "aliases": ["azure ml", "azure mlops", "azureml"],
    },
    "azure data factory": {
        "canonical": "Azure Data Factory", "category": "Cloud", "subcategory": "Azure Data Services",
        "aliases": ["adf", "azure adf", "azure etl"],
    },
    "azure databricks": {
        "canonical": "Azure Databricks", "category": "Cloud", "subcategory": "Azure Data Services",
        "aliases": [],
    },
    "azure kubernetes service": {
        "canonical": "Azure Kubernetes Service", "category": "Cloud", "subcategory": "Azure Compute",
        "aliases": ["aks", "azure aks"],
    },
    "azure blob storage": {
        "canonical": "Azure Blob Storage", "category": "Cloud", "subcategory": "Azure Storage",
        "aliases": ["azure storage", "azure blob"],
    },
    "azure devops": {
        "canonical": "Azure DevOps", "category": "Cloud", "subcategory": "Azure Developer Tools",
        "aliases": ["azure pipelines", "azure devops pipelines"],
    },
    "azure synapse": {
        "canonical": "Azure Synapse Analytics", "category": "Cloud", "subcategory": "Azure Data Services",
        "aliases": ["azure synapse", "synapse analytics"],
    },

    # =========================================================
    # GCP — specific services
    # =========================================================
    "gcp": {
        "canonical": "GCP", "category": "Cloud", "subcategory": "Providers",
        "aliases": ["google cloud", "google cloud platform", "gcloud"],
    },
    "vertex ai": {
        "canonical": "Vertex AI", "category": "Cloud", "subcategory": "GCP ML Services",
        "aliases": ["google vertex ai", "vertex ai platform", "vertex ai pipelines", "vertex ai workbench"],
    },
    "bigquery": {
        "canonical": "BigQuery", "category": "Cloud", "subcategory": "GCP Data Services",
        "aliases": ["google bigquery", "bq", "bigquery ml"],
    },
    "cloud run": {
        "canonical": "Google Cloud Run", "category": "Cloud", "subcategory": "GCP Compute",
        "aliases": ["gcp cloud run"],
    },
    "google kubernetes engine": {
        "canonical": "Google Kubernetes Engine", "category": "Cloud", "subcategory": "GCP Compute",
        "aliases": ["gke"],
    },
    "cloud composer": {
        "canonical": "Cloud Composer", "category": "Cloud", "subcategory": "GCP Orchestration",
        "aliases": ["google cloud composer", "gcp airflow"],
    },
    "google dataflow": {
        "canonical": "Google Dataflow", "category": "Cloud", "subcategory": "GCP Streaming",
        "aliases": ["gcp dataflow", "apache beam dataflow", "dataflow pipeline"],
    },
    "google pubsub": {
        "canonical": "Google Pub/Sub", "category": "Cloud", "subcategory": "GCP Streaming",
        "aliases": ["pub/sub", "pubsub", "google pub sub"],
    },

    # =========================================================
    # DATA ENGINEERING
    # =========================================================
    "sql": {
        "canonical": "SQL", "category": "Data Engineering", "subcategory": "Query Languages",
        "aliases": ["structured query language", "t-sql", "pl/sql", "relational database"],
    },
    "postgresql": {
        "canonical": "PostgreSQL", "category": "Data Engineering", "subcategory": "Databases",
        "aliases": ["postgres", "psql", "postgre sql"],
    },
    "mongodb": {
        "canonical": "MongoDB", "category": "Data Engineering", "subcategory": "Databases",
        "aliases": ["mongo db", "mongo", "document database", "mongodb atlas"],
    },
    "mysql": {
        "canonical": "MySQL / MariaDB", "category": "Data Engineering", "subcategory": "Databases",
        "aliases": ["mysql", "mariadb", "mysql database"],
    },
    "cassandra": {
        "canonical": "Apache Cassandra", "category": "Data Engineering", "subcategory": "Databases",
        "aliases": ["cassandra db", "cassandra database", "datastax cassandra"],
    },
    "clickhouse": {
        "canonical": "ClickHouse", "category": "Data Engineering", "subcategory": "Databases",
        "aliases": ["click house"],
    },
    "apache spark": {
        "canonical": "Apache Spark", "category": "Data Engineering", "subcategory": "Processing",
        "aliases": ["spark", "pyspark", "spark streaming", "spark sql", "spark dataframe"],
    },
    "databricks": {
        "canonical": "Databricks", "category": "Data Engineering", "subcategory": "Platforms",
        "aliases": ["databricks lakehouse", "databricks platform"],
    },
    "delta lake": {
        "canonical": "Delta Lake", "category": "Data Engineering", "subcategory": "Table Formats",
        "aliases": ["delta tables", "delta format"],
    },
    "apache iceberg": {
        "canonical": "Apache Iceberg", "category": "Data Engineering", "subcategory": "Table Formats",
        "aliases": ["iceberg tables", "iceberg format"],
    },
    "apache hudi": {
        "canonical": "Apache Hudi", "category": "Data Engineering", "subcategory": "Table Formats",
        "aliases": ["hudi", "hudi tables"],
    },
    "snowflake": {
        "canonical": "Snowflake", "category": "Data Engineering", "subcategory": "Data Warehouses",
        "aliases": [],
    },
    "trino": {
        "canonical": "Trino / Presto", "category": "Data Engineering", "subcategory": "Query Engines",
        "aliases": ["presto", "prestodb", "trino sql", "trino query", "prestosql"],
    },
    "duckdb": {
        "canonical": "DuckDB", "category": "Data Engineering", "subcategory": "Query Engines",
        "aliases": ["duck db"],
    },
    "apache hive": {
        "canonical": "Apache Hive", "category": "Data Engineering", "subcategory": "Query Engines",
        "aliases": ["hive metastore", "hive sql", "hiveql"],
    },
    "apache kafka": {
        "canonical": "Apache Kafka", "category": "Data Engineering", "subcategory": "Streaming",
        "aliases": ["kafka", "kafka streaming", "confluent kafka", "kafka topics"],
    },
    "apache flink": {
        "canonical": "Apache Flink", "category": "Data Engineering", "subcategory": "Streaming",
        "aliases": ["flink", "flink streaming", "flink sql"],
    },
    "dbt": {
        "canonical": "dbt", "category": "Data Engineering", "subcategory": "Transformation",
        "aliases": ["data build tool", "dbt cloud", "dbt core", "dbt models"],
    },
    "fivetran": {
        "canonical": "Fivetran", "category": "Data Engineering", "subcategory": "Data Integration",
        "aliases": ["fivetran connector", "fivetran pipeline"],
    },
    "airbyte": {
        "canonical": "Airbyte", "category": "Data Engineering", "subcategory": "Data Integration",
        "aliases": ["airbyte connector"],
    },
    "great expectations": {
        "canonical": "Great Expectations", "category": "Data Engineering", "subcategory": "Data Quality",
        "aliases": ["gx", "great expectations validation"],
    },
    "pandas": {
        "canonical": "Pandas", "category": "Data Engineering", "subcategory": "Libraries",
        "aliases": ["pandas dataframe"],
    },
    "numpy": {
        "canonical": "NumPy", "category": "Data Engineering", "subcategory": "Libraries",
        "aliases": ["numpy array"],
    },
    "polars": {
        "canonical": "Polars", "category": "Data Engineering", "subcategory": "Libraries",
        "aliases": [],
    },
    "scipy": {
        "canonical": "SciPy", "category": "Data Engineering", "subcategory": "Libraries",
        "aliases": ["scipy library", "scipy stats"],
    },
    "statsmodels": {
        "canonical": "Statsmodels", "category": "Data Engineering", "subcategory": "Libraries",
        "aliases": ["stats models"],
    },
    "data pipeline": {
        "canonical": "Data Pipelines", "category": "Data Engineering", "subcategory": "Architecture",
        "aliases": ["etl", "elt", "data ingestion", "data orchestration", "batch processing"],
    },

    # =========================================================
    # VECTOR DATABASES & SEARCH (each DB is its own entry)
    # =========================================================
    "pinecone": {
        "canonical": "Pinecone", "category": "Vector Databases", "subcategory": "Managed",
        "aliases": ["pinecone vector db", "pinecone index"],
    },
    "weaviate": {
        "canonical": "Weaviate", "category": "Vector Databases", "subcategory": "Open Source",
        "aliases": [],
    },
    "chroma": {
        "canonical": "ChromaDB", "category": "Vector Databases", "subcategory": "Open Source",
        "aliases": ["chromadb", "chroma db"],
    },
    "qdrant": {
        "canonical": "Qdrant", "category": "Vector Databases", "subcategory": "Open Source",
        "aliases": [],
    },
    "milvus": {
        "canonical": "Milvus", "category": "Vector Databases", "subcategory": "Open Source",
        "aliases": ["zilliz", "milvus vector db"],
    },
    "faiss": {
        "canonical": "FAISS", "category": "Vector Databases", "subcategory": "Libraries",
        "aliases": ["facebook ai similarity search"],
    },
    "pgvector": {
        "canonical": "pgvector", "category": "Vector Databases", "subcategory": "Libraries",
        "aliases": ["pg vector", "postgres vector", "postgresql vector"],
    },
    "opensearch": {
        "canonical": "OpenSearch", "category": "Vector Databases", "subcategory": "Search Engines",
        "aliases": ["aws opensearch", "open search"],
    },
    "elasticsearch": {
        "canonical": "Elasticsearch", "category": "Vector Databases", "subcategory": "Search Engines",
        "aliases": ["elastic search", "elastic stack"],
    },
    "redis": {
        "canonical": "Redis", "category": "Vector Databases", "subcategory": "Caching",
        "aliases": ["redis cache", "redis vector", "redis stack", "redis search"],
    },
    "neo4j": {
        "canonical": "Neo4j", "category": "Vector Databases", "subcategory": "Graph Databases",
        "aliases": ["graph database", "knowledge graph database"],
    },

    # =========================================================
    # HEALTHCARE — interoperability & compliance standards
    # =========================================================
    "fhir": {
        "canonical": "FHIR", "category": "Healthcare", "subcategory": "Interoperability Standards",
        "aliases": ["hl7 fhir", "fhir r4", "fhir api", "fast healthcare interoperability resources", "fhir resources"],
    },
    "smart on fhir": {
        "canonical": "SMART on FHIR", "category": "Healthcare", "subcategory": "Interoperability Standards",
        "aliases": ["smart fhir", "smart app launch", "smart on fhir apps"],
    },
    "cds hooks": {
        "canonical": "CDS Hooks", "category": "Healthcare", "subcategory": "Interoperability Standards",
        "aliases": ["clinical decision support hooks", "cds-hooks"],
    },
    "hl7": {
        "canonical": "HL7", "category": "Healthcare", "subcategory": "Interoperability Standards",
        "aliases": ["hl7 v2", "hl7 v3", "health level 7"],
    },
    "omop cdm": {
        "canonical": "OMOP CDM", "category": "Healthcare", "subcategory": "Data Standards",
        "aliases": ["omop", "omop common data model", "ohdsi omop"],
    },
    "epic": {
        "canonical": "Epic EHR", "category": "Healthcare", "subcategory": "EHR Systems",
        "aliases": ["epic ehr", "epic systems", "epic emr", "epic fhir", "mychart"],
    },
    "cerner": {
        "canonical": "Cerner / Oracle Health", "category": "Healthcare", "subcategory": "EHR Systems",
        "aliases": ["cerner", "oracle cerner", "oracle health", "cerner ehr"],
    },
    "ehr": {
        "canonical": "EHR", "category": "Healthcare", "subcategory": "Data Sources",
        "aliases": [
            "electronic health record", "electronic health records", "ehr system", "ehr data",
            "electronic medical record", "emr", "electronic medical records",
        ],
    },
    "hipaa": {
        "canonical": "HIPAA", "category": "Healthcare", "subcategory": "Compliance",
        "aliases": ["hipaa compliance", "hipaa regulations", "protected health information", "phi"],
    },
    "icd-10": {
        "canonical": "ICD-10", "category": "Healthcare", "subcategory": "Medical Coding",
        "aliases": ["icd10", "icd 10", "icd-11", "icd11", "medical coding", "diagnostic coding", "cpt codes", "cpt coding"],
    },
    "snomed ct": {
        "canonical": "SNOMED CT", "category": "Healthcare", "subcategory": "Clinical Terminologies",
        "aliases": ["snomed", "snomed-ct"],
    },
    "loinc": {
        "canonical": "LOINC", "category": "Healthcare", "subcategory": "Clinical Terminologies",
        "aliases": ["loinc codes", "logical observation identifiers"],
    },
    "rxnorm": {
        "canonical": "RxNorm", "category": "Healthcare", "subcategory": "Clinical Terminologies",
        "aliases": ["rxnorm codes", "medication normalization"],
    },
    "umls": {
        "canonical": "UMLS", "category": "Healthcare", "subcategory": "Clinical Terminologies",
        "aliases": ["unified medical language system", "umls metathesaurus"],
    },

    # =========================================================
    # CLINICAL AI / NLP LIBRARIES
    # =========================================================
    "medspacy": {
        "canonical": "medspaCy", "category": "Healthcare", "subcategory": "Clinical NLP Libraries",
        "aliases": ["med spacy", "medspacy library"],
    },
    "scispacy": {
        "canonical": "scispaCy", "category": "Healthcare", "subcategory": "Clinical NLP Libraries",
        "aliases": ["sci spacy", "scientific spacy"],
    },
    "biobert": {
        "canonical": "BioBERT", "category": "Healthcare", "subcategory": "Clinical NLP Libraries",
        "aliases": ["bio bert", "biomedical bert"],
    },
    "clinical bert": {
        "canonical": "ClinicalBERT", "category": "Healthcare", "subcategory": "Clinical NLP Libraries",
        "aliases": ["clinicalbert", "clinical-bert"],
    },
    "pubmedbert": {
        "canonical": "PubMedBERT", "category": "Healthcare", "subcategory": "Clinical NLP Libraries",
        "aliases": ["pubmed bert", "biomedical language model"],
    },
    "clinical nlp": {
        "canonical": "Clinical NLP", "category": "Healthcare", "subcategory": "Techniques",
        "aliases": [
            "medical nlp", "clinical text mining", "clinical text processing",
            "medical information extraction", "clinical entity recognition",
            "clinical named entity recognition", "biomedical nlp",
        ],
    },
    "named entity recognition": {
        "canonical": "Named Entity Recognition", "category": "Healthcare", "subcategory": "Techniques",
        "aliases": ["ner", "entity extraction", "entity recognition", "clinical ner"],
    },
    "relation extraction": {
        "canonical": "Relation Extraction", "category": "Healthcare", "subcategory": "Techniques",
        "aliases": ["information extraction", "clinical relation extraction", "biomedical relation extraction"],
    },

    # =========================================================
    # CLINICAL AI APPLICATIONS
    # =========================================================
    "radiology ai": {
        "canonical": "Radiology AI", "category": "Healthcare", "subcategory": "Clinical AI",
        "aliases": ["medical imaging ai", "radiology", "ct scan ai", "mri ai", "x-ray ai", "imaging ai", "chest x-ray ai"],
    },
    "pathology ai": {
        "canonical": "Pathology AI", "category": "Healthcare", "subcategory": "Clinical AI",
        "aliases": ["computational pathology", "digital pathology", "wsi", "whole slide image", "histopathology ai"],
    },
    "clinical decision support": {
        "canonical": "Clinical Decision Support", "category": "Healthcare", "subcategory": "Clinical AI",
        "aliases": ["cds", "cdss", "clinical decision support system", "clinical ai assistant"],
    },
    "ambient ai": {
        "canonical": "Ambient AI", "category": "Healthcare", "subcategory": "Clinical AI",
        "aliases": [
            "ambient clinical intelligence", "ambient documentation", "ambient scribe",
            "ai scribe", "clinical documentation ai", "automated documentation",
        ],
    },
    "medical llm": {
        "canonical": "Medical LLM", "category": "Healthcare", "subcategory": "Clinical AI",
        "aliases": [
            "clinical llm", "healthcare llm", "medical language model",
            "clinical language model", "biomedical llm", "healthcare foundation model",
            "medpalm", "med-palm", "meditron",
        ],
    },
    "prior authorization": {
        "canonical": "Prior Authorization AI", "category": "Healthcare", "subcategory": "Clinical AI Applications",
        "aliases": [
            "prior auth", "prior authorization automation", "utilization management ai",
            "um automation", "pa automation",
        ],
    },
    "risk stratification": {
        "canonical": "Risk Stratification", "category": "Healthcare", "subcategory": "Clinical AI Applications",
        "aliases": [
            "patient risk stratification", "clinical risk scoring", "acuity scoring",
            "risk scoring model", "patient acuity",
        ],
    },
    "readmission prediction": {
        "canonical": "Readmission Prediction", "category": "Healthcare", "subcategory": "Clinical AI Applications",
        "aliases": ["hospital readmission", "30-day readmission", "readmission risk model"],
    },
    "sepsis detection": {
        "canonical": "Sepsis Detection", "category": "Healthcare", "subcategory": "Clinical AI Applications",
        "aliases": [
            "early warning system", "deterioration detection", "sepsis prediction",
            "clinical early warning", "patient deterioration",
        ],
    },
    "drug safety": {
        "canonical": "Drug Safety / Pharmacovigilance", "category": "Healthcare", "subcategory": "Clinical AI Applications",
        "aliases": [
            "pharmacovigilance", "adverse event detection", "adverse drug reaction",
            "signal detection", "safety monitoring",
        ],
    },
    "clinical summarization": {
        "canonical": "Clinical Summarization", "category": "Healthcare", "subcategory": "Clinical AI Applications",
        "aliases": [
            "medical summarization", "discharge summary ai", "clinical note summarization",
            "medical record summarization", "clinical documentation summarization",
        ],
    },
    "medical coding ai": {
        "canonical": "Medical Coding AI", "category": "Healthcare", "subcategory": "Clinical AI Applications",
        "aliases": [
            "autonomous coding", "ai-assisted coding", "computer-assisted coding",
            "cac", "automated medical coding",
        ],
    },

    # =========================================================
    # MEDICAL IMAGING TOOLS
    # =========================================================
    "monai": {
        "canonical": "MONAI", "category": "Healthcare", "subcategory": "Medical Imaging Tools",
        "aliases": ["medical open network for ai", "monai framework", "monai deploy", "monai label"],
    },
    "simpleitk": {
        "canonical": "SimpleITK", "category": "Healthcare", "subcategory": "Medical Imaging Tools",
        "aliases": ["simple itk", "sitk", "itk toolkit"],
    },
    "pydicom": {
        "canonical": "pydicom", "category": "Healthcare", "subcategory": "Medical Imaging Tools",
        "aliases": ["py-dicom", "dicom python"],
    },
    "nibabel": {
        "canonical": "NiBabel", "category": "Healthcare", "subcategory": "Medical Imaging Tools",
        "aliases": ["nibabel library", "nifti format", "nii.gz"],
    },
    "nnunet": {
        "canonical": "nnU-Net", "category": "Healthcare", "subcategory": "Medical Imaging Tools",
        "aliases": ["nnunet", "nn-unet", "nnu-net", "nnunet framework", "nnunet segmentation"],
    },
    "torchio": {
        "canonical": "TorchIO", "category": "Healthcare", "subcategory": "Medical Imaging Tools",
        "aliases": ["torch io", "torchio library"],
    },
    "medical image segmentation": {
        "canonical": "Medical Image Segmentation", "category": "Healthcare", "subcategory": "Medical Imaging Tools",
        "aliases": [
            "organ segmentation", "tumor segmentation", "lesion segmentation",
            "3d segmentation", "volumetric segmentation",
        ],
    },
    "dicom": {
        "canonical": "DICOM", "category": "Healthcare", "subcategory": "Imaging Standards",
        "aliases": ["dicom standard", "digital imaging and communications in medicine"],
    },

    # =========================================================
    # BIOINFORMATICS — specific tools (each gets its own entry)
    # =========================================================
    "bwa": {
        "canonical": "BWA / Bowtie2", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["bwa aligner", "bwa-mem", "bwa-mem2", "bowtie2", "sequence alignment tool"],
    },
    "gatk": {
        "canonical": "GATK", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["genome analysis toolkit", "gatk variant calling", "haplotypecaller", "gatk4"],
    },
    "star aligner": {
        "canonical": "STAR Aligner", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["star rna-seq", "hisat2", "rna-seq alignment"],
    },
    "samtools": {
        "canonical": "Samtools / bcftools", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["bcftools", "htslib", "bam files", "sam files", "cram files"],
    },
    "picard": {
        "canonical": "Picard Tools", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["picard toolkit", "gatk picard", "picard metrics"],
    },
    "deseq2": {
        "canonical": "DESeq2 / edgeR", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["deseq", "edger", "limma", "differential expression analysis", "differential gene expression"],
    },
    "seurat": {
        "canonical": "Seurat", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["seurat r package", "seurat single cell"],
    },
    "scanpy": {
        "canonical": "Scanpy", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["anndata", "anndata library", "scverse"],
    },
    "nextflow": {
        "canonical": "Nextflow", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["nextflow pipeline", "nf-core", "nextflow dsl2"],
    },
    "snakemake": {
        "canonical": "Snakemake", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["snakemake workflow", "snakemake pipeline"],
    },
    "biopython": {
        "canonical": "BioPython", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["bio python", "biopython library"],
    },
    "cellranger": {
        "canonical": "Cell Ranger", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["cellranger", "10x genomics cellranger", "10x cellranger"],
    },
    "bioconductor": {
        "canonical": "Bioconductor", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": ["bioconductor packages", "r bioconductor"],
    },

    # =========================================================
    # GENOMICS DATA TYPES
    # =========================================================
    "wgs": {
        "canonical": "WGS / WES", "category": "Healthcare", "subcategory": "Genomics Data",
        "aliases": [
            "whole genome sequencing", "whole exome sequencing", "wes",
            "ngs", "next generation sequencing", "targeted sequencing",
        ],
    },
    "rna-seq": {
        "canonical": "RNA-seq", "category": "Healthcare", "subcategory": "Genomics Data",
        "aliases": ["rnaseq", "rna sequencing", "transcriptomics", "bulk rna-seq", "bulk rnaseq"],
    },
    "scrna-seq": {
        "canonical": "scRNA-seq", "category": "Healthcare", "subcategory": "Genomics Data",
        "aliases": [
            "single cell rna sequencing", "single-cell rna-seq", "scrna seq",
            "single cell transcriptomics", "10x genomics single cell",
        ],
    },
    "spatial transcriptomics": {
        "canonical": "Spatial Transcriptomics", "category": "Healthcare", "subcategory": "Genomics Data",
        "aliases": ["visium", "spatial genomics", "spatial gene expression", "spatial omics"],
    },
    "variant calling": {
        "canonical": "Variant Calling", "category": "Healthcare", "subcategory": "Genomics Data",
        "aliases": [
            "snp calling", "indel calling", "somatic variant calling",
            "germline variant calling", "vcf analysis", "somatic mutations",
        ],
    },
    "gwas": {
        "canonical": "GWAS", "category": "Healthcare", "subcategory": "Genomics Data",
        "aliases": [
            "genome-wide association study", "genome wide association",
            "polygenic risk score", "prs", "gwas analysis",
        ],
    },
    "pathway analysis": {
        "canonical": "Pathway Analysis", "category": "Healthcare", "subcategory": "Bioinformatics Tools",
        "aliases": [
            "gene set enrichment analysis", "gsea", "pathway enrichment",
            "go enrichment", "gene ontology analysis", "kegg pathway",
        ],
    },
    "genomics": {
        "canonical": "Genomics", "category": "Healthcare", "subcategory": "Bioinformatics",
        "aliases": ["genomic data", "genome analysis", "multi-omics", "omics data"],
    },
    "proteomics": {
        "canonical": "Proteomics", "category": "Healthcare", "subcategory": "Bioinformatics",
        "aliases": ["protein expression", "mass spectrometry", "proteomics analysis"],
    },

    # =========================================================
    # DRUG DISCOVERY
    # =========================================================
    "alphafold": {
        "canonical": "AlphaFold", "category": "Healthcare", "subcategory": "Drug Discovery",
        "aliases": ["alphafold2", "alpha fold", "protein structure prediction", "protein folding ai"],
    },
    "rdkit": {
        "canonical": "RDKit", "category": "Healthcare", "subcategory": "Drug Discovery",
        "aliases": ["rdkit cheminformatics", "cheminformatics library"],
    },
    "molecular docking": {
        "canonical": "Molecular Docking", "category": "Healthcare", "subcategory": "Drug Discovery",
        "aliases": [
            "virtual screening", "molecular dynamics simulation", "docking simulation",
            "autodock", "vina docking", "in silico screening",
        ],
    },
    "cheminformatics": {
        "canonical": "Cheminformatics", "category": "Healthcare", "subcategory": "Drug Discovery",
        "aliases": [
            "chemical informatics", "smiles", "molecular fingerprints",
            "molecular descriptors", "drug-like properties", "chemoinformatics",
        ],
    },
    "admet": {
        "canonical": "ADMET Prediction", "category": "Healthcare", "subcategory": "Drug Discovery",
        "aliases": ["admet", "adme prediction", "toxicity prediction", "pharmacokinetics prediction", "pk prediction"],
    },
    "drug-target interaction": {
        "canonical": "Drug-Target Interaction", "category": "Healthcare", "subcategory": "Drug Discovery",
        "aliases": ["dti", "drug target prediction", "protein-ligand binding", "drug discovery ai"],
    },
    "de novo drug design": {
        "canonical": "De Novo Drug Design", "category": "Healthcare", "subcategory": "Drug Discovery",
        "aliases": ["generative chemistry", "molecular generation", "de novo design"],
    },

    # =========================================================
    # CLINICAL TRIALS & REGULATORY
    # =========================================================
    "cdisc": {
        "canonical": "CDISC / SDTM", "category": "Healthcare", "subcategory": "Clinical Trial Standards",
        "aliases": ["cdisc", "sdtm", "adam", "cdisc standards", "study data tabulation model", "analysis data model"],
    },
    "fda regulatory": {
        "canonical": "FDA Regulatory", "category": "Healthcare", "subcategory": "Regulatory",
        "aliases": [
            "fda clearance", "510k", "510(k)", "de novo pathway", "pma",
            "samd", "software as medical device", "premarket approval", "fda submission",
        ],
    },
    "iso 13485": {
        "canonical": "ISO 13485 / IEC 62304", "category": "Healthcare", "subcategory": "Regulatory",
        "aliases": [
            "iso 13485", "iec 62304", "medical device software", "qms medical",
            "quality management system medical", "iso13485",
        ],
    },
    "clinical trials": {
        "canonical": "Clinical Trials", "category": "Healthcare", "subcategory": "Clinical Trials",
        "aliases": [
            "randomized controlled trial", "rct", "phase i trial", "phase ii trial",
            "phase iii trial", "clinical study design", "investigational study",
        ],
    },

    # =========================================================
    # REAL WORLD EVIDENCE & CLAIMS
    # =========================================================
    "real world evidence": {
        "canonical": "Real World Evidence", "category": "Healthcare", "subcategory": "Analytics",
        "aliases": ["rwe", "real-world evidence", "real world data", "rwd", "real-world data"],
    },
    "claims data": {
        "canonical": "Claims Data", "category": "Healthcare", "subcategory": "Data Sources",
        "aliases": [
            "insurance claims", "medical claims", "pharmacy claims",
            "administrative claims", "payer data", "claims analytics",
        ],
    },
    "hedis": {
        "canonical": "HEDIS", "category": "Healthcare", "subcategory": "Analytics",
        "aliases": ["hedis measures", "ncqa hedis", "quality measures", "star ratings"],
    },
    "sdoh": {
        "canonical": "Social Determinants of Health", "category": "Healthcare", "subcategory": "Analytics",
        "aliases": ["sdoh", "social determinants of health", "social drivers of health"],
    },
    "population health": {
        "canonical": "Population Health Analytics", "category": "Healthcare", "subcategory": "Analytics",
        "aliases": ["population health management", "population health analytics", "public health ai"],
    },

    # =========================================================
    # HEALTHCARE PRIVACY & SYNTHETIC DATA
    # =========================================================
    "de-identification": {
        "canonical": "De-identification", "category": "Healthcare", "subcategory": "Privacy",
        "aliases": [
            "deidentification", "phi removal", "patient data anonymization",
            "data anonymization", "data pseudonymization", "deid",
        ],
    },
    "synthetic health data": {
        "canonical": "Synthetic Health Data", "category": "Healthcare", "subcategory": "Privacy",
        "aliases": [
            "synthea", "synthetic patient data", "synthetic ehr data",
            "synthetic clinical data", "synthetic medical data",
        ],
    },

    # =========================================================
    # PROGRAMMING LANGUAGES
    # =========================================================
    "python": {
        "canonical": "Python", "category": "Programming", "subcategory": "Languages",
        "aliases": ["python3", "python 3"],
    },
    "r programming": {
        "canonical": "R", "category": "Programming", "subcategory": "Languages",
        "aliases": ["r language", "r statistical software", "rstudio", "tidyverse", "ggplot2", "dplyr", "r programming language"],
    },
    "julia": {
        "canonical": "Julia", "category": "Programming", "subcategory": "Languages",
        "aliases": ["julia lang", "julia programming"],
    },
    "rust": {
        "canonical": "Rust", "category": "Programming", "subcategory": "Languages",
        "aliases": ["rust lang", "rust programming"],
    },
    "golang": {
        "canonical": "Go", "category": "Programming", "subcategory": "Languages",
        "aliases": ["go lang", "golang"],
    },
    "java": {
        "canonical": "Java", "category": "Programming", "subcategory": "Languages",
        "aliases": ["java programming", "jvm", "spring boot"],
    },
    "scala": {
        "canonical": "Scala", "category": "Programming", "subcategory": "Languages",
        "aliases": [],
    },
    "c++": {
        "canonical": "C++", "category": "Programming", "subcategory": "Languages",
        "aliases": ["cpp", "c plus plus"],
    },
    "typescript": {
        "canonical": "TypeScript", "category": "Programming", "subcategory": "Languages",
        "aliases": [],
    },
    "bash scripting": {
        "canonical": "Bash / Shell Scripting", "category": "Programming", "subcategory": "Languages",
        "aliases": ["shell scripting", "bash script", "shell script", "unix scripting", "zsh scripting"],
    },

    # =========================================================
    # WEB / API FRAMEWORKS
    # =========================================================
    "fastapi": {
        "canonical": "FastAPI", "category": "Programming", "subcategory": "API Frameworks",
        "aliases": ["fast api", "fast-api"],
    },
    "flask": {
        "canonical": "Flask", "category": "Programming", "subcategory": "API Frameworks",
        "aliases": ["flask api", "flask framework"],
    },
    "django": {
        "canonical": "Django", "category": "Programming", "subcategory": "API Frameworks",
        "aliases": ["django rest framework", "drf"],
    },
    "pydantic": {
        "canonical": "Pydantic", "category": "Programming", "subcategory": "Libraries",
        "aliases": ["pydantic models", "pydantic v2"],
    },
    "grpc": {
        "canonical": "gRPC", "category": "Programming", "subcategory": "API Protocols",
        "aliases": ["protocol buffers", "protobuf", "grpc api"],
    },
    "rest api": {
        "canonical": "REST API", "category": "Programming", "subcategory": "API Protocols",
        "aliases": ["restful api", "restful", "api development"],
    },

    # =========================================================
    # GOVERNANCE / RESPONSIBLE AI
    # =========================================================
    "ai safety": {
        "canonical": "AI Safety", "category": "Governance", "subcategory": "Responsible AI",
        "aliases": ["responsible ai", "ai alignment", "ai ethics", "ai bias", "model bias", "ai governance", "trustworthy ai"],
    },
    "explainability": {
        "canonical": "Explainability / XAI", "category": "Governance", "subcategory": "Responsible AI",
        "aliases": ["xai", "explainable ai", "interpretability", "model interpretability", "shap", "lime", "feature importance"],
    },
    "hipaa compliance": {
        "canonical": "HIPAA Compliance", "category": "Governance", "subcategory": "Healthcare Compliance",
        "aliases": ["hipaa compliant", "hipaa security rule", "hipaa privacy rule"],
    },
    "soc 2": {
        "canonical": "SOC 2", "category": "Governance", "subcategory": "Security Compliance",
        "aliases": ["soc2", "soc 2 type ii", "aicpa soc"],
    },
    "hitrust": {
        "canonical": "HITRUST", "category": "Governance", "subcategory": "Healthcare Compliance",
        "aliases": ["hitrust certification", "hitrust csf"],
    },
    "fedramp": {
        "canonical": "FedRAMP", "category": "Governance", "subcategory": "Security Compliance",
        "aliases": ["fedramp authorization", "federal risk and authorization management"],
    },
    "data privacy": {
        "canonical": "Data Privacy", "category": "Governance", "subcategory": "Compliance",
        "aliases": ["gdpr", "ccpa", "data protection", "privacy compliance"],
    },
}


# ---------------------------------------------------------------------------
# Suppression map — broad parent is removed when any specific child is found
# ---------------------------------------------------------------------------

_PARENT_CHILDREN: dict[str, list[str]] = {
    # "Generative AI" is noise when we already have the specific technique
    "Generative AI": [
        "RAG", "Agentic RAG", "GraphRAG",
        "LangChain", "LangGraph", "LlamaIndex", "DSPy", "Haystack",
        "AutoGen", "CrewAI", "Semantic Kernel",
        "LoRA", "QLoRA", "RLHF", "DPO", "PEFT", "Instruction Tuning",
        "Constitutional AI / RLAIF", "Reward Modeling", "Knowledge Distillation",
        "Prompt Engineering", "Function Calling", "Multi-Agent Systems",
        "Structured Generation", "ReAct", "Synthetic Data Generation",
        "Embeddings", "Vector Search", "Reranking",
        "Amazon Bedrock", "Azure OpenAI", "Gemini API",
        "vLLM", "Triton Inference Server", "TensorRT", "Model Quantization",
        "LLM Evaluation", "RAGAS", "Arize AI", "LangFuse", "DeepEval",
    ],
    # Cloud providers — suppress when any specific service is found
    "AWS": [
        "AWS SageMaker", "AWS Glue", "Amazon Redshift", "Amazon S3",
        "Amazon Kinesis", "Amazon EKS", "AWS Lambda", "AWS Step Functions",
        "AWS Batch", "Amazon Athena", "AWS IAM", "Amazon Bedrock",
    ],
    "Azure": [
        "Azure Machine Learning", "Azure Data Factory", "Azure Databricks",
        "Azure Kubernetes Service", "Azure Blob Storage", "Azure DevOps",
        "Azure Synapse Analytics", "Azure OpenAI",
    ],
    "GCP": [
        "Vertex AI", "BigQuery", "Google Cloud Run", "Google Kubernetes Engine",
        "Cloud Composer", "Google Dataflow", "Google Pub/Sub",
    ],
    # NLP — suppress when specific clinical/ML NLP tools are found
    "NLP": [
        "Clinical NLP", "Named Entity Recognition", "Relation Extraction",
        "medspaCy", "scispaCy", "BioBERT", "ClinicalBERT", "PubMedBERT",
    ],
    # Deep Learning — suppress when specific frameworks are mentioned
    "Deep Learning": [
        "PyTorch", "TensorFlow", "JAX",
    ],
    # Data Pipelines — suppress when a specific orchestration tool is found
    "Data Pipelines": [
        "Apache Airflow", "Prefect", "Dagster", "Temporal",
        "Apache Spark", "Apache Kafka", "Apache Flink", "dbt",
        "AWS Glue", "Google Dataflow", "Azure Data Factory",
    ],
    # CI/CD — suppress when specific tools found
    "CI/CD": [
        "GitHub Actions", "ArgoCD",
    ],
    # Computer Vision — suppress when domain-specific or medical imaging variant found
    "Computer Vision": [
        "Radiology AI", "Pathology AI", "DICOM",
        "MONAI", "nnU-Net", "Medical Image Segmentation",
    ],
    # RL — suppress when specific alignment technique is found
    "Reinforcement Learning": [
        "RLHF", "DPO",
    ],
    # Multi-agent — suppress when a specific framework is named
    "Multi-Agent Systems": [
        "AutoGen", "CrewAI", "LangGraph",
    ],
    # Genomics broad — suppress when specific tools or data types are found
    "Genomics": [
        "BWA / Bowtie2", "GATK", "STAR Aligner", "Samtools / bcftools",
        "DESeq2 / edgeR", "Seurat", "Scanpy", "Nextflow", "Snakemake",
        "WGS / WES", "RNA-seq", "scRNA-seq", "Spatial Transcriptomics",
        "Variant Calling", "GWAS",
    ],
    # EHR broad — suppress when specific system is named
    "EHR": [
        "Epic EHR", "Cerner / Oracle Health",
    ],
}


# ---------------------------------------------------------------------------
# Compiled pattern cache  (built once at import time)
# ---------------------------------------------------------------------------

class _CompiledEntry:
    __slots__ = ("pattern", "canonical", "category", "subcategory")

    def __init__(self, pattern: re.Pattern, canonical: str, category: str, subcategory: str) -> None:
        self.pattern = pattern
        self.canonical = canonical
        self.category = category
        self.subcategory = subcategory


def _build_patterns() -> list[_CompiledEntry]:
    entries: list[_CompiledEntry] = []
    seen_terms: set[str] = set()

    for key, meta in SKILLS_DICT.items():
        terms = [key] + meta.get("aliases", [])
        for term in terms:
            term_lower = term.lower()
            if term_lower in seen_terms:
                continue
            seen_terms.add(term_lower)

            escaped = re.escape(term_lower)

            if term_lower[-1].isalnum() or term_lower[-1] in ("_", "+"):
                end_bound = r"\b"
            else:
                end_bound = r"(?=\s|$|[,;.()\[\]])"
            if term_lower[0].isalnum() or term_lower[0] in ("_",):
                start_bound = r"\b"
            else:
                start_bound = r"(?:^|(?<=\s)|(?<=[,;.()\[\]]))"

            pat = re.compile(start_bound + escaped + end_bound, re.IGNORECASE)
            entries.append(_CompiledEntry(pat, meta["canonical"], meta["category"], meta.get("subcategory", "")))

    logger.debug("Compiled %d skill patterns", len(entries))
    return entries


_COMPILED_PATTERNS: list[_CompiledEntry] = _build_patterns()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_skills(text: str) -> list[SkillMatch]:
    """
    Extract skills from *text* using deterministic regex matching.
    Returns a deduplicated list of SkillMatch (canonical, category, subcategory).
    Never infers or hallucinates — only returns skills explicitly found in text.

    Broad parent skills (e.g. "AWS", "Generative AI") are suppressed when at least
    one specific child skill (e.g. "AWS SageMaker", "RAG") is also found.
    """
    if not text:
        return []

    found: dict[str, SkillMatch] = {}
    for entry in _COMPILED_PATTERNS:
        if entry.pattern.search(text):
            if entry.canonical not in found:
                found[entry.canonical] = SkillMatch(
                    canonical=entry.canonical,
                    category=entry.category,
                    subcategory=entry.subcategory,
                )

    # Suppress broad parents when specific children are present
    for parent, children in _PARENT_CHILDREN.items():
        if parent in found and any(c in found for c in children):
            del found[parent]

    return list(found.values())


def get_skill_categories() -> list[str]:
    return sorted({v["category"] for v in SKILLS_DICT.values()})
