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
from app.web.routes import router as web_router

app.include_router(web_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
