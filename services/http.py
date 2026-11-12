"""Small retry helper. Retries only timeouts, 429 and 5xx. Never logs keys."""
import logging
import time
import requests
from services.errors import ServiceError

log = logging.getLogger("bharat_voice")


def post_with_retry(url, *, retries=2, timeout=45, what="service", **kwargs):
    last = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, timeout=timeout, **kwargs)
        except (requests.Timeout, requests.ConnectionError) as e:
            last = f"{what} did not respond (network/timeout)."
            log.warning("%s attempt %d failed: %s", what, attempt + 1, type(e).__name__)
        else:
            if r.status_code == 429 or r.status_code >= 500:
                last = f"{what} is busy (HTTP {r.status_code})."
                log.warning("%s attempt %d got HTTP %d", what, attempt + 1, r.status_code)
            else:
                return r
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    raise ServiceError(last + " Please try again in a moment.")
