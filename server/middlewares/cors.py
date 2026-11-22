ALLOWED_ORIGINS = [
    "http://127.0.0.1:18420",
    "http://localhost:18420",
    "http://127.0.0.1:18421",
    "http://localhost:18421",
]


def setup_cors(app):
    from fastapi import Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def block_untrusted_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in ALLOWED_ORIGINS:
            return JSONResponse(
                status_code=403,
                content={"detail": f"Origin '{origin}' is not allowed"},
            )
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )