# models.py
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, RootModel, field_validator

# Guard against absurdly large payloads
MAX_CODE_LENGTH = 50_000


class RunRequest(BaseModel):
    """Body for POST /run and POST /validate."""

    code: str = Field(..., description="PipeScript source code typed by the user")
    data: Optional[Any] = Field(
        default=None,
        description="Optional input dataset, injected as `input_data`. "
                    "list, list-of-dicts, or null.",
    )

    @field_validator("code")
    @classmethod
    def code_must_be_non_empty_and_bounded(cls, v: str) -> str:
        if v is None or not v.strip():
            raise ValueError("`code` must not be empty.")
        if len(v) > MAX_CODE_LENGTH:
            raise ValueError(
                f"`code` is {len(v)} characters, which exceeds the "
                f"{MAX_CODE_LENGTH}-character limit."
            )
        return v


class TokenOut(BaseModel):
    """One entry of the `tokens` list used for frontend syntax highlighting."""

    type: str
    value: str
    line: int
    col: int


class ErrorDetail(BaseModel):
    """One entry of the `errors` list."""

    phase: str  # "Lexer" | "Parser" | "Semantic" | "Runtime"
    message: str
    line: int


RowStatus = Literal["ok", "blank", "negative", "invalid_type"]


class StatusAnnotatedRow(BaseModel):
    """A row in the input/output dataset with an attached backend status."""

    status: RowStatus

    model_config = {"extra": "allow"}


class RowOutcomeStatus(BaseModel):
    """What was applied to a row while producing the final output."""

    state: Literal["ok", "cleaned", "transformed", "generated"]
    implemented: List[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class OutputItem(BaseModel):
    """One item in the cleaned output list with its status metadata."""

    value: Any
    status: RowOutcomeStatus

    model_config = {"extra": "allow"}


class RowDataset(RootModel[List[Dict[str, Any]]]):
    """A list of row-like records used for before/after data tables."""


class RunResponse(BaseModel):
    """Exact shape returned by PipeScriptEngine().run(), per the README."""

    success: bool
    before: Any = Field(default=None, description="Input data before PipeScript runs")
    output: Any = Field(
        default=None,
        description="Final value after PipeScript runs; list outputs may be wrapped with per-item status metadata",
    )
    print_log: List[str] = Field(default_factory=list)
    tokens: List[TokenOut] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)


class ValidateResponse(BaseModel):
    """Result of the lint-only /validate endpoint (Lexer+Parser+Semantic only)."""

    success: bool
    tokens: List[TokenOut] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)


class ExampleScript(BaseModel):
    """One canned example served by GET /examples."""

    name: str
    description: str
    code: str
    data: Optional[Any] = None


class HealthResponse(BaseModel):
    status: str