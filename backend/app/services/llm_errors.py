"""Lỗi chung của tầng AI - tách riêng để ollama_client và llm dùng chung không bị import vòng."""


class LLMError(Exception):
    """Không gọi được mô hình ngôn ngữ (bất kể nhà cung cấp nào)."""
