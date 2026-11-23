import os
import secrets
from fastapi import APIRouter, Depends, Request, Form, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import crud

router = APIRouter(prefix="/admin", tags=["Admin Portal"])
templates = Jinja2Templates(directory="frontend")

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


def get_authenticated_admin(admin_session: str | None) -> dict[str, str] | None:
    if not admin_session:
        return None
    return ADMIN_CREDENTIALS.get(admin_session)


# ==========================================
# 1. ADMIN AUTHENTICATION ROUTES
# ==========================================
@router.get("/login", response_class=HTMLResponse)
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


@router.post("/login")
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


@router.api_route("/logout", methods=["GET", "POST"])
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="admin_session")
    return response


# ==========================================
# 2. ADMIN DASHBOARD & STATUS UPDATES
# ==========================================
@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def read_admin_portal(
    request: Request,
    admin_session: str | None = Cookie(None),
    db: Session = Depends(get_db)
):
    admin_record = get_authenticated_admin(admin_session)
    if not admin_record:
        return RedirectResponse(url="/admin/login", status_code=303)

    complaints = crud.get_all_complaints(db)
    stats = crud.get_complaint_stats(complaints)

    return templates.TemplateResponse(request, "admin.html", {
        "request": request,
        "logged_in": True,
        "current_admin": admin_session,
        "role": admin_record["role"],
        "stats": stats,
        "complaints": complaints,
        "statuses": crud.VALID_STATUSES
    })


@router.post("/update-status/{tracking_id}")
@router.post("/update/{tracking_id}")
def update_complaint_status(
    tracking_id: str,
    status: str = Form(...),
    admin_session: str | None = Cookie(None),
    db: Session = Depends(get_db)
):
    if not get_authenticated_admin(admin_session):
        return RedirectResponse(url="/admin/login", status_code=303)

    try:
        crud.update_complaint_status(db, tracking_id, status)
    except Exception as e:
        print("DB UPDATE ERROR:", repr(e))

    return RedirectResponse(url="/admin", status_code=303)