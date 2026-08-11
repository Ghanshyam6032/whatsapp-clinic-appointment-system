from fastapi import APIRouter
from schemas import ChatRequest
from agent import process_message
from prompts import main_menu_prompt

router = APIRouter()

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Maintains backward compatibility for the existing web frontend UI."""
    if not request.message:
        return {"response": main_menu_prompt}
    response = process_message(request.session_id, request.message)
    return {"response": response}