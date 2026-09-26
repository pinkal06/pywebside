# WhatsApp Phase 9

Phase 9 uses `DevelopmentWhatsAppProvider` only. It writes a
`WhatsAppNotification` record and a masked log entry; it never makes an HTTP
request and sends no real WhatsApp messages.

Users can opt in from `/accounts/notifications/` or the profile editor. A
phone number and explicit opt-in are required; otherwise the record is marked
`SKIPPED`. Notification idempotency prevents repeated records for the same
user, event type, and reference.

Administrators can review logs at `/admin-panel/whatsapp/` and retry failed
records with a CSRF-protected POST action. Retry remains in development mode.

## Future provider integration

Set `WHATSAPP_PROVIDER`, `WHATSAPP_ENABLED`, `FIVEMINUTES_API_URL`, and
`FIVEMINUTES_API_KEY` only when a provider has been selected and its official
documentation is available. Do not put credentials in source control.

TODO - Future WhatsApp API Integration:

- Add a provider adapter implementing `WhatsAppProvider`.
- Confirm the provider's official authentication, payload, templates, and
  webhook/idempotency requirements.
- Do not assume the 5MinutesAPI endpoint or invent headers/request fields.
