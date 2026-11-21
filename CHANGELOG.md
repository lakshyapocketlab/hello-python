# Changelog

## 0.1.0

- Initial release: sync `Hello` and async `AsyncHello` clients for the Hello `/v1` Integration API
  (ping, phone numbers, messages, media, templates, direct webhook override).
- Typed exceptions for both error envelopes, retries with backoff and `Retry-After`,
  idempotency-key-gated send retries.
