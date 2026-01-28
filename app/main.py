from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.products import router as products_router  # <- to
from app.api.carts import router as carts_router
from app.api.orders import router as orders_router, checkout_router
from app.api.auth import router as auth_router

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500", "http://127.0.0.1", "http://localhost", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router, prefix=settings.api_prefix)  # <- to
app.include_router(carts_router, prefix=settings.api_prefix)
app.include_router(orders_router, prefix=settings.api_prefix)
app.include_router(checkout_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)



@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}


@app.get(f"{settings.api_prefix}/hello")
def hello():
    return {"message": "Hello from Lanari API"}