import logging
from rest_framework.views import exception_handler

logger = logging.getLogger("rest_framework")

def debug_exception_handler(exc, context):
    """
    Extend DRF's default handler to also log response data.
    """
    response = exception_handler(exc, context)

    view = context.get("view")
    view_name = view.__class__.__name__ if view else "UnknownView"

    if response is not None:
        logger.error(
            "DRF Exception in %s: %s | Response data: %s",
            view_name,
            exc,
            response.data,
        )
    else:
        logger.exception("Unhandled exception in %s", view_name, exc_info=exc)

    return response
