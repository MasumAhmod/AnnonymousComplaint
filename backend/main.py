from fastapi import FastAPI, Depends, Request, Form, HTTPException, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import secrets

from backend.database import get_db

app = FastAPI()

# Point FastAPI directly to your frontend folder
templates = Jinja2Templates(directory="frontend")

# Simple hardcoded admin credentials (move to database/env variables later)
ADMIN_CREDENTIALS = {
    "proctor": "mup1234",
    "dsw": "mu1234"
}

# ==========================================
# 1. STUDENT PORTAL ROUTES (`index.html`)
# ==========================================
@app.get("/", response_class=HTMLResponse)
def read_student_portal(request: Request, tab: str = "submit", db: Session = Depends(get_db)):
    categories = db.execute(text("SELECT id, name FROM categories")).fetchall()
    
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": tab,
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
    # Secure server-side ID generator (fixes sequential guessing flaw)
    tracking_id = f"MUST-{secrets.token_hex(3).upper()}"
    
    try:
        query = text("""
            INSERT INTO complaints (tracking_id, category_id, description, status) 
            VALUES (:t_id, :cat_id, :desc, 'Pending')
        """)
        db.execute(query, {"t_id": tracking_id, "cat_id": category_id, "desc": description})
        db.commit()
    except Exception as e:
        db.rollback()
        categories = db.execute(text("SELECT id, name FROM categories")).fetchall()
        return templates.TemplateResponse(request, "index.html", {
            "request": request,
            "tab": "submit",
            "categories": categories,
            "error": "Submission failed. Please try again."
        })

    categories = db.execute(text("SELECT id, name FROM categories")).fetchall()
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": "submit",
        "categories": categories,
        "tracking_id": tracking_id
    })

@app.post("/track", response_class=HTMLResponse)
def track_grievance(
    request: Request,
    tracking_id: str = Form(...),
    db: Session = Depends(get_db)
):
    categories = db.execute(text("SELECT id, name FROM categories")).fetchall()
    clean_id = tracking_id.strip().upper()
    
    query = text("SELECT status FROM complaints WHERE tracking_id = :t_id")
    result = db.execute(query, {"t_id": clean_id}).fetchone()
    
    # Safely extract status from query result tuple/mapping
    status = result[0] if result else None
    error = None if result else "Invalid tracking ID. Please re-enter your ID or check it again."

    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "tab": "track",
        "categories": categories,
        "tracking_id": None,
        "status": status,
        "error": error
    })


# ==========================================
# 2. ADMIN PORTAL & AUTHENTICATION ROUTES
# ==========================================
@app.get("/admin/login", response_class=HTMLResponse)
def read_admin_login(request: Request):
    return templates.TemplateResponse(request, "admin_login.html", {
        "request": request,
        "error": None
    })

@app.post("/admin/login")
def process_admin_login(username: str = Form(...), password: str = Form(...)):
    if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == password:
        response = RedirectResponse(url="/admin", status_code=303)
        # Set a simple cookie to track login state
        response.set_cookie(key="admin_session", value=username, httponly=True)
        return response
    
    return RedirectResponse(url="/admin/login?error=1", status_code=303)

@app.get("/admin/logout")
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="admin_session")
    return response

@app.get("/admin", response_class=HTMLResponse)
def read_admin_portal(request: Request, admin_session: str = Cookie(None), db: Session = Depends(get_db)):
    # Protect route: if not logged in, redirect to login page
    if not admin_session or admin_session not in ADMIN_CREDENTIALS:
        return RedirectResponse(url="/admin/login", status_code=303)

    query = text("""
        SELECT c.tracking_id, cat.name AS category_name, c.description, c.status, c.created_at 
        FROM complaints c
        JOIN categories cat ON c.category_id = cat.id
        ORDER BY c.created_at DESC
    """)
    complaints = db.execute(query).fetchall()
    
    return templates.TemplateResponse(request, "admin.html", {
        "request": request,
        "complaints": complaints,
        "current_admin": admin_session
    })

@app.post("/admin/update-status/{tracking_id}")
def update_status_jinja(tracking_id: str, status: str = Form(...), admin_session: str = Cookie(None), db: Session = Depends(get_db)):
    if not admin_session or admin_session not in ADMIN_CREDENTIALS:
        return RedirectResponse(url="/admin/login", status_code=303)

    try:
        query = text("UPDATE complaints SET status = :status WHERE tracking_id = :t_id")
        db.execute(query, {"status": status, "t_id": tracking_id})
        db.commit()
    except Exception as e:
        db.rollback()
    
    return RedirectResponse(url="/admin", status_code=303)