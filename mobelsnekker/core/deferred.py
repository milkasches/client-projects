"""Run work after the HTTP response has been sent to the visitor.

The WSGI server (gunicorn, uWSGI on PythonAnywhere, runserver) calls
`response.close()` only after the body is delivered, so anything hooked there
does not delay the visitor.  No threads, queues or extra services needed.
"""
import logging

from django.http import JsonResponse

log = logging.getLogger(__name__)


class DeferredJsonResponse(JsonResponse):
    def __init__(self, *args, after=(), **kwargs):
        super().__init__(*args, **kwargs)
        self._after = list(after)

    def close(self):
        super().close()
        tasks, self._after = self._after, []
        for fn in tasks:
            try:
                fn()
            except Exception:
                log.exception("Deferred task %r failed", fn)
