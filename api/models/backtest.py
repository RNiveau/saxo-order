"""Pydantic request/response models for the Backtest API."""

from pydantic import BaseModel

from model import BacktestDefinition


class BacktestDefinitionResponse(BaseModel):
    code: str
    display_name: str
    instrument: str

    @classmethod
    def from_definition(
        cls, definition: BacktestDefinition
    ) -> "BacktestDefinitionResponse":
        return cls(
            code=definition.code,
            display_name=definition.display_name,
            instrument=definition.instrument,
        )
