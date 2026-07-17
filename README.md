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

## 2b. (Optional) Set up the "suggested clients" feature

If you want the initial draft-email to include a list of past clients worth
re-contacting for each holiday, set up a Google Sheet:

1. Create a Google Sheet with a tab named `Clients` and these columns, in order:
   `Name | Email | Last Holiday Ordered | Last Order Date | Notes`

   Example row: `Jane Doe | jane@example.com | Christmas | Dec 2025 | Ordered custom red/green set, loved it`

   The `Last Holiday Ordered` value must match the holiday names used in this
   script exactly (case-insensitive is fine): `Christmas`, `Valentine's Day`,
   `Summer / 4th of July`.

2. Create a Google Cloud service account:
   - Go to https://console.cloud.google.com/ → create/select a project
   - Enable the **Google Sheets API**
   - Go to **IAM & Admin → Service Accounts → Create Service Account**
   - Once created, click it → **Keys → Add Key → Create new key → JSON**
   - This downloads a JSON file — you'll paste its entire contents into Railway

3. **Share the Google Sheet** with the service account's email address (it looks
   like `something@your-project.iam.gserviceaccount.com` — found in the JSON
   file under `client_email`). Give it Viewer access.

4. Get the **Sheet ID** from its URL:
   `https://docs.google.com/spreadsheets/d/THIS_PART_IS_THE_ID/edit`

5. In Railway, add two more variables:
   - `GOOGLE_SERVICE_ACCOUNT_JSON` = paste the *entire* contents of the JSON key file (as one line/string)
   - `CLIENT_SHEET_ID` = the sheet ID from step 4

If you skip this entirely, the emails still send fine — that section is just
left out.



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
