from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.api.v1 import admin, auth, nodes, shares, storage, trash
from app.core.config import settings
from app.core.errors import AppError, app_error_handler
from app.services.admin_bootstrap import ensure_single_admin


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_single_admin()
    yield

app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": "VALIDATION_ERROR", "message": "提交内容有误，请检查后重试", "details": jsonable_encoder(exc.errors())},
    )


@app.get("/health", tags=["系统"])
async def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(nodes.router, prefix=settings.api_prefix)
app.include_router(storage.router, prefix=settings.api_prefix)
app.include_router(trash.router, prefix=settings.api_prefix)
app.include_router(shares.router, prefix=settings.api_prefix)
app.include_router(shares.public_router, prefix=settings.api_prefix)
