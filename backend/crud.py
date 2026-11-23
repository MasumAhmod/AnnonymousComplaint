import secrets
from typing import cast
from sqlalchemy.orm import Session
from sqlalchemy.engine import CursorResult
from sqlalchemy import text

VALID_STATUSES = ["Pending", "Working on it", "Solved"]


# ==========================================
# 1. CATEGORY OPERATIONS
# ==========================================
def get_categories(db: Session):
    """Fetch all grievance categories ordered by ID."""
    query = text("SELECT id, name FROM categories ORDER BY id ASC")
    return db.execute(query).fetchall()


# ==========================================
# 2. STUDENT COMPLAINT OPERATIONS
# ==========================================
def generate_tracking_id() -> str:
    """Generate a unique tracking ID (e.g., MUST-7F3A2B)."""
    return f"MUST-{secrets.token_hex(3).upper()}"


def create_complaint(db: Session, category_id: int, description: str) -> str:
    """
    Insert a new anonymous complaint into MySQL and return its tracking_id.
    Raises an exception on database failure after rolling back.
    """
    clean_description = description.strip()
    if not clean_description:
        raise ValueError("Complaint description cannot be empty.")

    tracking_id = generate_tracking_id()

    try:
        query = text("""
            INSERT INTO complaints (tracking_id, category_id, description, status)
            VALUES (:t_id, :cat_id, :desc, 'Pending')
        """)
        db.execute(query, {
            "t_id": tracking_id,
            "cat_id": category_id,
            "desc": clean_description
        })
        db.commit()
        return tracking_id
    except Exception:
        db.rollback()
        raise


def get_complaint_by_tracking_id(db: Session, tracking_id: str):
    """Fetch a single complaint's status and category by its tracking ID."""
    clean_id = tracking_id.strip().upper()
    query = text("""
        SELECT c.tracking_id,
               COALESCE(cat.name, 'Uncategorized') AS category_name,
               c.status,
               c.created_at,
               c.updated_at
        FROM complaints c
        LEFT JOIN categories cat ON c.category_id = cat.id
        WHERE c.tracking_id = :t_id
    """)
    return db.execute(query, {"t_id": clean_id}).fetchone()


# ==========================================
# 3. ADMIN DASHBOARD OPERATIONS
# ==========================================
def get_all_complaints(db: Session):
    """Fetch all complaints newest-first with joined category names."""
    query = text("""
        SELECT c.tracking_id,
               COALESCE(cat.name, 'Uncategorized') AS category_name,
               c.description,
               c.status,
               c.created_at,
               c.updated_at
        FROM complaints c
        LEFT JOIN categories cat ON c.category_id = cat.id
        ORDER BY c.created_at DESC
    """)
    return db.execute(query).fetchall()


def get_complaint_stats(complaints) -> dict[str, int]:
    """Compute dashboard summary counts from a list of complaint rows."""
    return {
        "total": len(complaints),
        "pending": sum(1 for c in complaints if c.status == "Pending"),
        "working": sum(1 for c in complaints if c.status == "Working on it"),
        "solved": sum(1 for c in complaints if c.status == "Solved"),
    }


def update_complaint_status(db: Session, tracking_id: str, new_status: str) -> bool:
    """
    Update the status of an existing complaint.
    Returns True if a row was updated, False otherwise.
    """
    if new_status not in VALID_STATUSES:
        return False

    clean_id = tracking_id.strip().upper()
    try:
        query = text("""
            UPDATE complaints
            SET status = :status
            WHERE tracking_id = :t_id
        """)
        result = cast(
            CursorResult,
            db.execute(query, {"status": new_status, "t_id": clean_id})
        )
        db.commit()
        return (result.rowcount or 0) > 0
    except Exception:
        db.rollback()
        raise