"""Explicit read-only connectivity checks; never generate or persist credentials."""
import json
import urllib.error
import urllib.request

from . import openrouter, sources, workflow


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def check(base_url: str, api_key: str) -> dict:
    """OpenRouter has an authenticated /key route; other APIs expose /models.

    A successful model listing alone does not prove key acceptance. Only return
    bounded, non-sensitive facts; do not expose account labels, balance or payload.
    """
    base_url = workflow.api_address(base_url)
    authenticated = openrouter.is_openrouter(base_url)
    url = base_url + ('/key' if authenticated else '/models')
    request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + api_key})
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(request, timeout=sources.TIMEOUT) as response:
        body = response.read(1024 * 1024 + 1)
    if len(body) > 1024 * 1024:
        raise ValueError('Connection-check response is too large')
    value = json.loads(body)
    if authenticated:
        if not isinstance(value, dict) or not isinstance(value.get('data'), dict) or not value['data'] or 'error' in value:
            raise ValueError('Invalid key-check response')
        return {'authenticated': True}
    models = sources.parse_api_models(value)
    return {'authenticated': False, 'models': len(models)}


def error_message(error: Exception) -> str:
    reason = error
    for _ in range(6):
        if isinstance(reason, urllib.error.HTTPError):
            if reason.code in (401, 403):
                return 'Access denied. Check the API key and its permissions.'
            if reason.code == 404:
                return 'Connection check endpoint not found. Check the API base URL.'
            if reason.code == 429:
                return 'Rate limited (429). Try again later; your entries remain in the form.'
            return 'Connection check failed. The service returned an error; try again later.'
        if isinstance(reason, (urllib.error.URLError, TimeoutError)):
            return workflow.model_error('api', reason)
        if reason.__cause__ is None:
            break
        reason = reason.__cause__
    return 'The service returned an unreadable connection-check response.'
