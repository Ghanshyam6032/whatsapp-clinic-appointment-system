from fastapi import APIRouter, Request, Response, BackgroundTasks, HTTPException
from config import WHATSAPP_VERIFY_TOKEN, logger
from agent import process_message
from whatsapp_service import send_text_message, mark_message_as_read
from cachetools import TTLCache

router = APIRouter()

# Memory cache to strictly prevent processing duplicate messages from Meta
# Keeps message IDs for 10 minutes (600 seconds)
processed_message_ids = TTLCache(maxsize=1000, ttl=600)

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Verifies the webhook via Meta WhatsApp Cloud API requirements."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            logger.info("✅ WEBHOOK VERIFIED")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
            
    raise HTTPException(status_code=400, detail="Missing parameters")

async def process_whatsapp_background(body: dict):
    """Processes incoming messages in the background to avoid blocking."""
    try:
        if body.get("object") == "whatsapp_business_account":
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Handle messages
                    if "messages" in value:
                        for msg in value.get("messages", []):
                            msg_id = msg.get("id")
                            
                            # DUPLICATE PROTECTION: If we already saw this message ID, safely ignore it.
                            if msg_id in processed_message_ids:
                                logger.info(f"Duplicate message ignored: {msg_id}")
                                continue
                                
                            processed_message_ids[msg_id] = True

                            msg_type = msg.get("type")
                            sender = msg.get("from")

                            await mark_message_as_read(msg_id)

                            if msg_type == "text":
                                text = msg.get("text", {}).get("body", "")
                                response_text = process_message(sender, text)
                                await send_text_message(sender, response_text)
                            else:
                                logger.info(f"⚠️ Ignored unsupported message type: {msg_type}")
                                await send_text_message(sender, "⚠️ This AI system currently only supports text messages. Please reply with text.")
                                
                    # Handle message statuses safely without crashing
                    elif "statuses" in value:
                        logger.debug("Received message status update, ignoring.")
                        
    except Exception as e:
        logger.error(f"Error processing webhook payload: {e}")

@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receives WhatsApp webhook payload and passes it to a background task."""
    try:
        body = await request.json()
        background_tasks.add_task(process_whatsapp_background, body)
        return Response(content="EVENT_RECEIVED", status_code=200)
    except Exception as e:
        logger.error(f"Failed to read webhook body: {e}")
        return Response(content="ERROR", status_code=500)