# Changelog

## 0.1.1

- Fix: the default API host is now `https://helloapi.lakshyapocketlab.com` (was `api.lakshyapocketlab.com`).
- Add the `HELLO_BASE_URL` environment variable to override the API host (the `base_url` argument wins).
- README: show passing the API key explicitly first, with `HELLO_API_KEY` as the fallback.

## 0.1.0

- Initial release: sync `Hello` and async `AsyncHello` clients for the Hello `/v1` Integration API
  (ping, phone numbers, messages, media, templates, direct webhook override).
- Typed exceptions for both error envelopes, retries with backoff and `Retry-After`,
  idempotency-key-gated send retries.
