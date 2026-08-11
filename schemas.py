from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ValidationResult(BaseModel):
    is_valid: bool = Field(description="True if user input meets rules, False otherwise.")
    extracted_value: str = Field(description="The exact extracted value. Empty if invalid.")