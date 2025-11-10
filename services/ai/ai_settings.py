from dataclasses import dataclass, field
from enum import Enum

from core.config import AIMode, get_config


class AgentRole(Enum):
    SUMMARIZER = "summarizer"
    METRICS_EXPERT = "metrics_expert"
    PHYSIOLOGY_EXPERT = "physiology_expert"
    ACTIVITY_EXPERT = "activity_expert"
    SYNTHESIS = "synthesis"
    WORKOUT = "workout"
    COMPETITION_PLANNER = "competition_planner"
    SEASON_PLANNER = "season_planner"
    FORMATTER = "formatter"


@dataclass
class AISettings:
    mode: AIMode

    model_assignments: dict[AIMode, dict[AgentRole, str]] = field(
        default_factory=lambda: {
            AIMode.STANDARD: {
                AgentRole.SUMMARIZER: "gpt-5",
                AgentRole.FORMATTER: "gpt-5",
                AgentRole.METRICS_EXPERT: "gpt-5",
                AgentRole.PHYSIOLOGY_EXPERT: "gpt-5",
                AgentRole.ACTIVITY_EXPERT: "gpt-5",
                AgentRole.SYNTHESIS: "gpt-5",
                AgentRole.WORKOUT: "gpt-5",
                AgentRole.COMPETITION_PLANNER: "gpt-5",
                AgentRole.SEASON_PLANNER: "gpt-5",
            },
            AIMode.COST_EFFECTIVE: {
                AgentRole.SUMMARIZER: "claude-3-haiku",
                AgentRole.FORMATTER: "claude-3-haiku",
                AgentRole.METRICS_EXPERT: "claude-3-haiku",
                AgentRole.PHYSIOLOGY_EXPERT: "claude-3-haiku",
                AgentRole.ACTIVITY_EXPERT: "claude-3-haiku",
                AgentRole.SYNTHESIS: "claude-3-haiku",
                AgentRole.WORKOUT: "claude-3-haiku",
                AgentRole.COMPETITION_PLANNER: "claude-3-haiku",
                AgentRole.SEASON_PLANNER: "claude-3-haiku",
            },
            AIMode.DEVELOPMENT: {
                AgentRole.SUMMARIZER: "claude-4",
                AgentRole.FORMATTER: "claude-4",
                AgentRole.METRICS_EXPERT: "claude-4",
                AgentRole.PHYSIOLOGY_EXPERT: "claude-4",
                AgentRole.ACTIVITY_EXPERT: "claude-4",
                AgentRole.SYNTHESIS: "claude-4",
                AgentRole.WORKOUT: "claude-4",
                AgentRole.COMPETITION_PLANNER: "claude-4",
                AgentRole.SEASON_PLANNER: "claude-4",
            },
            AIMode.KIMI: {
                AgentRole.SUMMARIZER: "kimi-k2",
                AgentRole.FORMATTER: "kimi-k2",
                AgentRole.METRICS_EXPERT: "kimi-k2",
                AgentRole.PHYSIOLOGY_EXPERT: "kimi-k2",
                AgentRole.ACTIVITY_EXPERT: "kimi-k2",
                AgentRole.SYNTHESIS: "kimi-k2",
                AgentRole.WORKOUT: "kimi-k2",
                AgentRole.COMPETITION_PLANNER: "kimi-k2",
                AgentRole.SEASON_PLANNER: "kimi-k2",
            },
            AIMode.KIMI_BALANCED: {
                # K2-0905 for tool-calling experts (need latest agentic features)
                AgentRole.METRICS_EXPERT: "kimi-k2-0905",
                AgentRole.PHYSIOLOGY_EXPERT: "kimi-k2-0905",
                AgentRole.ACTIVITY_EXPERT: "kimi-k2-0905",
                AgentRole.SYNTHESIS: "kimi-k2-0905",
                AgentRole.COMPETITION_PLANNER: "kimi-k2-0905",
                AgentRole.SEASON_PLANNER: "kimi-k2-0905",
                # V1-32k for data processing roles (cost optimization)
                AgentRole.SUMMARIZER: "kimi-v1-32k",
                AgentRole.FORMATTER: "kimi-v1-32k",
                AgentRole.WORKOUT: "kimi-v1-32k",
            },
            AIMode.KIMI_COST_EFFECTIVE: {
                # V1-8k for high-output roles (cheapest per-token output)
                AgentRole.SUMMARIZER: "kimi-v1-8k",
                AgentRole.FORMATTER: "kimi-v1-8k",
                AgentRole.WORKOUT: "kimi-v1-8k",
                # V1-32k for tool-calling roles (balance cost and features)
                AgentRole.METRICS_EXPERT: "kimi-v1-32k",
                AgentRole.PHYSIOLOGY_EXPERT: "kimi-v1-32k",
                AgentRole.ACTIVITY_EXPERT: "kimi-v1-32k",
                AgentRole.COMPETITION_PLANNER: "kimi-v1-32k",
                AgentRole.SEASON_PLANNER: "kimi-v1-32k",
                # V1-128k for synthesis (high context needs)
                AgentRole.SYNTHESIS: "kimi-v1-128k",
            },
        }
    )

    def get_model_for_role(self, role: AgentRole) -> str:
        return self.model_assignments[self.mode][role]

    @classmethod
    def load_settings(cls) -> "AISettings":
        return cls(mode=get_config().ai_mode)


# Global settings instance
ai_settings = AISettings.load_settings()
