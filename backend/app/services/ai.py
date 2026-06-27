from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.language_models import BaseLanguageModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import get_settings


def get_embeddings():
    settings = get_settings()
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
        return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
    return HuggingFaceEmbeddings(model_name=settings.embedding_model)


def get_llm() -> BaseLanguageModel:
    settings = get_settings()
    if settings.llm_provider == "ollama":
        return ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url, temperature=0.1)
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0.1)
