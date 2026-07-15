from sqlalchemy.orm import Session
from app.models import AuditLog


def write_audit(
    db: Session, actor_id, action: str, entity: str,
    entity_id: str = None, before: dict = None, after: dict = None,
):
    db.add(AuditLog(
        actor_id=actor_id,
        action=action,          # CREATE / UPDATE / DELETE / APPROVE
        entity=entity,          # 'documents', 'drugs'...
        entity_id=str(entity_id) if entity_id else None,
        before_data=before,
        after_data=after,
    ))
    # KHÔNG commit ở đây — để commit chung transaction với thao tác chính