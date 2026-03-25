from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Lead, Contact, Account, Project
from schemas import LeadCreate, LeadUpdate, LeadOut

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("/", response_model=List[LeadOut])
def list_leads(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Lead).offset(skip).limit(limit).all()


@router.post("/", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead


@router.put("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(lead, k, v)
    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    db.delete(lead)
    db.commit()


@router.post("/{lead_id}/convert", response_model=dict)
def convert_lead(lead_id: int, db: Session = Depends(get_db)):
    """Convert a lead into a Contact + Project automatically."""
    from models import LeadStatus, ProjectStatus
    from services.sales_cycle_manager import create_sales_cycle

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    # Create or reuse contact
    contact = db.query(Contact).filter(Contact.email == lead.email).first()
    if not contact and lead.email:
        contact = Contact(
            first_name=lead.first_name or "",
            last_name=lead.last_name or "",
            email=lead.email,
            phone=lead.phone,
            job_title=lead.company,
        )
        db.add(contact)
        db.flush()

    # Create project
    project = Project(
        name=f"{lead.company or lead.email} – Deal",
        description=lead.notes,
        account_id=lead.account_id,
        lead_id=lead.id,
        status=ProjectStatus.PROSPECT,
    )
    if contact:
        project.contacts.append(contact)
    db.add(project)
    db.flush()

    # Kick off sales cycle
    cycle = create_sales_cycle(db, project.id)

    # Update lead
    lead.status = LeadStatus.CONVERTED
    if contact:
        lead.contact_id = contact.id

    db.commit()

    return {
        "contact_id": contact.id if contact else None,
        "project_id": project.id,
        "sales_cycle_id": cycle.id,
    }
