"""Request and response models for the staffing agent.

Unknown fields are rejected. The API key is accepted on the request and is not
part of the result.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _reject_empty_countries(countries: list[str] | None) -> list[str] | None:
    if countries is not None and len(countries) == 0:
        raise ValueError("countries must be omitted or contain at least one country")
    return countries


class LLMChoice(BaseModel):
    """Which model answers the turn. The default is Gemini on the free tier."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(
        default="google",
        description="google uses the Gemini API. Any other name is passed to init_chat_model.",
    )
    model: str = Field(
        default="gemini-3.5-flash-lite",
        description="Model id. gemini-3.5-flash-lite is the free-tier default for a new project.",
    )
    api_key: str | None = Field(
        default=None,
        description="User-supplied key. Required for the Gemini provider. Not stored in the result.",
    )

    @field_validator("provider", "model")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.casefold()


class SimulatorParams(BaseModel):
    """User settings the beer-game simulator uses to scale demand."""

    model_config = ConfigDict(extra="forbid")

    demand_scale: float = Field(
        default=1.0,
        gt=0,
        description="1 keeps the forecast. 0.8 is lower sign-ups and 1.2 is higher sign-ups.",
    )
    countries: list[str] | None = Field(
        default=None,
        description="Countries to adjust. Omit to include every country.",
    )

    @field_validator("countries")
    @classmethod
    def countries_not_empty(cls, countries: list[str] | None) -> list[str] | None:
        return _reject_empty_countries(countries)


class StaffingParams(BaseModel):
    """User settings for the headcount search.

    The plan must maximize profit and beat keep_current_staff: each country's
    January 2026 headcount repeated for every month.
    """

    model_config = ConfigDict(extra="forbid")

    countries: list[str] | None = Field(
        default=None,
        description="Countries to re-staff. Countries omitted here stay at current staff.",
    )
    min_agents: int | None = Field(default=None, ge=0)
    max_agents_vs_current: float | None = Field(
        default=None,
        gt=0,
        description="Upper bound as a multiple of January 2026 headcount. 2.0 means at most double.",
    )
    min_service_rate: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Optional annual service-rate floor. 0.98 is the SLA mode. Omit for profit-only.",
    )
    objective: Literal["max_profit"] = "max_profit"
    baseline: Literal["keep_current_staff"] = "keep_current_staff"

    @field_validator("countries")
    @classmethod
    def countries_not_empty(cls, countries: list[str] | None) -> list[str] | None:
        return _reject_empty_countries(countries)


class TurnRequest(BaseModel):
    """One manager message, the model to use, and the settings for this turn."""

    model_config = ConfigDict(extra="forbid")

    message: str
    thread_id: str = "default"
    llm: LLMChoice = Field(default_factory=LLMChoice)
    enabled_tools: list[str] = Field(
        default_factory=list,
        description="Optional data tools to bind. world_bank_gdp stays off until it is listed.",
    )
    simulator: SimulatorParams = Field(default_factory=SimulatorParams)
    staffing: StaffingParams = Field(default_factory=StaffingParams)

    @field_validator("message", "thread_id")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class TurnResult(BaseModel):
    """The reply and the settings that were in effect after the turn."""

    model_config = ConfigDict(extra="forbid")

    reply: str
    thread_id: str
    provider: str
    model: str
    enabled_tools: list[str]
    simulator: SimulatorParams
    staffing: StaffingParams
