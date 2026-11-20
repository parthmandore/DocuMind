"""Processing Jobs API Routes

Endpoints for inspecting background ingestion jobs and processing status.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db.base import get_db
from backend.db.models import ProcessingJob
from backend.api.schemas import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("", response_model=List[JobResponse])
def list_jobs(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List recent background processing jobs."""
    jobs = (
        db.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [JobResponse.model_validate(j) for j in jobs]

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Retrieve details and status for a specific processing job."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )
    return JobResponse.model_validate(job)
