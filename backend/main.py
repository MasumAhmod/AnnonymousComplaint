import os
from pathlib import Path
import secrets
from fastapi import FastAPI, Depends, Request, Form, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.database import get_db

# Load key=value pairs from root .env using Python standard library
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

app = FastAPI(title="MU Anonymous Grievance Portal")

# Mount frontend templates directory (run uvicorn from project root)
templates = Jinja2Templates(directory="frontend")

# Admin credentials loaded from .env with local development fallbacks
ADMIN_CREDENTIALS = {
    "proctor": {
        "password": os.getenv("PROCTOR_PASSWORD", "mup1234"),
        "role": "Proctor Office"
    },
    "dsw": {
        "password": os.getenv("DSW_PASSWORD", "mu1234"),
        "role": "Directorate of Student Welfare (DSW)"
    }
}

VALID_STATUSES = ["Pending", "Working on it", "Solved"]


def get_categories(db: Session):
    return db.execute(text("SELECT id, name FROM categories ORDER BY id ASC")).fetchall()


def get_authenticated_admin(admin_session: str | None) -> dict[str, str] | None:
    if not admin_session:
        return None
    return ADMIN_CREDENTIALS.get(admin_session)


# ==========================================
# 1. STUDENT PORTAL ROUTES (`index.html`)
# ==========================================
@app.get("/", response_class=HTMLResponse)
def read_student_portal(request: Request, tab: str = "submit", db: Session = Depends(get_db)):
    categories = get_categories(db)
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": tab if tab in ("submit", "track") else "submit",
        "categories": categories,
        "tracking_id": None,
        "status": None,
        "error": None
    })


@app.post("/", response_class=HTMLResponse)
def submit_grievance(
    request: Request,
    category_id: int = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db)
):
    categories = get_categories(db)
    clean_description = description.strip()

    if not clean_description:
        return templates.TemplateResponse(request, "index.html", {
            "request": request,
            "tab": "submit",
            "categories": categories,
            "tracking_id": None,
            "status": None,
            "error": "Description cannot be empty."
        })

    # Generate unique tracking ID (e.g., MUST-7F3A2B)
    tracking_id = f"MUST-{secrets.token_hex(3).upper()}"

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
    except Exception:
        db.rollback()
        return templates.TemplateResponse(request, "index.html", {
            "request": request,
            "tab": "submit",
            "categories": categories,
            "tracking_id": None,
            "status": None,
            "error": "Submission failed. Please verify your category selection and try again."
        })

    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": "submit",
        "categories": categories,
        "tracking_id": tracking_id,
        "status": None,
        "error": None
    })


@app.get("/track", response_class=HTMLResponse)
def read_track_page(request: Request, db: Session = Depends(get_db)):
    categories = get_categories(db)
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": "track",
        "categories": categories,
        "tracking_id": None,
        "status": None,
        "error": None
    })


@app.post("/track", response_class=HTMLResponse)
def track_grievance(
    request: Request,
    tracking_id: str = Form(...),
    db: Session = Depends(get_db)
):
    categories = get_categories(db)
    clean_id = tracking_id.strip().upper()

    query = text("SELECT status FROM complaints WHERE tracking_id = :t_id")
    result = db.execute(query, {"t_id": clean_id}).fetchone()

    status = result[0] if result else None
    error = None if result else "Invalid tracking ID. Please check your ID and try again."

    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": "track",
        "categories": categories,
        "searched_id": clean_id,
        "tracking_id": None,
        "status": status,
        "error": error
    })


# ==========================================
# 2. ADMIN AUTHENTICATION ROUTES
# ==========================================
@app.get("/admin/login", response_class=HTMLResponse)
def read_admin_login(
    request: Request,
    error: str | None = None,
    admin_session: str | None = Cookie(None)
):
    if get_authenticated_admin(admin_session):
        return RedirectResponse(url="/admin", status_code=303)

    error_msg = "Invalid Admin ID or Password." if error else None
    return templates.TemplateResponse(request, "admin.html", {
        "request": request,
        "logged_in": False,
        "error": error_msg
    })


@app.post("/admin/login")
def process_admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    clean_user = username.strip().lower()
    admin_record = ADMIN_CREDENTIALS.get(clean_user)

    if admin_record and secrets.compare_digest(admin_record["password"], password):
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(
            key="admin_session",
            value=clean_user,
            httponly=True,
            samesite="lax"
        )
        return response

    return templates.TemplateResponse(request, "admin.html", {
        "request": request,
        "logged_in": False,
        "error": "Invalid Admin ID or Password."
    }, status_code=401)


@app.api_route("/admin/logout", methods=["GET", "POST"])
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="admin_session")
    return response


# ==========================================
# 3. ADMIN DASHBOARD & STATUS UPDATE ROUTES
# ==========================================
@app.get("/admin", response_class=HTMLResponse)
def read_admin_portal(
    request: Request,
    admin_session: str | None = Cookie(None),
    db: Session = Depends(get_db)
):
    admin_record = get_authenticated_admin(admin_session)
    if not admin_record:
        return RedirectResponse(url="/admin/login", status_code=303)

    query = text("""
        SELECT c.tracking_id, cat.name AS category_name, c.description, c.status, c.created_at
        FROM complaints c
        JOIN categories cat ON c.category_id = cat.id
        ORDER BY c.created_at DESC
    """)
    complaints = db.execute(query).fetchall()

    stats = {
        "total": len(complaints),
        "pending": sum(1 for c in complaints if c.status == "Pending"),
        "working": sum(1 for c in complaints if c.status == "Working on it"),
        "solved": sum(1 for c in complaints if c.status == "Solved"),
    }

    return templates.TemplateResponse(request, "admin.html", {
        "request": request,
        "logged_in": True,
        "current_admin": admin_session,
        "role": admin_record["role"],
        "stats": stats,
        "complaints": complaints,
        "statuses": VALID_STATUSES
    })


@app.post("/admin/update-status/{tracking_id}")
@app.post("/admin/update/{tracking_id}")
def update_complaint_status(
    tracking_id: str,
    status: str = Form(...),
    admin_session: str | None = Cookie(None),
    db: Session = Depends(get_db)
):
    if not get_authenticated_admin(admin_session):
        return RedirectResponse(url="/admin/login", status_code=303)

    if status not in VALID_STATUSES:
        return RedirectResponse(url="/admin", status_code=303)

    try:
        query = text("UPDATE complaints SET status = :status WHERE tracking_id = :t_id")
        db.execute(query, {"status": status, "t_id": tracking_id.strip().upper()})
        db.commit()
    except Exception:
        db.rollback()

    return RedirectResponse(url="/admin", status_code=303)