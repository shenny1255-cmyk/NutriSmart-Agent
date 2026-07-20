# Design: Email Verification (Phase 2 of auth hardening)

**Date:** 2026-07-20
**Status:** Approved
**Branch:** `feat/email-verification` (stacked on `feat/auth-hardening` / PR #6)

## 1. Goal

When a user signs up, send a verification link to their email so they can confirm
the address. Delivery is **real SMTP** (configured by the user in `.env`), with a
**console fallback** when SMTP is not configured so the feature works offline and
tests never depend on a live mail server.

Enforcement is **soft**: unverified users can still log in and use the app, but see
a "please verify your email" banner with a **Resend** button.

## 2. Decisions

- **Token:** stateless signed JWT (reuse `python-jose`), claims
  `{sub: user_id, purpose: "verify_email", exp: now + 24h}`. No DB table, no cleanup
  job; resend just mints a fresh token. Verify decodes, checks purpose, marks the user.
- **Sending:** `services/email.py` with `send_verification_email(to, link)`.
  If SMTP env vars are set → send via `smtplib` (STARTTLS). Otherwise → log the link
  (`logging.getLogger`) at INFO. The caller never knows or cares which path ran.
- **State:** add `email_verified BOOLEAN NOT NULL DEFAULT false` to `users`.

## 3. Configuration (`backend/app/config.py` + `.env`)

```env
SMTP_HOST=            # e.g. smtp.gmail.com  (empty → console fallback)
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=        # Gmail: an App Password, NOT the account password
SMTP_FROM=NutriSmart <no-reply@nutrismart.local>
APP_BASE_URL=http://localhost:5173   # base for the verify link
```

The user fills SMTP credentials in themselves; the code only reads env vars.

## 4. Data model & migration

- `models.py`: `User.email_verified = Column(Boolean, nullable=False, server_default="false")`.
- New `db/migrations/12_email_verified.sql`:
  `ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false;`
- Apply to the already-running DB via `docker exec … psql -f`.
- Demo seed (`routers/demo.py`): set seeded accounts `email_verified = true`.

## 5. Backend components

### `app/security.py` (edit)
- `create_verification_token(user_id) -> str` — JWT with `purpose="verify_email"`, 24h exp.
- `decode_verification_token(token) -> str | None` — returns user_id iff signature valid,
  not expired, and `purpose == "verify_email"`; else `None`.

### `app/services/email.py` (new)
- `send_verification_email(to_email: str, verify_link: str) -> None`
  - SMTP configured → build a MIME message (Vietnamese subject/body with the link),
    send via `smtplib.SMTP` + STARTTLS + login. On failure, log a warning and fall
    back to logging the link (never raise into the request path).
  - Not configured → log the link at INFO.
- `build_verify_link(token) -> str` → `{APP_BASE_URL}/verify?token={token}`.

### `app/routers/auth.py` (edit)
| Endpoint | Behavior |
|---|---|
| `POST /auth/register` | After commit: mint token → `send_verification_email`. Response unchanged (still returns `access_token`). Sending failure must not fail registration. |
| `GET /auth/verify?token=` | `decode_verification_token`; if valid → set `email_verified=true` (idempotent), return `{status: "verified"}`; invalid/expired → `400`. |
| `POST /auth/resend-verification` (auth) | If already verified → `{status: "already_verified"}`; else mint + send, return `{status: "sent"}`. |
| `GET /auth/me` | Include `email_verified` (add to `UserOut`). |

## 6. Frontend

- `lib/api.js`: `verifyEmail(token) → GET /auth/verify?token=`; `resendVerification() → POST /auth/resend-verification`.
- `pages/Verify.jsx` (new, **public** route `/verify`): reads `?token=`, calls
  `verifyEmail`, shows states — verifying / success (link to app) / failed (with a
  "go to login" link). Wrapped so it works whether or not logged in.
- `App.jsx`: add `/verify` route (public, outside `RequireAuth`).
- `components/VerifyBanner.jsx` (new): shown in `Shell` when `me.email_verified === false`.
  Amber bar: "Hãy xác minh email của bạn" + **Gửi lại** button → `resendVerification()`,
  shows "đã gửi" / "đã xác minh". Shell fetches `api.me()` on mount for the flag.

## 7. Error handling

| Case | Behavior |
|---|---|
| SMTP down / bad creds | `email.py` catches, logs warning, falls back to console log; registration still succeeds. |
| Invalid/expired verify token | `GET /auth/verify` → 400; Verify page shows "link hết hạn" + resend hint. |
| Already verified | verify + resend are idempotent, friendly status. |
| Resend spam | Out of scope (no throttle) — YAGNI. |

## 8. Testing

- **Unit — security:** `create/decode_verification_token` round-trip; expired token → None;
  wrong-purpose token (an access token) → None.
- **Unit — email service:** with SMTP unset, `send_verification_email` logs the link and
  does not raise; `build_verify_link` shape. SMTP path: monkeypatch `smtplib.SMTP`, assert
  `sendmail` called with the link; SMTP raising → falls back, no exception.
- **Integration:** register → `me.email_verified == false`; call `/auth/verify` with a
  freshly minted token → 200 → `me.email_verified == true`; bad token → 400; resend when
  verified → `already_verified`. `email.send` monkeypatched — no real mail in tests.

## 9. Out of scope (YAGNI)

Resend throttling/rate-limit, hard-blocking login until verified, changing email address,
HTML email templates (plain-text link is enough), background/async send queue.
