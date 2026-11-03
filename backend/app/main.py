
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.interventions import router as intervention_router
from app.api.reviews import router as review_router
from app.api.reviews import queue_router as review_queue_router
from app.api.dashboard import router as dashboard_router
from app.api.data_quality import router as data_quality_router

from app.api.employees import router as employee_router

app = FastAPI(
    title="Yotta Employee Retention Support System",
    description=(
        "An explainable employee support assessment "
        "and intervention management application."
    ),
    version="1.0.0",
)

# Allow the React development server to communicate with FastAPI.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(employee_router)
app.include_router(intervention_router)
app.include_router(review_router)
app.include_router(review_queue_router)
app.include_router(dashboard_router)
app.include_router(data_quality_router)


@app.get("/")
def root():
    return {
        "message": "Yotta Employee Retention Support API is running."
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "employee-retention-api",
    }
