from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.api.products import router as products_router  # <- to
from app.api.carts import router as carts_router
from app.api.orders import router as orders_router, checkout_router
from app.api.auth import router as auth_router
from app.api.media import router as media_router
from app.api.admin import router as admin_router
from app.api.shipping import router as shipping_router
from app.api.profiles import router as profiles_router

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    # Uwaga: używamy credentials, więc nie można użyć "*" w allow_origins.
    # Dodajemy typowe lokalne hosty + "null" (origin dla file:// w przeglądarce).
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1",
        "http://localhost",
        "null",
    ],
    allow_origin_regex="^.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization", "Content-Type", "Idempotency-Key"],
)

# Serwowanie plików statycznych (uploads)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(products_router, prefix=settings.api_prefix)  # <- to
app.include_router(carts_router, prefix=settings.api_prefix)
app.include_router(orders_router, prefix=settings.api_prefix)
app.include_router(checkout_router, prefix=settings.api_prefix)
app.include_router(shipping_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(media_router, prefix=settings.api_prefix)
app.include_router(profiles_router, prefix=settings.api_prefix)
app.include_router(admin_router) # Bez prefixu api, bo to admin

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_INDEX = PROJECT_ROOT / "frontend" / "index.html"

@app.get("/admin")
def admin_page():
    return FileResponse("app/static/admin/index.html")

@app.get("/store")
def store_page():
    if FRONTEND_INDEX.exists():
        return FileResponse(str(FRONTEND_INDEX))
    return {"detail": "Frontend not found"}

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}


@app.get(f"{settings.api_prefix}/hello")
def hello():
    return {"message": "Hello from Lanari API"}
