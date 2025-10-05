"""
Multi-Agent Blog Automation System

This package contains specialized agents for automated blog content generation:
- BaseAgent: Common functionality for all agents
- ManagerAgent: Orchestrates workflow and manages state transitions
- TopicDiscoveryAgent: Discovers unique topics and cleans stale workflows
- ResearchAgent: Conducts keyword research and content analysis
- SEOWriterAgent: Writes SEO-optimized articles
- ContentCheckerAgent: Validates quality and compliance
"""

__version__ = "2.0.0"
__author__ = "Across Ceylon"

from .base_agent import BaseAgent

__all__ = ["BaseAgent"]
