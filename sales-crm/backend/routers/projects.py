from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Project, Contact, Account, Stakeholder
from schemas import ProjectCreate, ProjectUpdate, ProjectOut, ContactOut, StakeholderOut, AccountOut, LeadOut

router = APIRouter(prefix="/projects", tags=["Projects"])


# ── CRUD ───────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ProjectOut])
def list_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Project).offset(skip).limit(limit).all()


@router.post("/", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    from services.sales_cycle_manager import create_sales_cycle
    data = payload.model_dump(exclude={"contact_ids"})
    project = Project(**data)
    if payload.contact_ids:
        contacts = db.query(Contact).filter(Contact.id.in_(payload.contact_ids)).all()
        project.contacts = contacts
    db.add(project)
    db.flush()
    create_sales_cycle(db, project.id)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    data = payload.model_dump(exclude={"contact_ids"}, exclude_none=True)
    for k, v in data.items():
        setattr(project, k, v)
    if payload.contact_ids is not None:
        contacts = db.query(Contact).filter(Contact.id.in_(payload.contact_ids)).all()
        project.contacts = contacts
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    db.delete(project)
    db.commit()


# ── Relationship: list related entities ────────────────────────────────────────

@router.get("/{project_id}/contacts", response_model=List[ContactOut])
def get_project_contacts(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    return project.contacts


@router.get("/{project_id}/stakeholders", response_model=List[StakeholderOut])
def get_project_stakeholders(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    return project.stakeholders


@router.get("/{project_id}/account", response_model=AccountOut)
def get_project_account(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.account:
        raise HTTPException(404, "No account linked to this project")
    return project.account


@router.get("/{project_id}/lead", response_model=LeadOut)
def get_project_lead(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.lead:
        raise HTTPException(404, "No lead linked to this project")
    return project.lead


# ── Relationship: link / unlink ───────────────────────────────────────────────

@router.post("/{project_id}/link/contact/{contact_id}", status_code=200)
def link_contact(project_id: int, contact_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not project or not contact:
        raise HTTPException(404, "Project or Contact not found")
    if contact not in project.contacts:
        project.contacts.append(contact)
    db.commit()
    return {"linked": True}


@router.delete("/{project_id}/unlink/contact/{contact_id}", status_code=200)
def unlink_contact(project_id: int, contact_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not project or not contact:
        raise HTTPException(404, "Project or Contact not found")
    if contact in project.contacts:
        project.contacts.remove(contact)
    db.commit()
    return {"unlinked": True}


@router.post("/{project_id}/link/stakeholder/{stakeholder_id}", status_code=200)
def link_stakeholder(project_id: int, stakeholder_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    stakeholder = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id).first()
    if not project or not stakeholder:
        raise HTTPException(404, "Project or Stakeholder not found")
    if stakeholder not in project.stakeholders:
        project.stakeholders.append(stakeholder)
    db.commit()
    return {"linked": True}


@router.delete("/{project_id}/unlink/stakeholder/{stakeholder_id}", status_code=200)
def unlink_stakeholder(project_id: int, stakeholder_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    stakeholder = db.query(Stakeholder).filter(Stakeholder.id == stakeholder_id).first()
    if not project or not stakeholder:
        raise HTTPException(404, "Project or Stakeholder not found")
    if stakeholder in project.stakeholders:
        project.stakeholders.remove(stakeholder)
    db.commit()
    return {"unlinked": True}


@router.patch("/{project_id}/link/account/{account_id}", response_model=ProjectOut)
def link_account(project_id: int, account_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    account = db.query(Account).filter(Account.id == account_id).first()
    if not project or not account:
        raise HTTPException(404, "Project or Account not found")
    project.account_id = account_id
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id}/link/lead/{lead_id}", response_model=ProjectOut)
def link_lead(project_id: int, lead_id: int, db: Session = Depends(get_db)):
    from models import Lead
    project = db.query(Project).filter(Project.id == project_id).first()
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not project or not lead:
        raise HTTPException(404, "Project or Lead not found")
    project.lead_id = lead_id
    db.commit()
    db.refresh(project)
    return project
