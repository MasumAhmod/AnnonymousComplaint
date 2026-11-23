from fastapi import APIRouter, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import crud

router = APIRouter(tags=["Student Portal"])
templates = Jinja2Templates(directory="frontend")


# ==========================================
# 1. STUDENT PORTAL HOME & SUBMIT ROUTES
# ==========================================
@router.get("/", response_class=HTMLResponse)
def read_student_portal(
    request: Request,
    tab: str = "submit",
    db: Session = Depends(get_db)
):
    categories = crud.get_categories(db)
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": tab if tab in ("submit", "track") else "submit",
        "categories": categories,
        "tracking_id": None,
        "status": None,
        "error": None
    })


@router.post("/", response_class=HTMLResponse)
def submit_grievance(
    request: Request,
    category_id: int = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db)
):
    categories = crud.get_categories(db)

    try:
        tracking_id = crud.create_complaint(db, category_id, description)
    except ValueError as ve:
        return templates.TemplateResponse(request, "index.html", {
            "request": request,
            "tab": "submit",
            "categories": categories,
            "tracking_id": None,
            "status": None,
            "error": str(ve)
        })
    except Exception as e:
        print("DB INSERT ERROR:", repr(e))
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


# ==========================================
# 2. STUDENT TRACKING ROUTES
# ==========================================
@router.get("/track", response_class=HTMLResponse)
def read_track_page(request: Request, db: Session = Depends(get_db)):
    categories = crud.get_categories(db)
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": "track",
        "categories": categories,
        "tracking_id": None,
        "status": None,
        "error": None
    })


@router.post("/track", response_class=HTMLResponse)
def track_grievance(
    request: Request,
    tracking_id: str = Form(...),
    db: Session = Depends(get_db)
):
    categories = crud.get_categories(db)
    clean_id = tracking_id.strip().upper()
    complaint = crud.get_complaint_by_tracking_id(db, clean_id)

    status = complaint.status if complaint else None
    error = None if complaint else "Invalid tracking ID. Please check your ID and try again."

    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": "track",
        "categories": categories,
        "searched_id": clean_id,
        "tracking_id": None,
        "status": status,
        "error": error
    })