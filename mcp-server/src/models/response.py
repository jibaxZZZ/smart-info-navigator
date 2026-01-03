"""Standard response models for MCP tools."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from datetime import datetime


class MCPResponse(BaseModel):
    """Standard response format for all MCP tools."""

    success: bool = Field(..., description="Whether the operation was successful")
    data: Optional[Any] = Field(None, description="Response payload")
    metadata: dict[str, Any] = Field(
        default_factory=lambda: {
            "timestamp": datetime.now().isoformat(),
            "processingTime": 0.0,
        },
        description="Metadata about the response",
    )
    error: Optional[str] = Field(None, description="Error message if operation failed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"result": "example"},
                "metadata": {
                    "timestamp": "2025-01-03T12:00:00Z",
                    "processingTime": 1.23,
                },
                "error": None,
            }
        }
    )
