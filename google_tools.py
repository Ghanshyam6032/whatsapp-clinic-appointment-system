import os
import datetime
import threading
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import (
    GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID, GOOGLE_CALENDAR_ID,
    CLINIC_MORNING_START, CLINIC_MORNING_END, CLINIC_EVENING_START, CLINIC_EVENING_END, SLOT_DURATION_MIN,
    logger, TZ
)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/calendar']
creds = None
if os.path.exists(GOOGLE_CREDENTIALS_FILE):
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)

# Concurrency & Lock Management
PENDING_LOCKS = {}
booking_lock = threading.Lock() # Prevents race conditions during simultaneous sheet insertions

def get_sheets_service(): 
    return build('sheets', 'v4', credentials=creds)

def get_calendar_service(): 
    return build('calendar', 'v3', credentials=creds)

def clean_expired_locks():
    now = datetime.datetime.now(TZ)
    expired_keys = [k for k, v in PENDING_LOCKS.items() if v['expires_at'] < now]
    for k in expired_keys:
        del PENDING_LOCKS[k]

def acquire_pending_lock(doctor: str, date_str: str, time_str: str, session_id: str) -> bool:
    clean_expired_locks()
    lock_key = f"{doctor}_{date_str}_{time_str}"
    
    if lock_key in PENDING_LOCKS and PENDING_LOCKS[lock_key]["session_id"] != session_id:
        return False
        
    PENDING_LOCKS[lock_key] = {
        "session_id": session_id,
        "expires_at": datetime.datetime.now(TZ) + datetime.timedelta(minutes=5)
    }
    return True

def verify_and_clear_lock(doctor: str, date_str: str, time_str: str, session_id: str) -> bool:
    clean_expired_locks()
    lock_key = f"{doctor}_{date_str}_{time_str}"
    
    if lock_key in PENDING_LOCKS and PENDING_LOCKS[lock_key]["session_id"] == session_id:
        del PENDING_LOCKS[lock_key]
        return True
    return False

def init_sheet():
    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1!A1:M1").execute()
        if 'values' not in result:
            headers = [["ID", "Name", "Mobile", "Age", "Doctor", "Date", "Time", "Duration", "Reason", "Status", "Created At", "Event ID", "Reminder Sent"]]
            service.spreadsheets().values().update(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1!A1", valueInputOption="RAW", body={"values": headers}).execute()
    except Exception as e: 
        logger.error(f"Error initializing sheet: {e}")

def test_calendar():
    try:
        service = get_calendar_service()
        service.events().list(calendarId=GOOGLE_CALENDAR_ID, maxResults=1).execute()
        logger.info(f"✅ Calendar Connected: {GOOGLE_CALENDAR_ID}")
    except Exception as e: 
        logger.error(f"❌ Calendar Error: {e}")

def clean_past_calendar_events():
    """Removes events older than 48 hours after appointment end."""
    try:
        service = get_calendar_service()
        time_max = (datetime.datetime.utcnow() - datetime.timedelta(hours=48)).isoformat() + 'Z'
        events_result = service.events().list(calendarId=GOOGLE_CALENDAR_ID, timeMax=time_max, singleEvents=True).execute()
        events = events_result.get('items', [])
        
        for event in events:
            try: 
                service.events().delete(calendarId=GOOGLE_CALENDAR_ID, eventId=event['id']).execute()
                logger.info(f"Cleaned old calendar event: {event['id']}")
            except: 
                pass
    except Exception as e: 
        logger.error(f"Calendar Cleanup Error: {e}")

def get_patient_history(mobile: str):
    """Retrieves patient history based on WhatsApp number (matching last 10 digits)."""
    try:
        values = get_sheets_service().spreadsheets().values().get(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1").execute().get('values', [])
        history = {"visits": 0, "last_visit": None, "name": None, "age": None}
        
        # Get only the last 10 digits of the incoming WhatsApp number
        search_mobile = str(mobile).strip()[-10:]
        
        for row in values[1:]:
            if len(row) > 3:
                # Get the last 10 digits of the number saved in the sheet
                row_mobile = str(row[2]).strip()[-10:]
                
                if row_mobile == search_mobile:
                    history["name"] = row[1]
                    history["age"] = row[3]
                    if len(row) > 9 and row[9] in ["Confirmed", "Completed"]:
                        history["visits"] += 1
                        history["last_visit"] = row[5]
                        
        return history if history["name"] else None
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return None

def generate_all_slots():
    slots = []
    def generate(start_str, end_str):
        start = datetime.datetime.strptime(start_str, "%H:%M")
        end = datetime.datetime.strptime(end_str, "%H:%M")
        while start + datetime.timedelta(minutes=SLOT_DURATION_MIN) <= end:
            slots.append(start.strftime("%I:%M %p"))
            start += datetime.timedelta(minutes=SLOT_DURATION_MIN)
    generate(CLINIC_MORNING_START, CLINIC_MORNING_END)
    generate(CLINIC_EVENING_START, CLINIC_EVENING_END)
    return slots

def get_slots_with_status(doctor_name: str, date_str: str, current_session_id: str):
    clean_expired_locks()
    try:
        sheet = get_sheets_service()
        result = sheet.spreadsheets().values().get(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1").execute()
        values = result.get('values', [])
        
        booked_slots = [row[6] for row in values[1:] if len(row) > 9 and row[4] == doctor_name and row[5] == date_str and row[9] == "Confirmed"]
        all_slots = generate_all_slots()
        
        current_dt = datetime.datetime.now(TZ)
        is_today = date_str == current_dt.strftime("%d-%m-%Y")
        
        display_slots = []
        for s in all_slots:
            slot_time_obj = datetime.datetime.strptime(s, "%I:%M %p").time()
            if is_today and current_dt.time() > slot_time_obj: continue 
                
            lock_key = f"{doctor_name}_{date_str}_{s}"
            if s in booked_slots:
                display_slots.append({"time": s, "status": "🔴 Booked"})
            elif lock_key in PENDING_LOCKS:
                if PENDING_LOCKS[lock_key]["session_id"] == current_session_id:
                    display_slots.append({"time": s, "status": "🟢 Available"})
                else:
                    display_slots.append({"time": s, "status": "🟡 Pending"})
            else:
                display_slots.append({"time": s, "status": "🟢 Available"})
        return display_slots
    except Exception as e: 
        return []

def check_is_slot_available_in_sheet(doctor: str, date: str, time: str) -> bool:
    try:
        sheet = get_sheets_service()
        result = sheet.spreadsheets().values().get(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1").execute()
        values = result.get('values', [])
        for row in values[1:]:
            if len(row) > 9 and row[4] == doctor and row[5] == date and row[6] == time and row[9] == "Confirmed":
                return False
        return True
    except Exception:
        return False

def generate_appointment_id() -> str:
    try:
        service = get_sheets_service()
        result = service.spreadsheets().values().get(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1!A:A").execute()
        count = len(result.get('values', []))
        return f"APT-{count:02d}"
    except Exception: 
        return "APT-99"

def create_appointment(data: dict):
    with booking_lock: 
        if not check_is_slot_available_in_sheet(data['doctor'], data['date'], data['time']):
            return False

        try:
            dt_start = TZ.localize(datetime.datetime.strptime(f"{data['date']} {data['time']}", "%d-%m-%Y %I:%M %p"))
            dt_end = dt_start + datetime.timedelta(minutes=SLOT_DURATION_MIN)
            
            event = {
                'summary': f"[{data['doctor']}] Appointment - {data['name']}",
                'description': f"ID: {data['appointment_id']}\nMobile: {data['mobile']}\nAge: {data['age']}\nReason: {data['reason']}",
                'start': {'dateTime': dt_start.isoformat(), 'timeZone': 'Asia/Kolkata'},
                'end': {'dateTime': dt_end.isoformat(), 'timeZone': 'Asia/Kolkata'},
            }
            created_event = get_calendar_service().events().insert(calendarId=GOOGLE_CALENDAR_ID, body=event).execute()
            
            row = [
                data['appointment_id'], data['name'], data['mobile'], data['age'], 
                data['doctor'], data['date'], data['time'], "20 mins", data['reason'], 
                "Confirmed", datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"), created_event['id'], "FALSE"
            ]
            get_sheets_service().spreadsheets().values().append(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1", valueInputOption="RAW", body={"values": [row]}).execute()
            return True
        except Exception as e: 
            logger.error(f"Failed to create appointment: {e}")
            return False

def find_appointment_by_mobile(mobile: str):
    """Finds active appointment by matching the last 10 digits of the mobile number."""
    try:
        values = get_sheets_service().spreadsheets().values().get(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1").execute().get('values', [])
        
        # Get only the last 10 digits of the incoming WhatsApp number
        search_mobile = str(mobile).strip()[-10:]
        
        for i, row in reversed(list(enumerate(values))):
            if len(row) > 9 and row[9] == "Confirmed":
                # Get the last 10 digits of the number saved in the sheet
                row_mobile = str(row[2]).strip()[-10:]
                
                if row_mobile == search_mobile:
                    return {
                        "Row": i + 1, 
                        "ID": row[0], 
                        "Name": row[1], 
                        "Doctor": row[4], 
                        "Date": row[5], 
                        "Time": row[6], 
                        "Reason": row[8], 
                        "Status": row[9], 
                        "EventID": row[11] if len(row) > 11 else None
                    }
        return None
    except Exception as e: 
        logger.error(f"Failed to find appointment: {e}")
        return None

def cancel_appointment_in_system(mobile: str):
    with booking_lock:
        try:
            apt = find_appointment_by_mobile(mobile)
            if not apt: return False
            
            sheet = get_sheets_service()
            sheet.spreadsheets().values().update(spreadsheetId=GOOGLE_SHEET_ID, range=f"Sheet1!J{apt['Row']}", valueInputOption="RAW", body={"values": [["Cancelled"]]}).execute()
            
            if apt['EventID']:
                try: get_calendar_service().events().delete(calendarId=GOOGLE_CALENDAR_ID, eventId=apt['EventID']).execute()
                except: pass
            return True
        except Exception as e:
            logger.error(f"Failed to cancel appointment: {e}")
            return False

def update_appointment(mobile: str, new_date: str, new_time: str) -> bool:
    with booking_lock:
        try:
            apt = find_appointment_by_mobile(mobile)
            if not apt: return False
            if not check_is_slot_available_in_sheet(apt['Doctor'], new_date, new_time): return False

            if apt['EventID']:
                dt_start = TZ.localize(datetime.datetime.strptime(f"{new_date} {new_time}", "%d-%m-%Y %I:%M %p"))
                dt_end = dt_start + datetime.timedelta(minutes=SLOT_DURATION_MIN)
                event = get_calendar_service().events().get(calendarId=GOOGLE_CALENDAR_ID, eventId=apt['EventID']).execute()
                event['start'] = {'dateTime': dt_start.isoformat(), 'timeZone': 'Asia/Kolkata'}
                event['end'] = {'dateTime': dt_end.isoformat(), 'timeZone': 'Asia/Kolkata'}
                get_calendar_service().events().update(calendarId=GOOGLE_CALENDAR_ID, eventId=apt['EventID'], body=event).execute()
            
            sheet = get_sheets_service()
            sheet.spreadsheets().values().update(
                spreadsheetId=GOOGLE_SHEET_ID, 
                range=f"Sheet1!F{apt['Row']}:G{apt['Row']}", 
                valueInputOption="RAW", 
                body={"values": [[new_date, new_time]]}
            ).execute()
            # Reset Reminder status on reschedule
            sheet.spreadsheets().values().update(
                spreadsheetId=GOOGLE_SHEET_ID, 
                range=f"Sheet1!M{apt['Row']}", 
                valueInputOption="RAW", 
                body={"values": [["FALSE"]]}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error rescheduling: {e}")
            return False

def get_appointments_for_reminder():
    """Finds appointments happening in the next 1-2 hours where reminder hasn't been sent."""
    try:
        now = datetime.datetime.now(TZ)
        time_lower = now + datetime.timedelta(hours=1)
        time_upper = now + datetime.timedelta(hours=2)
        
        sheet = get_sheets_service()
        values = sheet.spreadsheets().values().get(spreadsheetId=GOOGLE_SHEET_ID, range="Sheet1").execute().get('values', [])
        
        reminders = []
        for i, row in enumerate(values[1:]):
            if len(row) >= 10 and row[9] == "Confirmed":
                has_sent = row[12].upper() == "TRUE" if len(row) > 12 else False
                if not has_sent:
                    try:
                        apt_time = TZ.localize(datetime.datetime.strptime(f"{row[5]} {row[6]}", "%d-%m-%Y %I:%M %p"))
                        if time_lower <= apt_time <= time_upper:
                            reminders.append({
                                "row": i + 2, "mobile": row[2], "name": row[1], 
                                "doctor": row[4], "date": row[5], "time": row[6]
                            })
                    except Exception: pass
        return reminders
    except Exception as e:
        logger.error(f"Reminder fetch error: {e}")
        return []

def mark_reminder_sent(row_index: int):
    try:
        sheet = get_sheets_service()
        sheet.spreadsheets().values().update(
            spreadsheetId=GOOGLE_SHEET_ID, 
            range=f"Sheet1!M{row_index}", 
            valueInputOption="RAW", 
            body={"values": [["TRUE"]]}
        ).execute()
    except Exception as e:
        logger.error(f"Mark reminder error: {e}")