from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth import router as auth_router
from app.vehicles import router as vehicles_router

app = FastAPI(title="Car Dealership Inventory System")
app.include_router(auth_router)
app.include_router(vehicles_router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, error):
    """Keep submitted passwords and other input out of validation responses."""
    return JSONResponse(
        status_code=422,
        content={"detail": [
            {key: item[key] for key in ("loc", "msg", "type")}
            for item in error.errors()
        ]},
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}
