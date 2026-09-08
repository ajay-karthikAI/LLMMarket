"""Unit tests for deterministic skill extraction."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from extraction.skills import extract_skills, SKILLS_DICT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def skill_names(text: str) -> set[str]:
    return {m.canonical for m in extract_skills(text)}


# ---------------------------------------------------------------------------
# Positive matches — skills explicitly in text
# ---------------------------------------------------------------------------

def test_pytorch_exact():
    assert "PyTorch" in skill_names("Experience with PyTorch required")

def test_pytorch_alias_torch():
    assert "PyTorch" in skill_names("Proficiency in torch for training")

def test_rag_full_phrase():
    assert "RAG" in skill_names("Build retrieval augmented generation pipelines")

def test_rag_alias_hyphenated():
    assert "RAG" in skill_names("Implement retrieval-augmented generation")

def test_langchain():
    assert "LangChain" in skill_names("Using LangChain for orchestration")

def test_langchain_alias_space():
    assert "LangChain" in skill_names("Built with lang chain")

def test_aws_exact():
    # SageMaker is a child of AWS — AWS is suppressed, SageMaker surfaces instead
    names = skill_names("Deploy on AWS using SageMaker")
    assert "AWS SageMaker" in names
    assert "AWS" not in names

def test_aws_alias_amazon():
    # Generic "Amazon Web Services" with no specific service — AWS should show
    assert "AWS" in skill_names("Amazon Web Services deployment")

def test_fhir():
    assert "FHIR" in skill_names("Build FHIR-compliant APIs for EHR integration")

def test_ehr_alias():
    assert "EHR" in skill_names("5 years with electronic health records")

def test_hipaa():
    assert "HIPAA" in skill_names("Must ensure HIPAA compliance")

def test_kubernetes():
    assert "Kubernetes" in skill_names("Orchestrate with Kubernetes")

def test_kubernetes_alias_k8s():
    assert "Kubernetes" in skill_names("Deploy on k8s clusters")

def test_clinical_nlp():
    assert "Clinical NLP" in skill_names("Experience with clinical NLP and medical NLP")

def test_icd10_alias():
    assert "ICD-10" in skill_names("Knowledge of medical coding and ICD-10 standards")

def test_multiple_skills():
    text = "We use PyTorch, LangChain, RAG, FHIR, and Kubernetes"
    names = skill_names(text)
    assert {"PyTorch", "LangChain", "RAG", "FHIR", "Kubernetes"}.issubset(names)

def test_lora_is_own_skill():
    # LoRA is now its own canonical entry, not an alias for "Fine-tuning"
    names = skill_names("Apply LoRA for efficient fine-tuning of LLMs")
    assert "LoRA" in names

def test_qlora_is_own_skill():
    assert "QLoRA" in skill_names("We use QLoRA to fine-tune our medical LLM")

def test_rlhf_is_own_skill():
    assert "RLHF" in skill_names("Trained via reinforcement learning from human feedback")

def test_dpo_is_own_skill():
    assert "DPO" in skill_names("Direct preference optimization for alignment")

def test_embedding_alias():
    assert "Embeddings" in skill_names("Generate text embeddings using OpenAI")

def test_gcp_alias_vertex():
    # Vertex AI is a GCP child — GCP is suppressed, Vertex AI surfaces instead
    names = skill_names("Use Vertex AI on Google Cloud")
    assert "Vertex AI" in names
    assert "GCP" not in names

def test_snowflake():
    assert "Snowflake" in skill_names("Data warehouse built on Snowflake")

def test_clinical_decision_support():
    assert "Clinical Decision Support" in skill_names("Build a clinical decision support system for physicians")

def test_de_identification():
    assert "De-identification" in skill_names("Implement de-identification of PHI from clinical notes")


# ---------------------------------------------------------------------------
# Negative — skills NOT in text should not appear
# ---------------------------------------------------------------------------

def test_no_hallucination_pytorch():
    names = skill_names("We value strong communication skills and teamwork")
    assert "PyTorch" not in names

def test_no_hallucination_rag():
    names = skill_names("Manage cloud infrastructure and databases")
    assert "RAG" not in names

def test_no_hallucination_fhir():
    names = skill_names("Python developer with 5 years experience")
    assert "FHIR" not in names

def test_empty_text():
    assert extract_skills("") == []

def test_none_safe():
    assert extract_skills(None) == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Category checks
# ---------------------------------------------------------------------------

def test_rag_is_llm_stack():
    matches = extract_skills("retrieval augmented generation pipeline")
    cat_map = {m.canonical: m.category for m in matches}
    assert cat_map.get("RAG") == "LLM Stack"

def test_kubernetes_is_mlops():
    matches = extract_skills("run on k8s clusters")
    cat_map = {m.canonical: m.category for m in matches}
    assert cat_map.get("Kubernetes") == "MLOps"

def test_fhir_is_healthcare():
    matches = extract_skills("FHIR-compliant REST API")
    cat_map = {m.canonical: m.category for m in matches}
    assert cat_map.get("FHIR") == "Healthcare"


# ---------------------------------------------------------------------------
# Skills dict integrity
# ---------------------------------------------------------------------------

def test_all_dict_entries_have_required_fields():
    for key, val in SKILLS_DICT.items():
        assert "canonical" in val, f"Missing 'canonical' in {key}"
        assert "category" in val,  f"Missing 'category' in {key}"
        assert isinstance(val.get("aliases", []), list), f"Bad aliases in {key}"

def test_no_duplicate_canonicals():
    canonicals = [v["canonical"] for v in SKILLS_DICT.values()]
    assert len(canonicals) == len(set(canonicals)), "Duplicate canonical names in SKILLS_DICT"
