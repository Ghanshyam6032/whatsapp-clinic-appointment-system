import os
import logging
import pytz
from dotenv import load_dotenv

load_dotenv()

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("clinic_system")

# Timezone Configuration
TZ = pytz.timezone("Asia/Kolkata")

# Google Config
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# WhatsApp Config
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET")

# Clinic Configuration
CLINIC_MORNING_START = "10:00"
CLINIC_MORNING_END = "13:00"
CLINIC_EVENING_START = "16:00"
CLINIC_EVENING_END = "19:00"
SLOT_DURATION_MIN = 20

DOCTORS = {
    "1": "Dr. Patel",
    "2": "Dr. Shah",
    "3": "Dr. Mehta"
}
