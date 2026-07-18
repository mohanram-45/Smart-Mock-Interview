# Report delivery

This isolated module creates the interview PDF and sends the professional HTML email.

## Email configuration

1. Copy `.env.example` to `.env` inside this folder.
2. Enter the SMTP settings supplied by your email provider.
3. For Gmail, use an App Password rather than your normal account password. The
   example uses SSL on port 465, which works on networks that block port 587.
   A Google App Password contains 16 characters. Pasting it with or without the
   displayed spaces is supported.
4. Restart the Flask backend after changing `.env`.

The recipient enters their address in the frontend dialog. The backend validates it,
generates the same PDF used by the download action, attaches it, and sends the email.
Credentials never appear in frontend code or API responses.

## Endpoints

- `GET /api/reports/<interview_id>/pdf`
- `POST /api/reports/<interview_id>/email` with `{ "email": "name@example.com" }`

Generated PDF files are retained under `output/pdf/`.
