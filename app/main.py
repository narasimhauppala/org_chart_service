from fastapi import FastAPI
from app.routers import orgchart

app = FastAPI()
app.include_router(orgchart.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Org Chart Service!"}