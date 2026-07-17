"""
Sleepy Saturday — Holiday Email Automation
Runs once per invocation, checks today's date against the calendar below,
and sends the matching email(s) via Gmail SMTP.

Deploy this on Railway as a Cron Job service (see README.md).
"""

import os
import smtplib
import ssl
from datetime import date
from email.mime.text import MIMEText

# ---------- CONFIG (set these as Railway environment variables) ----------
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]          # the sending account, e.g. hello@sleepysaturday.com
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]  # 16-char Gmail App Password (not your normal password)
TO_EMAIL = os.environ.get("TO_EMAIL", GMAIL_ADDRESS)   # defaults to sending to itself

# Optional — only needed if you want the "suggested clients to reach out to" section.
# If these aren't set, that section is just skipped (nothing breaks).
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")  # full JSON key, as a string
CLIENT_SHEET_ID = os.environ.get("CLIENT_SHEET_ID")  # the Google Sheet ID from its URL
CLIENT_SHEET_RANGE = os.environ.get("CLIENT_SHEET_RANGE", "Clients!A2:E1000")

# ---------- HOLIDAY CALENDAR ----------
# type: "discount" | "deadline_initial" | "checkin" | "reminder"
# All dates already have the weekend-backtrack rule applied (weekend dates moved to preceding Friday).

TRIGGERS = [
    # --- Discount code alerts (10 days before each holiday) ---
    {"date": "2026-08-28", "type": "discount", "holiday": "Labor Day", "holiday_date": "Sep 7, 2026"},
    {"date": "2026-10-21", "type": "discount", "holiday": "Halloween", "holiday_date": "Oct 31, 2026"},
    {"date": "2026-11-16", "type": "discount", "holiday": "Thanksgiving", "holiday_date": "Nov 26, 2026"},
    {"date": "2026-11-17", "type": "discount", "holiday": "Black Friday", "holiday_date": "Nov 27, 2026"},
    {"date": "2026-11-20", "type": "discount", "holiday": "Cyber Monday", "holiday_date": "Nov 30, 2026"},
    {"date": "2026-12-15", "type": "discount", "holiday": "Christmas", "holiday_date": "Dec 25, 2026"},
    {"date": "2026-12-22", "type": "discount", "holiday": "New Year's Day", "holiday_date": "Jan 1, 2027"},
    {"date": "2027-02-04", "type": "discount", "holiday": "Valentine's Day", "holiday_date": "Feb 14, 2027"},
    {"date": "2027-03-05", "type": "discount", "holiday": "St. Patrick's Day", "holiday_date": "Mar 17, 2027"},
    {"date": "2027-03-18", "type": "discount", "holiday": "Easter", "holiday_date": "Mar 28, 2027"},
    {"date": "2027-04-29", "type": "discount", "holiday": "Mother's Day", "holiday_date": "May 9, 2027"},
    {"date": "2027-05-21", "type": "discount", "holiday": "Memorial Day", "holiday_date": "May 31, 2027"},
    {"date": "2027-06-10", "type": "discount", "holiday": "Father's Day", "holiday_date": "Jun 20, 2027"},
    {"date": "2027-06-24", "type": "discount", "holiday": "4th of July", "holiday_date": "Jul 4, 2027"},

    # --- Pajama order-deadline sequence (Christmas, Valentine's, Summer/4th of July) ---
    # Each holiday gets 3 emails, all containing the draft client email:
    # 2 weeks before deadline (initial) -> 1 week before (follow-up) -> day of (final call)
    {"date": "2026-07-17", "type": "two_week", "holiday": "Christmas", "deadline_date": "Jul 31, 2026"},
    {"date": "2026-07-24", "type": "one_week", "holiday": "Christmas", "deadline_date": "Jul 31, 2026"},
    {"date": "2026-07-31", "type": "day_of", "holiday": "Christmas", "deadline_date": "Jul 31, 2026"},

    {"date": "2026-09-30", "type": "two_week", "holiday": "Valentine's Day", "deadline_date": "Oct 14, 2026"},
    {"date": "2026-10-07", "type": "one_week", "holiday": "Valentine's Day", "deadline_date": "Oct 14, 2026"},
    {"date": "2026-10-14", "type": "day_of", "holiday": "Valentine's Day", "deadline_date": "Oct 14, 2026"},

    {"date": "2027-02-18", "type": "two_week", "holiday": "Summer / 4th of July", "deadline_date": "Mar 4, 2027"},
    {"date": "2027-02-25", "type": "one_week", "holiday": "Summer / 4th of July", "deadline_date": "Mar 4, 2027"},
    {"date": "2027-03-04", "type": "day_of", "holiday": "Summer / 4th of July", "deadline_date": "Mar 4, 2027"},
]


def get_suggested_clients(holiday):
    """
    Reads the client sheet and returns clients whose last order was for this
    same holiday (repeat customers worth reaching out to again). Returns an
    empty list if Sheets isn't configured or anything goes wrong — this
    section is a bonus, not a dependency for the email to send.

    Expected sheet columns (in order): Name | Email | Last Holiday Ordered |
    Last Order Date | Notes
    """
    if not (GOOGLE_SERVICE_ACCOUNT_JSON and CLIENT_SHEET_ID):
        return []

    try:
        import json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        credentials = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
        )
        service = build("sheets", "v4", credentials=credentials)
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=CLIENT_SHEET_ID, range=CLIENT_SHEET_RANGE)
            .execute()
        )
        rows = result.get("values", [])

        matches = []
        for row in rows:
            # Pad short rows so index access doesn't blow up
            row = row + [""] * (5 - len(row))
            name, email, last_holiday, last_order_date, notes = row[:5]
            if last_holiday.strip().lower() == holiday.strip().lower():
                matches.append(
                    {
                        "name": name,
                        "email": email,
                        "last_order_date": last_order_date,
                        "notes": notes,
                    }
                )
        return matches
    except Exception as e:
        print(f"Warning: couldn't fetch client suggestions ({e}). Skipping that section.")
        return []


def format_client_suggestions(clients):
    if not clients:
        return ""

    lines = ["\n---\nPeople to consider reaching out to (ordered this holiday before):\n"]
    for c in clients:
        line = f"- {c['name']} ({c['email']})"
        if c["last_order_date"]:
            line += f" — last ordered {c['last_order_date']}"
        if c["notes"]:
            line += f"\n  Notes: {c['notes']}"
        lines.append(line)
    return "\n".join(lines)


def build_email(trigger):
    holiday = trigger["holiday"]
    ttype = trigger["type"]

    if ttype == "discount":
        holiday_date = trigger["holiday_date"]
        subject = f"{holiday} is coming — time for a discount code"
        body = (
            f"Hey team,\n\n"
            f"{holiday} is 10 days away (falls on {holiday_date}). "
            f"Let's get a discount code created and ready to go for the promo push — "
            f"something like HOLIDAY20 or SLEEPY-XMAS15 works well as a format.\n\n"
            f"Thanks!"
        )
        return subject, body

    deadline_date = trigger["deadline_date"]
    suggestions_block = format_client_suggestions(get_suggested_clients(holiday))

    draft_block = (
        f"---\n"
        f"Draft client email:\n\n"
        f"Subject: Order deadline for {holiday} pajamas — let's get you stocked up\n\n"
        f"Hi [Client Name],\n\n"
        f"Wanted to reach out because our deadline for ordering sets in time for {holiday} is "
        f"coming up on {deadline_date}. We'd love to put together a holiday-themed design set "
        f"for you, or just get some additional orders in so you have ample stock heading into "
        f"the busy season.\n\n"
        f"Let us know if you'd like to get started!\n\n"
        f"Best,\n"
        f"Sleepy Saturday"
    )

    if ttype == "two_week":
        subject = f"{holiday} pajama order deadline in 2 weeks — draft client email inside"
        intro = (
            f"Hey team,\n\n"
            f"The {holiday} pajama order deadline ({deadline_date}) is 2 weeks out. Here's the "
            f"draft email to send clients — take a look and send whenever you're ready.\n\n"
        )
        return subject, intro + draft_block + suggestions_block

    if ttype == "one_week":
        subject = f"{holiday} pajama order deadline in 1 week — draft client email inside"
        intro = (
            f"Hey team,\n\n"
            f"Reminder — the {holiday} pajama order deadline ({deadline_date}) is next week. "
            f"If the draft hasn't gone out yet, here it is again:\n\n"
        )
        return subject, intro + draft_block + suggestions_block

    if ttype == "day_of":
        subject = f"{holiday} pajama order deadline is today — draft client email inside"
        intro = (
            f"Hey team,\n\n"
            f"Today ({deadline_date}) is the last day for clients to order in time for {holiday}. "
            f"Last call — here's the draft one more time if you need it:\n\n"
        )
        return subject, intro + draft_block + suggestions_block

    raise ValueError(f"Unknown trigger type: {ttype}")


def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = TO_EMAIL

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls(context=context)
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [TO_EMAIL], msg.as_string())


def main():
    today = date.today().isoformat()
    matches = [t for t in TRIGGERS if t["date"] == today]

    if not matches:
        print(f"[{today}] No triggers scheduled today. Nothing to send.")
        return

    for trigger in matches:
        subject, body = build_email(trigger)
        send_email(subject, body)
        print(f"[{today}] Sent: {subject}")


if __name__ == "__main__":
    main()
