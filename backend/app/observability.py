"""Structured logging + per-request correlation.

Every log line emitted from inside a request gets the ``request_id`` and
``method`` / ``path`` of that request, so grep/jq-friendly logs are possible
without a heavy tracing stack.
"""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
	return _request_id_var.get()


class _RequestContextFilter(logging.Filter):
	def filter(self, record: logging.LogRecord) -> bool:
		record.request_id = _request_id_var.get() or "-"
		return True


def configure_logging(level: str | None = None) -> None:
	"""Idempotently install a sane logging config for the API.

	Honours the ``LOG_LEVEL`` env var. Plays nicely with uvicorn's own loggers
	by attaching the request-id filter to the root logger so child loggers
	inherit it without extra wiring.
	"""

	level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
	root = logging.getLogger()
	if getattr(root, "_dishify_configured", False):
		root.setLevel(level_name)
		return

	handler = logging.StreamHandler(stream=sys.stdout)
	handler.setFormatter(
		logging.Formatter(
			fmt="%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
			datefmt="%Y-%m-%dT%H:%M:%S",
		)
	)
	handler.addFilter(_RequestContextFilter())

	root.handlers.clear()
	root.addHandler(handler)
	root.setLevel(level_name)
	root._dishify_configured = True  # type: ignore[attr-defined]

	# Keep uvicorn's noisy access log but route it through our handler so the
	# request-id appears there too.
	for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
		uv = logging.getLogger(name)
		uv.handlers = [handler]
		uv.propagate = False


class RequestIdMiddleware(BaseHTTPMiddleware):
	"""Mints (or reads) an X-Request-ID, binds it to the contextvar, and
	emits a one-line access log per request with status + latency."""

	logger = logging.getLogger("dishify.access")

	async def dispatch(self, request: Request, call_next):
		incoming = request.headers.get("x-request-id")
		request_id = incoming or uuid.uuid4().hex[:12]
		token = _request_id_var.set(request_id)
		started = time.perf_counter()
		response: Response
		try:
			response = await call_next(request)
		except Exception:
			elapsed_ms = (time.perf_counter() - started) * 1000
			self.logger.exception("%s %s -> 500 in %.1fms", request.method, request.url.path, elapsed_ms)
			_request_id_var.reset(token)
			raise
		elapsed_ms = (time.perf_counter() - started) * 1000
		response.headers["x-request-id"] = request_id
		self.logger.info(
			"%s %s -> %d in %.1fms",
			request.method,
			request.url.path,
			response.status_code,
			elapsed_ms,
		)
		_request_id_var.reset(token)
		return response
