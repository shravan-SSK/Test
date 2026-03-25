from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Contact, Account
from schemas import ContactCreate, ContactUpdate, ContactOut

router = APIRouter(prefix="/contacts", tags=["Contacts"])


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


@router.get("/search/email/{email}", response_model=ContactOut)
def find_by_email(email: str, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.email == email.lower()).first()
    if not contact:
        raise HTTPException(404, "No contact with that email")
    return contact
