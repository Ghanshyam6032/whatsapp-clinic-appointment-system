import httpx
from config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    logger,
)

# Use v26.0 consistently without exposing token in the URL
BASE_URL = f"https://graph.facebook.com/v26.0/{WHATSAPP_PHONE_NUMBER_ID}"

HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

async def send_text_message(to_number: str, text: str):
    """Send a WhatsApp text message."""
    url = f"{BASE_URL}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "body": text
        }
    }

    logger.info(f"Sending message to {to_number}. URL: {url}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                json=payload,
                headers=HEADERS,
                timeout=20.0,
            )

            response.raise_for_status()
            logger.info(f"✅ Message sent successfully to {to_number}")
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error("=" * 60)
            logger.error("WHATSAPP SEND ERROR")
            logger.error(f"Request URL : {url}")
            logger.error(f"Status Code : {e.response.status_code}")
            logger.error(f"Response    : {e.response.text}")
            logger.error("=" * 60)
            return None

        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp message: {e}")
            return None


async def mark_message_as_read(message_id: str):
    """Mark an incoming WhatsApp message as read."""
    url = f"{BASE_URL}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    logger.info(f"Marking message as read. URL: {url} | Message ID: {message_id}")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                json=payload,
                headers=HEADERS,
                timeout=20.0,
            )

            response.raise_for_status()
            logger.info(f"✅ Message marked as read: {message_id}")

        except httpx.HTTPStatusError as e:
            logger.error("=" * 60)
            logger.error("MARK AS READ ERROR")
            logger.error(f"Request URL : {url}")
            logger.error(f"Status Code : {e.response.status_code}")
            logger.error(f"Response    : {e.response.text}")
            logger.error("=" * 60)
            # Return cleanly so the webhook continues processing the patient's message
            return None

        except Exception as e:
            logger.error(f"Unexpected error in mark_message_as_read: {e}")
            # Return cleanly to prevent crashing the background task
            return None