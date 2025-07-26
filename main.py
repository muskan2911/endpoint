from fastapi import APIRouter, FastAPI, HTTPException
from typing import List
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
from pydantic import BaseModel
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Firebase service account key file path
FIREBASE_KEY_PATH = os.path.join(os.path.dirname(__file__), 'firebase-key.json')

try:
    if os.path.exists(FIREBASE_KEY_PATH):
        cred = credentials.Certificate(FIREBASE_KEY_PATH)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized successfully")
    else:
        print(f"Firebase key file not found at: {FIREBASE_KEY_PATH}")
        print("Please download your Firebase service account key and save it as 'firebase-key.json'")
        db = None
except Exception as e:
    print(f"Firebase initialization failed: {e}")
    db = None

router = APIRouter()

class GoalInput(BaseModel):
    id: int
    name: str
    target: int
    current: int
    deadline: str 
    category: str
    priority: str
    user_session_id: str

class Goal(GoalInput):
    monthly_contribution: int
    time_left: str
    progress: float

@router.get("/")
def root():
    return {"message": "FastAPI with Firebase is running!"}

@router.post("/addGoal", response_model=Goal)
def add_goal(goal_input: GoalInput):
    try:
        deadline_date = datetime.strptime(goal_input.deadline, "%Y-%m-%d")
        today = datetime.today()
        delta_months = (deadline_date.year - today.year) * 12 + (deadline_date.month - today.month)
        delta_months = max(delta_months, 1)
        remaining = goal_input.target - goal_input.current
        monthly_contribution = max(0, remaining // delta_months)
        progress = round((goal_input.current / goal_input.target) * 100, 2)
        progress = min(progress, 100.0)

        goal_data = goal_input.dict()
        goal_data["timeLeft"] = f"{delta_months} months"
        goal_data["monthlyContribution"] = monthly_contribution
        goal_data["progress"] = progress

        doc_id = str(uuid.uuid4())
        db.collection('goals_final').document(doc_id).set(goal_data)

        return goal_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/getGoals", response_model=List[Goal])
def get_goals():
    try:
        docs = db.collection('goals_final').stream()
        goals = []
        for doc in docs:
            data = doc.to_dict()

            # Ensure required fields are mapped correctly
            transformed = {
                "id": data.get("id"),
                "name": data.get("name"),
                "target": data.get("target"),
                "current": data.get("current"),
                "deadline": data.get("deadline"),
                "category": data.get("category"),
                "priority": data.get("priority"),
                "user_session_id": data.get("user_session_id", "unknown"),  # default or fallback
                "monthly_contribution": data.get("monthlyContribution", 0),
                "time_left": data.get("timeLeft", "N/A"),
                "progress": data.get("progress", 0.0),
            }

            goals.append(transformed)
        return goals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/totalGoals")
def total_goals():
    try:
        docs = db.collection('goals_final').stream()
        total = sum(1 for _ in docs)
        return {"totalGoals": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monthlyTarget")
def monthly_target():
    try:
        docs = db.collection('goals_final').stream()
        total_monthly_contribution = sum(doc.to_dict().get("monthlyContribution", 0) for doc in docs)
        return {"monthlyTarget": total_monthly_contribution}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Define and include the app
app = FastAPI()
app.include_router(router)
