from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(title="Economic Analytics Engine API")
app.include_router(router)
