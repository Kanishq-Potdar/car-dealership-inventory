from fastapi import FastAPI

app = FastAPI(title="Car Dealership Inventory System")


@app.get("/health")
def health_check():
    return {"status": "ok"}
