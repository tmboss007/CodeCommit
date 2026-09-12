import httpx

DEFAULT_TIMEOUT = 8.0


def http_get(url: str, **kwargs):
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    return httpx.get(url, timeout=timeout, **kwargs)
