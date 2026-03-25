from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import Contact, Account, Project, Lead, Stakeholder
from schemas import ContactCreate, ContactUpdate, ContactOut, AccountOut, ProjectOut, LeadOut, StakeholderOut

router = APIRouter(prefix="/contacts", tags=["Contacts"])


# ── CRUD ───────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ContactOut])
def list_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Contact).offset(skip).limit(limit).all()


@router.post("/", response_model=ContactOut, status_code=201)
def create_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"account_ids"})
    contact = Contact(**data)
    if payload.account_ids:
        accounts = db.query(Account).filter(Account.id.in_(payload.account_ids)).all()
        contact.accounts = accounts
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/search/email/{email}", response_model=ContactOut)
def find_by_email(email: str, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.email == email.lower()).first()
    if not contact:
        raise HTTPException(404, "No contact with that email")
    return contact


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, payload: ContactUpdate, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    data = payload.model_dump(exclude={"account_ids"}, exclude_none=True)
    for k, v in data.items():
        setattr(contact, k, v)
    if payload.account_ids is not None:
        accounts = db.query(Account).filter(Account.id.in_(payload.account_ids)).all()
        contact.accounts = accounts
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    db.delete(contact)
    db.commit()


# ── Relationship: list related entities ────────────────────────────────────────

@router.get("/{contact_id}/accounts", response_model=List[AccountOut])
def get_contact_accounts(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    return contact.accounts


@router.get("/{contact_id}/projects", response_model=List[ProjectOut])
def get_contact_projects(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    return contact.projects


@router.get("/{contact_id}/leads", response_model=List[LeadOut])
def get_contact_leads(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    return contact.leads


@router.get("/{contact_id}/stakeholder", response_model=Optional[StakeholderOut])
def get_contact_stakeholder(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(404, "Contact not found")
    return contact.stakeholder


# ── Relationship: link / unlink ───────────────────────────────────────────────

@router.post("/{contact_id}/link/account/{account_id}", status_code=200)
def link_account(contact_id: int, account_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    account = db.query(Account).filter(Account.id == account_id).first()
    if not contact or not account:
        raise HTTPException(404, "Contact or Account not found")
    if account not in contact.accounts:
        contact.accounts.append(account)
    db.commit()
    return {"linked": True}


@router.delete("/{contact_id}/unlink/account/{account_id}", status_code=200)
def unlink_account(contact_id: int, account_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    account = db.query(Account).filter(Account.id == account_id).first()
    if not contact or not account:
        raise HTTPException(404, "Contact or Account not found")
    if account in contact.accounts:
        contact.accounts.remove(account)
    db.commit()
    return {"unlinked": True}


@router.post("/{contact_id}/link/project/{project_id}", status_code=200)
def link_project(contact_id: int, project_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not contact or not project:
        raise HTTPException(404, "Contact or Project not found")
    if project not in contact.projects:
        contact.projects.append(project)
    db.commit()
    return {"linked": True}


@router.delete("/{contact_id}/unlink/project/{project_id}", status_code=200)
def unlink_project(contact_id: int, project_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not contact or not project:
        raise HTTPException(404, "Contact or Project not found")
    if project in contact.projects:
        contact.projects.remove(project)
    db.commit()
    return {"unlinked": True}
