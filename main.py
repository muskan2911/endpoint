from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

firebase_json = os.environ.get("FIREBASE_CREDENTIAL_JSON")

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(firebase_json))
    firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Input model from user
class GoalInput(BaseModel):
    id: int
    name: str
    target: float
    current: float
    deadline: str
    priority: str
    category: str
    onTrack: bool


# Output model with derived fields
class Goal(BaseModel):
    id: int
    name: str
    target: float
    current: float
    deadline: str
    priority: str
    category: str
    onTrack: bool         # required
    timeLeft: str         # required
    monthlyContribution: float  # required
    progress: float       # required



@app.get("/")
def root():
    return {"message": "FastAPI with Firebase is running!"}


# 🔹 Add Goal with Calculated Fields
@app.post("/addGoal", response_model=Goal)
def add_goal(goal_input: GoalInput):
    try:
        deadline_date = datetime.strptime(goal_input.deadline, "%Y-%m-%d")
        today = datetime.today()

        # Months left
        delta_months = (deadline_date.year - today.year) * 12 + (deadline_date.month - today.month)
        delta_months = max(delta_months, 1)

        # Monthly contribution
        remaining = goal_input.target - goal_input.current
        monthly_contribution = round(max(0, remaining / delta_months), 2)

        # Progress in %
        progress = round((goal_input.current / goal_input.target) * 100, 2)
        progress = min(progress, 100.0)

        # Final goal data
        goal_data = goal_input.dict()
        goal_data.update({
            "timeLeft": f"{delta_months} months",
            "monthlyContribution": monthly_contribution,
            "progress": progress
        })

        db.collection('goals').document(str(goal_input.id)).set(goal_data)
        return goal_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/getGoals", response_model=List[Goal])
def get_goals():
    try:
        docs = db.collection("goals").stream()
        result = []

        for doc in docs:
            data = doc.to_dict()
            data["id"] = int(doc.id) if doc.id.isdigit() else 0

            # Ensure all required fields are present or calculated
            target = data.get("target", 0)
            current = data.get("current", 0)
            deadline = data.get("deadline", "")
            on_track = data.get("onTrack", False)

            # Compute time left
            try:
                deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
                today = datetime.today()
                delta_months = (deadline_date.year - today.year) * 12 + (deadline_date.month - today.month)
                delta_months = max(delta_months, 1)
                time_left = f"{delta_months} months"
            except Exception:
                delta_months = 1
                time_left = "N/A"

            # Compute progress and monthly contribution
            progress = round((current / target) * 100, 2) if target else 0
            progress = min(progress, 100.0)
            monthly_contribution = round(max(0, (target - current) / delta_months), 2)

            # Update data with missing computed fields
            data.update({
                "onTrack": on_track,
                "timeLeft": time_left,
                "monthlyContribution": monthly_contribution,
                "progress": progress
            })

            result.append(data)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# 🔹 API: Total number of goals
@app.get("/totalGoals")
def total_goals():
    try:
        docs = db.collection('goals').stream()
        total = sum(1 for _ in docs)
        return {"totalGoals": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 🔹 API: Total monthly target
@app.get("/monthlyTarget")
def monthly_target():
    try:
        docs = db.collection('goals').stream()
        total_monthly_contribution = sum(doc.to_dict().get("monthlyContribution", 0) for doc in docs)
        return {"monthlyTarget": round(total_monthly_contribution, 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
