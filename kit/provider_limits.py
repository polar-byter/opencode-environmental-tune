"""Classify public provider errors without retaining bodies, keys or reasoning."""
import re


def quota_error(error) -> bool:
    if not isinstance(error, dict):
        return False
    if any(type(error.get(key)) is int and error[key] == 429 for key in ('status', 'statusCode', 'code')):
        return True
    kind = str(error.get('type', error.get('name', ''))).lower()
    if kind in ('provider.quota', 'freeusagelimiterror', 'ratelimiterror', 'insufficientquotaerror'):
        return True
    message = error.get('message', '')
    return isinstance(message, str) and bool(re.search(
        r'\b429\b|rate[ _-]?limit(?:ed| exceeded| reached)?|(?:daily|free|usage) (?:usage )?(?:limit|quota) (?:exceeded|exhausted|reached)|insufficient[_ ]quota',
        message, re.IGNORECASE))
