from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    debug=settings.DEBUG,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
from app.api.v1.router import api_router
from app.api.routes import router as page_router

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(page_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
