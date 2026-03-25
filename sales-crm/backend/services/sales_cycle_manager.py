"""
Sales cycle management engine.

Handles:
- Stage transitions with validation
- Auto-probability assignment per stage
- Activity logging on every transition
- Next-action suggestions
"""

from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session

from models import SalesCycle, Activity, Project, SalesCycleStage, ProjectStatus


# Default win-probability per stage (can be overridden per deal)
STAGE_PROBABILITY: Dict[str, float] = {
    SalesCycleStage.PROSPECTING:    5.0,
    SalesCycleStage.QUALIFICATION:  15.0,
    SalesCycleStage.NEEDS_ANALYSIS: 25.0,
    SalesCycleStage.VALUE_PROP:     40.0,
    SalesCycleStage.PROPOSAL:       60.0,
    SalesCycleStage.NEGOTIATION:    80.0,
    SalesCycleStage.CLOSED_WON:     100.0,
    SalesCycleStage.CLOSED_LOST:    0.0,
}

# Suggested next actions per stage
STAGE_NEXT_ACTIONS: Dict[str, str] = {
    SalesCycleStage.PROSPECTING:    "Research the prospect and send an introductory email.",
    SalesCycleStage.QUALIFICATION:  "Schedule a discovery call to qualify budget, authority, need, and timeline.",
    SalesCycleStage.NEEDS_ANALYSIS: "Send a detailed questionnaire and schedule a needs-assessment meeting.",
    SalesCycleStage.VALUE_PROP:     "Prepare and deliver a customised value-proposition presentation.",
    SalesCycleStage.PROPOSAL:       "Send a formal proposal / quote and set a follow-up date.",
    SalesCycleStage.NEGOTIATION:    "Engage stakeholders, address objections, and agree on contract terms.",
    SalesCycleStage.CLOSED_WON:     "Issue contract, kick off onboarding, and hand off to customer success.",
    SalesCycleStage.CLOSED_LOST:    "Document the reason for loss and schedule a retrospective.",
}

# Valid forward transitions (backward always allowed for corrections)
VALID_TRANSITIONS = {
    SalesCycleStage.PROSPECTING:    [SalesCycleStage.QUALIFICATION, SalesCycleStage.CLOSED_LOST],
    SalesCycleStage.QUALIFICATION:  [SalesCycleStage.NEEDS_ANALYSIS, SalesCycleStage.CLOSED_LOST],
    SalesCycleStage.NEEDS_ANALYSIS: [SalesCycleStage.VALUE_PROP, SalesCycleStage.CLOSED_LOST],
    SalesCycleStage.VALUE_PROP:     [SalesCycleStage.PROPOSAL, SalesCycleStage.CLOSED_LOST],
    SalesCycleStage.PROPOSAL:       [SalesCycleStage.NEGOTIATION, SalesCycleStage.CLOSED_LOST],
    SalesCycleStage.NEGOTIATION:    [SalesCycleStage.CLOSED_WON, SalesCycleStage.CLOSED_LOST],
    SalesCycleStage.CLOSED_WON:     [],
    SalesCycleStage.CLOSED_LOST:    [SalesCycleStage.PROSPECTING],  # reopen
}


def create_sales_cycle(db: Session, project_id: int,
                       stage: SalesCycleStage = SalesCycleStage.PROSPECTING) -> SalesCycle:
    """Create a new sales cycle for a project."""
    cycle = SalesCycle(
        project_id=project_id,
        stage=stage,
        probability=STAGE_PROBABILITY[stage],
        next_action=STAGE_NEXT_ACTIONS[stage],
    )
    db.add(cycle)
    db.flush()
    _log_activity(db, cycle.id, "stage_change", "Sales cycle opened",
                  f"Deal entered {stage.value} stage.", None, stage.value)
    return cycle


def advance_stage(db: Session, cycle_id: int,
                  new_stage: SalesCycleStage,
                  notes: Optional[str] = None) -> Tuple[SalesCycle, str]:
    """
    Attempt to move a sales cycle to a new stage.
    Returns (updated_cycle, message).
    Raises ValueError on invalid transition.
    """
    cycle = db.query(SalesCycle).filter(SalesCycle.id == cycle_id).first()
    if not cycle:
        raise ValueError(f"Sales cycle {cycle_id} not found.")

    old_stage = cycle.stage

    # Allow any transition (CRM users sometimes need to correct stages)
    # but warn if jumping over stages
    valid_next = VALID_TRANSITIONS.get(old_stage, [])
    if new_stage == old_stage:
        raise ValueError("Already in this stage.")

    warning = ""
    if valid_next and new_stage not in valid_next:
        warning = (f"Non-standard transition from {old_stage.value} → "
                   f"{new_stage.value} recorded.")

    cycle.stage       = new_stage
    cycle.probability = STAGE_PROBABILITY[new_stage]
    cycle.next_action = STAGE_NEXT_ACTIONS[new_stage]

    # Update linked project status
    project = db.query(Project).filter(Project.id == cycle.project_id).first()
    if project:
        if new_stage == SalesCycleStage.CLOSED_WON:
            project.status = ProjectStatus.ACTIVE
        elif new_stage == SalesCycleStage.CLOSED_LOST:
            project.status = ProjectStatus.CLOSED

    _log_activity(
        db, cycle_id, "stage_change",
        f"Stage: {old_stage.value} → {new_stage.value}",
        notes or STAGE_NEXT_ACTIONS[new_stage],
        old_stage.value, new_stage.value,
    )

    message = warning or f"Successfully advanced to {new_stage.value}."
    return cycle, message


def get_pipeline_summary(db: Session) -> Dict:
    """Return a count + value summary grouped by stage."""
    from models import Project
    from sqlalchemy import func as sqlfunc

    rows = (
        db.query(SalesCycle.stage, sqlfunc.count(SalesCycle.id),
                 sqlfunc.sum(Project.value))
        .join(Project, Project.id == SalesCycle.project_id)
        .group_by(SalesCycle.stage)
        .all()
    )

    result = {}
    for stage in SalesCycleStage:
        result[stage.value] = {"count": 0, "total_value": 0.0, "probability": STAGE_PROBABILITY[stage]}

    for stage, count, total in rows:
        result[stage.value]["count"] = count
        result[stage.value]["total_value"] = float(total or 0)

    return result


# ── Internal helper ────────────────────────────────────────────────────────────

def _log_activity(db: Session, cycle_id: int, act_type: str,
                  title: str, description: str,
                  from_stage: Optional[str], to_stage: Optional[str]):
    act = Activity(
        sales_cycle_id=cycle_id,
        type=act_type,
        title=title,
        description=description,
        from_stage=from_stage,
        to_stage=to_stage,
    )
    db.add(act)
