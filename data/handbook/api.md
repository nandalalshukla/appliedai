---
product: api
updated: 2026
---
# Developer API

## Rate limits
The API allows 600 requests per minute per API key on the Team plan and 60 per minute on the Free plan. Exceeding the limit returns HTTP 429 with a Retry-After header. Limits reset on a rolling 60 second window.

## Authentication
Every request must send an API key in the Authorization header as a bearer token. Keys are created under Settings, then Developer. A key is shown only once at creation. Rotate keys every 90 days; old keys keep working for 24 hours after rotation.

## Webhooks
Webhooks deliver events such as file.created and invoice.paid. Each delivery is signed with HMAC-SHA256 using the webhook secret. Failed deliveries are retried 5 times with exponential backoff over 24 hours, then dropped.

## Pagination
List endpoints return at most 100 items per page. Use the cursor value from the response to fetch the next page. Offsets are not supported.
