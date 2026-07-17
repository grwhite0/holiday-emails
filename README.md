# Sleepy Saturday Holiday Emails — Railway Cron Job

Sends the discount-code alerts and pajama order-deadline sequence automatically,
by checking today's date against a hardcoded calendar and sending via Gmail SMTP.

## 1. Get a Gmail App Password (required — your normal password won't work for SMTP)

1. On the Google account for **hello@sleepysaturday.com** (or whichever account sends these),
   go to https://myaccount.google.com/security
2. Turn on **2-Step Verification** if it isn't already on (App Passwords require it).
3. Go to https://myaccount.google.com/apppasswords
4. Create a new App Password (name it something like "Railway Holiday Emails").
5. Copy the 16-character password it gives you — you'll only see it once.

## 2. Deploy to Railway

1. Push this folder to a GitHub repo (or use `railway up` from the CLI directly in this folder).
2. In Railway, create a **New Project → Deploy from GitHub repo** (or from local via CLI).
3. In the service settings, go to **Settings → Cron Schedule** and set it to run **daily**, e.g.:
   ```
   0 8 * * *
   ```
   (This runs at 8:00 AM UTC every day — adjust for your timezone. Railway cron jobs run once per
   schedule trigger and exit, which fits this script perfectly since it just checks-and-sends.)
4. Under **Variables**, add:
   - `GMAIL_ADDRESS` = hello@sleepysaturday.com
   - `GMAIL_APP_PASSWORD` = the 16-character app password from step 1
   - `TO_EMAIL` = hello@sleepysaturday.com (or wherever you want it delivered — can be the same address)
5. Deploy. Railway will run `python main.py` on the schedule automatically.

## 3. Test it before relying on it

Trigger a manual run from the Railway dashboard (or `railway run python main.py` locally with the
env vars set) on a day that doesn't match any calendar date — it should print
`No triggers scheduled today` and exit cleanly. To test the actual send, temporarily edit one
date in `TRIGGERS` in `main.py` to today's date, redeploy, confirm the email arrives, then revert.

## 4. Updating the calendar

All dates are hardcoded in `main.py` under `TRIGGERS`. This covers 2026–2027 only — you'll need to
add next year's dates for each holiday when this cycle ends. Each entry is a dict with a `date`,
a `type` (`discount`, `deadline_initial`, `checkin`, or `reminder`), and the relevant holiday info.

## Notes

- All dates already have the "if it lands on a weekend, send the Friday before" rule baked in.
- The Christmas order-deadline's initial draft email was skipped because its scheduled send date
  (Jul 2, 2026) had already passed by the time this was built — send that one manually now if you
  haven't already.
- This script doesn't track "already sent" state — if Railway's cron somehow fires twice on the same
  day you'd get a duplicate. Railway's cron jobs are single-fire per schedule, so this is unlikely,
  but flagging it in case you want to add idempotency later (e.g. writing sent dates to a small
  key-value store).
