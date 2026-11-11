from pydantic import BaseModel, ConfigDict, Field

from app.modules.catalog.schemas import APIModel


class ProfileSummary(APIModel):
    education: str | None = Field(default=None, max_length=1000)
    experience: str | None = Field(default=None, max_length=1000)
    skills: str | None = Field(default=None, max_length=1000)
    tools: str | None = Field(default=None, max_length=1000)
    languages: str | None = Field(default=None, max_length=1000)
    interests: str | None = Field(default=None, max_length=1000)


class ModelChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    offer_id: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1600)


class ModelAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cv_readable: bool
    profile: ProfileSummary
    choices: list[ModelChoice] = Field(max_length=3)


class RecommendedOffer(APIModel):
    offer_uuid: str
    area_slug: str
    title: str
    folio: str
    remuneration: str
    reason: str
    supervisor_email: str
    work_address: str


class RecommendationAnalysis(APIModel):
    profile: ProfileSummary | None
    recommendations: list[RecommendedOffer]
    message: str | None = None
