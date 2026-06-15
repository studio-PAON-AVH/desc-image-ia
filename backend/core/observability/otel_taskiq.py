"""Middleware taskiq : un span par tâche, relié à la trace de la requête API.

Le contexte de trace est injecté dans les labels du message côté producteur
(pre_send) et extrait côté worker (pre_execute) : l'upload d'un EPUB et son
traitement par le worker forment ainsi une seule trace de bout en bout dans
Tempo, même si les deux tournent dans des conteneurs différents.
"""

import logging

from opentelemetry import context as otel_context
from opentelemetry import propagate, trace
from opentelemetry.trace import Span, SpanKind, Status, StatusCode
from taskiq import TaskiqMiddleware
from taskiq.message import TaskiqMessage
from taskiq.result import TaskiqResult

logger = logging.getLogger(__name__)


class OtelMiddleware(TaskiqMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self._tracer = trace.get_tracer(__name__)
        # Spans en cours, par task_id : l'instance du middleware est partagée
        # entre toutes les tâches concurrentes du worker, un simple attribut
        # self.span serait écrasé par la tâche suivante.
        self._inflight: dict[str, tuple[Span, object]] = {}

    def pre_send(self, message: TaskiqMessage) -> TaskiqMessage:
        propagate.inject(message.labels)
        return message

    def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        parent = propagate.extract(message.labels)
        span = self._tracer.start_span(
            message.task_name, context=parent, kind=SpanKind.CONSUMER
        )
        span.set_attribute("taskiq.task_id", message.task_id)
        span.set_attribute("taskiq.task_name", message.task_name)
        token = otel_context.attach(trace.set_span_in_context(span))
        self._inflight[message.task_id] = (span, token)
        return message

    def on_error(
        self,
        message: TaskiqMessage,
        result: TaskiqResult,
        exception: BaseException,
    ) -> None:
        entry = self._inflight.get(message.task_id)
        if entry is None:
            return
        span, _ = entry
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))

    def post_execute(self, message: TaskiqMessage, result: TaskiqResult) -> None:
        # Toujours appelé par le receiver taskiq, y compris après on_error :
        # c'est ici (et seulement ici) que le span est terminé.
        entry = self._inflight.pop(message.task_id, None)
        if entry is None:
            return
        span, token = entry
        if not result.is_err:
            span.set_status(Status(StatusCode.OK))
        span.end()
        otel_context.detach(token)
