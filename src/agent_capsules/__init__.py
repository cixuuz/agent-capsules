"""agent-capsules: Universal learning extraction for AI coding agents."""

from agent_capsules.store import CapsuleStore
from agent_capsules.extract import extract_capsules
from agent_capsules.distill import GeneDistiller
from agent_capsules.models import Capsule, Gene

__version__ = "0.1.0"
__all__ = ["CapsuleStore", "extract_capsules", "GeneDistiller", "Capsule", "Gene"]
