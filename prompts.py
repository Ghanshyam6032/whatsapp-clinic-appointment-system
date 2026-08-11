main_menu_prompt = (
    "👋 Welcome to the Clinic AI Assistant.\n\n"
    "Please select an option by replying with a number:\n"
    "1️⃣ Book Appointment\n"
    "2️⃣ Check Appointment\n"
    "3️⃣ Reschedule Appointment\n"
    "4️⃣ Cancel Appointment"
)

select_doctor_prompt = (
    "Please select a Doctor:\n"
    "1️⃣ Dr. Patel\n"
    "2️⃣ Dr. Shah\n"
    "3️⃣ Dr. Mehta"
)

select_date_prompt = (
    "Please select a Date:\n"
    "1️⃣ Today\n"
    "2️⃣ Tomorrow\n"
    "3️⃣ Custom Date"
)

custom_date_prompt = "Please enter the date strictly in this format: DD-MM-YYYY\n(Example: 08-08-2026)"

def generate_review_prompt(name, mobile, age, doctor, date, time, reason):
    return (
        f"📋 *Review your Appointment Details:*\n\n"
        f"👤 Name: {name}\n"
        f"📱 Mobile: {mobile}\n"
        f"🎂 Age: {age}\n"
        f"👨‍⚕️ Doctor: {doctor}\n"
        f"📅 Date: {date}\n"
        f"⏰ Time: {time}\n"
        f"⏳ Duration: 20 mins\n"
        f"📝 Reason: {reason}\n\n"
        f"Please select an option:\n"
        f"1️⃣ Confirm\n"
        f"2️⃣ Edit\n"
        f"3️⃣ Cancel"
    )

edit_menu_prompt = (
    "What would you like to edit?\n"
    "1️⃣ Doctor\n"
    "2️⃣ Date & Time\n"
    "3️⃣ Name\n"
    "4️⃣ Mobile\n"
    "5️⃣ Reason\n"
    "6️⃣ Age\n"
    "7️⃣ Back to Review"
)