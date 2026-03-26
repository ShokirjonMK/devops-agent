"""
LLM tanlash va HTTP chaqiruvlar — `app.services.llm_router` bilan bir xil manba.
Agent va testlar `app.agent.llm_router` dan import qilishi mumkin.
"""

from __future__ import annotations

from app.services.llm_router import LLMRouter, OPENAI_COMPATIBLE, PROVIDER_LIST

__all__ = ["LLMRouter", "OPENAI_COMPATIBLE", "PROVIDER_LIST"]
