import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from api import router as api_router
from whatsapp_webhook import router as webhook_router
from google_tools import init_sheet, test_calendar, clean_past_calendar_events, get_appointments_for_reminder, mark_reminder_sent
from whatsapp_service import send_text_message
from config import logger, TZ

app = FastAPI(title="AI Clinic Booking System with WhatsApp")
scheduler = BackgroundScheduler(timezone=TZ)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api", tags=["Web API"])
app.include_router(webhook_router, tags=["WhatsApp Webhooks"])

def reminder_job():
    """Runs every 15 minutes to find appointments within 1-2 hours and send WhatsApp reminders."""
    logger.info("Running automatic appointment reminder check...")
    try:
        reminders = get_appointments_for_reminder()
        if not reminders:
            logger.info("No upcoming appointments require reminders at this time.")
            return

        for apt in reminders:
            message = (
                f"🔔 *Appointment Reminder*\n"
                f"Hello {apt['name']} 👋\n"
                f"Your appointment is today:\n\n"
                f"👨‍⚕️ {apt['doctor']}\n"
                f"⏰ {apt['time']}\n"
                f"📅 {apt['date']}\n\n"
                f"Please arrive 10 minutes early.\n"
                f"Reply to this message if you need to Reschedule or Cancel."
            )
            # Run the async WhatsApp sender inside the synchronous scheduler context safely
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(send_text_message(apt['mobile'], message))
            loop.close()
            
            if success:
                mark_reminder_sent(apt['row'])
                logger.info(f"✅ Reminder sent successfully to {apt['mobile']}")
    except Exception as e:
        logger.error(f"Error in reminder scheduler: {e}")

@app.on_event("startup")
def startup_event():
    logger.info("🚀 Starting AI Clinic Booking System")
    init_sheet()
    test_calendar()
    clean_past_calendar_events()
    
    # Start Background Reminder Job strictly tracking TZ
    scheduler.add_job(reminder_job, trigger=IntervalTrigger(minutes=15, timezone=TZ))
    scheduler.start()
    
    logger.info("✅ Startup Completed")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

@app.get("/")
async def api_status():
    return {"status": "online", "service": "AI Clinic Booking System API"}

if __name__ == "__main__":
    # Dynamically bind to Railway's PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
