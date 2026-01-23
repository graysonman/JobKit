"""
CRUD API for company research.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import Company
from ..schemas import CompanyCreate, CompanyUpdate, CompanyResponse

router = APIRouter()

@router.get("/", response_model=List[CompanyResponse])
def list_companies(
    skip: int = 0,
    limit: int = 100,
    size: Optional[str] = None,
    min_priority: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List companies with optional filters."""
    query = db.query(Company)

    if size:
        query = query.filter(Company.size == size)
    if min_priority is not None:
        query = query.filter(Company.priority >= min_priority)

    # TODO Phase 6: Add search by tech_stack
    # TODO Phase 6: Add sorting options

    return query.order_by(Company.priority.desc()).offset(skip).limit(limit).all()


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: int, db: Session = Depends(get_db)):
    """Get a specific company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("/", response_model=CompanyResponse)
def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Create a new company."""
    db_company = Company(**company.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(company_id: int, company: CompanyUpdate, db: Session = Depends(get_db)):
    """Update a company."""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = company.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_company, key, value)

    db.commit()
    db.refresh(db_company)
    return db_company


@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    """Delete a company."""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(db_company)
    db.commit()
    return {"message": "Company deleted"}


# TODO Phase 4: Add endpoint to fetch company info from LinkedIn/website
# TODO Phase 6: Add /companies/{id}/applications endpoint
# TODO Phase 6: Add /companies/{id}/contacts endpoint
