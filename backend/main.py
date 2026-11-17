from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
import secrets

from database import get_db

app = FastAPI()

@app.get("/api/categories")
def get_categories(db: Session = Depends(get_db)):
    # 2. Wrap your raw SQL string inside text()
    categories = db.execute(text("SELECT id, name FROM categories")).fetchall()
    
    # Format them into a clean JSON list for the frontend
    result = [{"id": row.id, "name": row.name} for row in categories]
    return result

class ComplaintCreate(BaseModel):
    category_id: int
    description: str
    
@app.post("/api/complaints")
def submit_complaint(complaint: ComplaintCreate, db: Session = Depends(get_db)):
    
    # 1. Generate a secure, unguessable tracking ID (e.g., MUST-7F3A2B)
    random_string = secrets.token_hex(3).upper() # Generates 6 random hex characters
    tracking_id = f"MUST-{random_string}"
    
    # 2. Insert the grievance into MySQL
    try:
        query = text("""
            INSERT INTO complaints (tracking_id, category_id, description, status) 
            VALUES (:t_id, :cat_id, :desc, 'Pending')
        """)
        
        db.execute(query, {
            "t_id": tracking_id, 
            "cat_id": complaint.category_id, 
            "desc": complaint.description
        })
        db.commit() # Save changes to database
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    # 3. Return the generated tracking ID back to the frontend
    return {
        "message": "Complaint submitted successfully",
        "tracking_id": tracking_id
    }