"""Remplace fastapi_limiter.depends.RateLimiter, dont le __call__ plante avec les
versions actuelles de FastAPI/Starlette : il boucle sur request.app.routes en
lisant route.path pour calculer un index route/dépendance, mais depuis
l'introduction des _IncludedRouter (app.include_router) certaines entrées de
app.routes n'ont plus cet attribut -> AttributeError non catché sur CHAQUE appel
(404/500 systématique sur /api/auth/register et /api/auth/login). fastapi-limiter
0.2.0 (dernière version connue) n'a pas suivi ce changement interne.

Cet index route/dépendance ne sert qu'à distinguer plusieurs RateLimiter posés sur
UNE MÊME route : ici chaque route n'en a qu'un, et l'identifiant par défaut
(IP + chemin de la requête) est déjà unique par (client, route) — la boucle sur
app.routes n'apporte donc rien pour cet usage.
"""

from typing import Callable

from fastapi import HTTPException, Request, Response
from pyrate_limiter import Limiter
from starlette.status import HTTP_429_TOO_MANY_REQUESTS


async def default_identifier(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0]
    elif request.client:
        ip = request.client.host
    else:
        ip = "127.0.0.1"
    return f"{ip}:{request.scope['path']}"


class RateLimiter:
    def __init__(
        self,
        limiter: Limiter,
        identifier: Callable = default_identifier,
        blocking: bool = False,
    ):
        self.limiter = limiter
        self.identifier = identifier
        self.blocking = blocking

    async def __call__(self, request: Request, response: Response) -> None:
        key = await self.identifier(request)
        success = await self.limiter.try_acquire_async(key, blocking=self.blocking)
        if not success:
            raise HTTPException(HTTP_429_TOO_MANY_REQUESTS, "Too Many Requests")
