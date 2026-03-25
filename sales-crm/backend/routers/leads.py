from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Lead, Contact, Account, Project, Stakeholder
from schemas import LeadCreate, LeadUpdate, LeadOut, ContactOut, AccountOut, ProjectOut, StakeholderOut

router = APIRouter(prefix="/leads", tags=["Leads"])


# ── CRUD ───────────────────────────────────────────────────────────────────────

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


# ── Convert ───────────────────────────────────────────────────────────────────

@router.post("/{lead_id}/convert", response_model=dict)
def convert_lead(lead_id: int, db: Session = Depends(get_db)):
    """Convert a lead into a Contact + Project automatically."""
    from models import LeadStatus, ProjectStatus
    from services.sales_cycle_manager import create_sales_cycle

    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

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

    cycle = create_sales_cycle(db, project.id)
    lead.status = LeadStatus.CONVERTED
    if contact:
        lead.contact_id = contact.id
    db.commit()

    return {
        "contact_id": contact.id if contact else None,
        "project_id": project.id,
        "sales_cycle_id": cycle.id,
    }


# ── Relationship: list related entities ────────────────────────────────────────

@router.get("/{lead_id}/contact", response_model=ContactOut)
def get_lead_contact(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.contact:
        raise HTTPException(404, "No contact linked to this lead")
    return lead.contact


@router.get("/{lead_id}/account", response_model=AccountOut)
def get_lead_account(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.account:
        raise HTTPException(404, "No account linked to this lead")
    return lead.account


@router.get("/{lead_id}/project", response_model=ProjectOut)
def get_lead_project(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if not lead.project:
        raise HTTPException(404, "No project linked to this lead")
    return lead.project


@router.get("/{lead_id}/stakeholders", response_model=List[StakeholderOut])
def get_lead_stakeholders(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return lead.stakeholders


# ── Relationship: link ────────────────────────────────────────────────────────

@router.patch("/{lead_id}/link/contact/{contact_id}", response_model=LeadOut)
def link_contact(lead_id: int, contact_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not lead or not contact:
        raise HTTPException(404, "Lead or Contact not found")
    lead.contact_id = contact_id
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}/link/account/{account_id}", response_model=LeadOut)
def link_account(lead_id: int, account_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    account = db.query(Account).filter(Account.id == account_id).first()
    if not lead or not account:
        raise HTTPException(404, "Lead or Account not found")
    lead.account_id = account_id
    db.commit()
    db.refresh(lead)
    return lead
