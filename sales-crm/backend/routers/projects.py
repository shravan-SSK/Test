from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Project, Contact, Account
from schemas import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/projects", tags=["Projects"])


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

    # Auto-create a sales cycle for every new project
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
