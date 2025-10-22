"""Prompt building and context injection for agent iterations.

This module handles all prompt construction logic for the agent, including
initial message setup, task-aware prompts, periodic status updates, and
rejection messages.
"""

from .context_builder import ContextBuilder

__all__ = ['ContextBuilder']