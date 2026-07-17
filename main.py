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
    # Christmas: deadline Jul 31, 2026. Initial draft-send date already passed (Jul 2, 2026) — not scheduled.
    {"date": "2026-07-17", "type": "checkin", "holiday": "Christmas", "deadline_date": "Jul 31, 2026"},
    {"date": "2026-07-24", "type": "reminder", "holiday": "Christmas", "deadline_date": "Jul 31, 2026"},

    {"date": "2026-09-14", "type": "deadline_initial", "holiday": "Valentine's Day", "deadline_date": "Oct 14, 2026"},
    {"date": "2026-09-30", "type": "checkin", "holiday": "Valentine's Day", "deadline_date": "Oct 14, 2026"},
    {"date": "2026-10-07", "type": "reminder", "holiday": "Valentine's Day", "deadline_date": "Oct 14, 2026"},

    {"date": "2027-02-04", "type": "deadline_initial", "holiday": "Summer / 4th of July", "deadline_date": "Mar 4, 2027"},
    {"date": "2027-02-18", "type": "checkin", "holiday": "Summer / 4th of July", "deadline_date": "Mar 4, 2027"},
    {"date": "2027-02-25", "type": "reminder", "holiday": "Summer / 4th of July", "deadline_date": "Mar 4, 2027"},
]


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

    if ttype == "deadline_initial":
        subject = f"{holiday} pajama order deadline — draft client email inside"
        body = (
            f"Hey team,\n\n"
            f"Here's the draft email to send clients about the {holiday} pajama order deadline "
            f"({deadline_date}). Take a look and send whenever you're ready.\n\n"
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
        return subject, body

    if ttype == "checkin":
        subject = f"Check-in: {holiday} order deadline in 2 weeks"
        body = (
            f"Hey team,\n\n"
            f"Just flagging that the {holiday} pajama order deadline ({deadline_date}) is 2 weeks "
            f"out. Wanted to check in on where things stand with client orders / whether the "
            f"reminder email should go out."
        )
        return subject, body

    if ttype == "reminder":
        subject = f"Reminder: {holiday} order deadline in 1 week"
        body = (
            f"Hey team,\n\n"
            f"Reminder — the {holiday} pajama order deadline ({deadline_date}) is next week. "
            f"Last call to get client orders in / send a final nudge if needed."
        )
        return subject, body

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
