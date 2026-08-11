import datetime
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from config import MISTRAL_API_KEY, DOCTORS, logger
from schemas import ValidationResult
from prompts import (
    main_menu_prompt, select_doctor_prompt, select_date_prompt,
    custom_date_prompt, generate_review_prompt, edit_menu_prompt
)
from google_tools import (
    get_slots_with_status, create_appointment, generate_appointment_id,
    find_appointment_by_mobile, cancel_appointment_in_system,
    acquire_pending_lock, verify_and_clear_lock, get_patient_history, update_appointment
)

llm = ChatMistralAI(model="mistral-small-latest", temperature=0, mistral_api_key=MISTRAL_API_KEY)
structured_llm = llm.with_structured_output(ValidationResult)

validation_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a strict data validation assistant for a Clinic Booking System. Do not chat.\n"
               "Current Date: {current_date}\n\nRULES FOR THIS STEP:\n{rules}\n\n"
               "Extract the value exactly. If invalid, set is_valid to False."),
    ("user", "User Input: {user_input}")
])
validation_chain = validation_prompt | structured_llm

sessions = {}

def get_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = {"state": "MAIN_MENU", "data": {}}
    return sessions[session_id]

def extract_validation(res):
    if res is None: return False, None
    is_valid = res.get("is_valid") if isinstance(res, dict) else getattr(res, "is_valid", False)
    val = res.get("extracted_value") if isinstance(res, dict) else getattr(res, "extracted_value", None)
    return is_valid, val

def classify_intent(msg: str) -> str:
    """Safely maps natural language and numbers to menu options without blocking the user."""
    msg_lower = msg.lower().strip()
    
    if msg_lower in ["1", "book", "book appointment", "i want an appointment", "appointment book karna hai"]:
        return "1"
    if msg_lower in ["2", "check", "check appointment", "my appointment", "mera appointment"]:
        return "2"
    if msg_lower in ["3", "reschedule", "reschedule appointment", "change appointment", "change my appointment", "appointment change karna hai", "move my appointment"] or "tomorrow" in msg_lower or "change it to" in msg_lower:
        return "3"
    if msg_lower in ["4", "cancel", "cancel appointment", "cancel my appointment", "i want to cancel", "appointment cancel karna hai"]:
        return "4"
        
    return None

def format_available_slots(session, slots_with_status):
    if not slots_with_status: return "❌ Sorry, no slots available. Type 0 to restart."
    msg = "Please select a time slot by number:\n\n"
    single_boxes = {'0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'}
    valid_selectable = []
    for i, slot_data in enumerate(slots_with_status, 1):
        num_str = "".join([single_boxes.get(d, d) for d in str(i)])
        msg += f"{num_str} {slot_data['time']} {slot_data['status']}\n"
        if "Available" in slot_data['status']: valid_selectable.append(str(i))
    session["data"]["displayed_slots"] = slots_with_status
    session["data"]["valid_slot_choices"] = valid_selectable
    return msg

def fetch_and_show_slots(session, session_id):
    data = session["data"]
    slots = get_slots_with_status(data.get("doctor"), data.get("date"), session_id)
    if not slots:
        session["state"] = "BOOK_DATE" if "reschedule" not in session["state"].lower() else "RESCHEDULE_DATE"
        return "❌ No available slots for this date.\n\n" + select_date_prompt
    session["state"] = "BOOK_TIME" if "reschedule" not in session["state"].lower() else "RESCHEDULE_TIME"
    return format_available_slots(session, slots)

def process_message(session_id: str, message: str) -> str:
    session = get_session(session_id)
    state = session["state"]
    data = session["data"]
    msg = message.strip()
    current_date = datetime.datetime.now().strftime("%d-%m-%Y")
    
    # Global Zero Command intercepts everything
    if msg == "0":
        session["state"] = "MAIN_MENU"
        session["data"] = {}
        return main_menu_prompt

    invalid_msg = "⚠️ Please select a valid option."

    try:
        # ---------------- MAIN MENU (State-Aware NLP Routing) ---------------- #
        if state == "MAIN_MENU":
            intent = classify_intent(msg)
            
            if not intent: 
                return invalid_msg + "\n\n" + main_menu_prompt
            
            if intent == "1":
                history = get_patient_history(session_id)
                if history:
                    data["name"] = history["name"]
                    data["age"] = history["age"]
                    data["mobile"] = session_id
                    session["state"] = "BOOK_DOCTOR"
                    return f"👋 Welcome back, {history['name']}!\n📊 Total Visits: {history['visits']}\n📅 Last Visit: {history['last_visit'] or 'N/A'}\n\nLet's book your next appointment.\n\n" + select_doctor_prompt
                
                session["state"] = "BOOK_DOCTOR"
                return select_doctor_prompt
                
            elif intent == "2":
                apt = find_appointment_by_mobile(session_id)
                if not apt: return "❌ No active appointment found.\n\n" + main_menu_prompt
                session["state"] = "MANAGE_APPOINTMENT"
                data["reschedule_mobile"] = session_id
                data["doctor"] = apt["Doctor"]
                return (f"📅 {apt['Date']}\n"
                        f"⏰ {apt['Time']}\n"
                        f"👨‍⚕️ {apt['Doctor']}\n"
                        f"Status: {apt['Status']}\n\n"
                        f"1️⃣ Reschedule\n"
                        f"2️⃣ Cancel\n"
                        f"3️⃣ Main Menu")
                
            elif intent == "3":
                apt = find_appointment_by_mobile(session_id)
                if not apt: return "❌ No active appointment found to reschedule.\n\n" + main_menu_prompt
                session["state"] = "MANAGE_APPOINTMENT"
                data["reschedule_mobile"] = session_id
                data["doctor"] = apt["Doctor"]
                return (f"Please select the appointment you want to reschedule:\n"
                        f"📅 {apt['Date']}\n"
                        f"⏰ {apt['Time']}\n"
                        f"👨‍⚕️ {apt['Doctor']}\n\n"
                        f"1️⃣ Reschedule\n"
                        f"2️⃣ Cancel")
                        
            elif intent == "4":
                apt = find_appointment_by_mobile(session_id)
                if not apt: return "❌ No active appointment found to cancel.\n\n" + main_menu_prompt
                session["state"] = "CANCEL_CONFIRM"
                data["cancel_mobile"] = session_id
                return (f"Your appointment:\n"
                        f"📅 {apt['Date']}\n"
                        f"⏰ {apt['Time']}\n"
                        f"👨‍⚕️ {apt['Doctor']}\n\n"
                        f"Are you sure you want to cancel?\n"
                        f"1️⃣ Yes, Cancel\n"
                        f"2️⃣ No")

        # ---------------- MANAGE APPOINTMENT ---------------- #
        elif state == "MANAGE_APPOINTMENT":
            if msg == "1":
                session["state"] = "RESCHEDULE_DATE"
                return "Please select a new date.\n\n" + select_date_prompt
            elif msg == "2":
                session["state"] = "CANCEL_CONFIRM"
                return "Are you sure you want to cancel?\n1️⃣ Yes, Cancel\n2️⃣ No"
            elif msg == "3":
                session["state"] = "MAIN_MENU"
                return main_menu_prompt
            return "⚠️ Please reply with 1 to Reschedule, 2 to Cancel, or 3 for Main Menu."

        # ---------------- DOCTOR SELECTION ---------------- #
        elif state == "BOOK_DOCTOR":
            if msg not in DOCTORS: return invalid_msg + "\n\n" + select_doctor_prompt
            data["doctor"] = DOCTORS[msg]
            session["state"] = "BOOK_DATE"
            return select_date_prompt

        # ---------------- DATE SELECTION ---------------- #
        elif state in ["BOOK_DATE", "RESCHEDULE_DATE"]:
            # Quick NLP catch for reschedule shortcut
            msg_lower = msg.lower()
            if "tomorrow" in msg_lower:
                msg = "2"
            elif "today" in msg_lower:
                msg = "1"

            if msg == "1": data["date"] = datetime.datetime.now().strftime("%d-%m-%Y")
            elif msg == "2": data["date"] = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
            elif msg == "3":
                session["state"] = "BOOK_CUSTOM_DATE" if state == "BOOK_DATE" else "RESCHEDULE_CUSTOM_DATE"
                return custom_date_prompt
            else: return "⚠️ Please select 1, 2, or 3."
            
            return fetch_and_show_slots(session, session_id)

        elif state in ["BOOK_CUSTOM_DATE", "RESCHEDULE_CUSTOM_DATE"]:
            date_str = msg.replace("/", "-").replace(".", "-")
            try:
                dt = datetime.datetime.strptime(date_str, "%d-%m-%Y").date()
                if dt < datetime.datetime.now().date(): return "⚠️ Past dates are not allowed. Try again:"
                data["date"] = dt.strftime("%d-%m-%Y")
                return fetch_and_show_slots(session, session_id)
            except ValueError: return "⚠️ Invalid format. Use DD-MM-YYYY:"

        # ---------------- TIME SELECTION ---------------- #
        elif state in ["BOOK_TIME", "RESCHEDULE_TIME"]:
            displayed = data.get("displayed_slots", [])
            valid_choices = data.get("valid_slot_choices", [])
            
            if not msg.isdigit() or msg not in valid_choices:
                return "⚠️ Please select a valid time slot from the list."
            
            selected_time = displayed[int(msg) - 1]["time"]
            
            if not acquire_pending_lock(data["doctor"], data["date"], selected_time, session_id):
                return "❌ Slot just taken. Select another:\n\n" + fetch_and_show_slots(session, session_id)
            
            data["time"] = selected_time
            if state == "RESCHEDULE_TIME":
                # Reschedule Confirmation Prompt
                session["state"] = "RESCHEDULE_CONFIRM"
                return (f"Please confirm:\n"
                        f"📅 {data['date']}\n"
                        f"⏰ {data['time']}\n"
                        f"👨‍⚕️ {data['doctor']}\n"
                        f"1️⃣ Confirm\n"
                        f"2️⃣ Cancel")
            
            if "name" in data: # Skip to reason if history exists
                session["state"] = "BOOK_REASON"
                return "Please briefly state the reason for the visit:"
                
            session["state"] = "BOOK_NAME"
            return "Please enter your Full Name:"

        # ---------------- RESCHEDULE CONFIRM ---------------- #
        elif state == "RESCHEDULE_CONFIRM":
            if msg == "1":
                if update_appointment(data["reschedule_mobile"], data["date"], data["time"]):
                    session["state"] = "MAIN_MENU"
                    return f"✅ Appointment successfully rescheduled."
                return "⚠️ System error while rescheduling. Type 0 for Menu."
            elif msg == "2":
                verify_and_clear_lock(data["doctor"], data["date"], data["time"], session_id)
                session["state"] = "MAIN_MENU"
                return main_menu_prompt
            return "⚠️ Please reply with 1 to Confirm or 2 to Cancel."

        # ---------------- PATIENT DETAILS ---------------- #
        elif state == "BOOK_NAME":
            data["name"] = msg
            session["state"] = "BOOK_MOBILE"
            return "Please enter your 10-digit Mobile Number:"

        elif state == "BOOK_MOBILE":
            clean_mobile = msg.replace(" ", "")
            if len(clean_mobile) != 10 or not clean_mobile.isdigit(): return "⚠️ Invalid mobile. Enter 10 digits:"
            data["mobile"] = clean_mobile
            session["state"] = "BOOK_AGE"
            return "Please enter your Age:"

        elif state == "BOOK_AGE":
            if not msg.isdigit() or not (1 <= int(msg) <= 120): return "⚠️ Invalid age. Enter a number (1-120):"
            data["age"] = msg
            session["state"] = "BOOK_REASON"
            return "Please enter your Reason for visit:"

        elif state == "BOOK_REASON":
            if not msg: return "Please enter your Reason for visit:"
            data["reason"] = msg
            session["state"] = "BOOK_REVIEW"
            return generate_review_prompt(**{k: data.get(k, '') for k in ['name','mobile','age','doctor','date','time','reason']})

        # ---------------- REVIEW & CONFIRMATION ---------------- #
        elif state == "BOOK_REVIEW":
            if msg == "1":
                if not verify_and_clear_lock(data["doctor"], data["date"], data["time"], session_id):
                    session["state"] = "BOOK_TIME"
                    return "❌ Slot expired. Select another:\n\n" + fetch_and_show_slots(session, session_id)
                
                data["appointment_id"] = generate_appointment_id()
                if create_appointment(data):
                    session["state"] = "MAIN_MENU"
                    return f"✅ Appointment Confirmed!\n🆔 ID: {data['appointment_id']}\n👨‍⚕️ {data['doctor']}\n📅 {data['date']} | ⏰ {data['time']}\n👤 {data['name']}\n\nType 0 for Main Menu."
                return "⚠️ System error. Type 0 to restart."
            elif msg == "2": session["state"] = "BOOK_EDIT"; return edit_menu_prompt
            elif msg == "3": 
                verify_and_clear_lock(data["doctor"], data["date"], data["time"], session_id)
                session["state"] = "MAIN_MENU"; return main_menu_prompt
            return "⚠️ Reply with 1, 2, or 3."

        elif state == "CANCEL_CONFIRM":
            if msg in ["1", "yes", "confirm", "yes, cancel"]:
                if cancel_appointment_in_system(data["cancel_mobile"]):
                    session["state"] = "MAIN_MENU"
                    return "✅ Appointment cancelled successfully."
                return "⚠️ Error cancelling. Type 0 for Menu."
            elif msg in ["2", "no", "back"]:
                session["state"] = "MAIN_MENU"
                return main_menu_prompt
            return "⚠️ Reply with 1 to Confirm or 2 to Back."

    except Exception as e:
        logger.error(f"Error in session {session_id} state {state}: {e}", exc_info=True)
        return "⚠️ An error occurred. Type 0 to restart."