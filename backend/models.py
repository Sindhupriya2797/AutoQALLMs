from pydantic import BaseModel
from typing import Optional


class GenerateRequest(BaseModel):
    """
    This defines exactly what the frontend sends to the backend
    when the user clicks Generate.
    """
    url: str
    model: str        # "gpt4", "claude", or "grok"
    framework: str    # "selenium_python" or "playwright_js"


class GenerateResponse(BaseModel):
    """
    This defines exactly what the backend sends back to the frontend.
    """
    success: bool
    script: Optional[str] = None
    error: Optional[str] = None
    generation_time: Optional[float] = None
    elements_found: Optional[int] = None
    framework: Optional[str] = None
    model_used: Optional[str] = None