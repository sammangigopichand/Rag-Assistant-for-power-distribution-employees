from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.admin_config import configured_admin_emails
from app.models import User, WorkProcess, WorkStep, EmployeeProgress
from app.schemas import UserRegister
from app.auth import hash_password
from app.auth import verify_password, create_access_token
from app.database import SessionLocal
from app.services.process_service import generate_work_process
from app.services.index_service import rebuild_index
from datetime import datetime, timezone
import os
import threading

from fastapi.responses import RedirectResponse
from app.auth import decode_access_token

from pydantic import BaseModel
from app.services.rag_service import ask_rag


from fastapi import Request
from fastapi.templating import Jinja2Templates







app = FastAPI()
class QuestionRequest(BaseModel):
    question: str


class ProcessSaveRequest(BaseModel):
    save_token: str


class EmployeeActiveRequest(BaseModel):
    is_active: bool

index_job = {"status": "idle", "message": "No indexing job has run yet.", "processed": 0, "total": 0}
index_lock = threading.Lock()


@app.get("/")
def home():
    return {"message": "Utility Employee RAG Backend Running"}


@app.post("/register")
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):

    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=("admin" if user_data.email.strip().casefold() in configured_admin_emails() else "employee")
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "name": new_user.name,
        "email": new_user.email
    }



    

from app.schemas import UserRegister, UserLogin

from app.auth import (
    hash_password,
    verify_password,
    create_access_token
)




# @app.post("/login")
# def login_user(
#     user_data: UserLogin,
#     db: Session = Depends(get_db)
# ):

#     user = (
#         db.query(User)
#         .filter(User.email == user_data.email)
#         .first()
#     )

#     if not user:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid email or password"
#         )

#     if not verify_password(
#         user_data.password,
#         user.password_hash
#     ):
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid email or password"
#         )

#     token = create_access_token(
#         {
#             "sub": str(user.id),
#             "email": user.email
#         }
#     )

#     return {
#         "message": "Login successful",
#         "access_token": token,
#         "token_type": "bearer"
#     }


from fastapi import Response

@app.post("/login")
def login_user(
    user_data: UserLogin,
    response: Response,
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        user_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been suspended. Contact an administrator.")

    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        }
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=3600,
        samesite="lax"
    )

    return {
        "message": "Login successful"
    }

templates = Jinja2Templates(
    directory="app/templates"
)



@app.get("/login-page")
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )


@app.get("/register-page")
def register_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="register.html"
    )


@app.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse(
            url="/login-page",
            status_code=302
        )

    payload = decode_access_token(token)

    if not payload:
        return RedirectResponse(
            url="/login-page",
            status_code=302
        )

    user_id = int(payload["sub"])

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return RedirectResponse(
            url="/login-page",
            status_code=302
        )

    if user.role == "admin":
        return templates.TemplateResponse(request=request, name="admin_dashboard.html", context={
            "user": user,
            "employee_count": db.query(User).filter(User.role == "employee").count(),
            "process_count": db.query(WorkProcess).count(),
            "step_count": db.query(WorkStep).count(),
            "index_job": index_job,
        })
    return templates.TemplateResponse(request=request, name="employee_progress.html", context={"user": user})


def page_user(request: Request, db: Session):
    """Return the signed-in account for HTML pages, redirecting expired sessions."""
    token = request.cookies.get("access_token")
    payload = decode_access_token(token) if token else None
    if not payload:
        return RedirectResponse(url="/login-page", status_code=302)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        return RedirectResponse(url="/login-page", status_code=302)
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    return user or RedirectResponse(url="/login-page", status_code=302)


@app.get("/employee/progress-page")
def employee_progress_page(request: Request, db: Session = Depends(get_db)):
    user = page_user(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role != "employee":
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="employee_progress.html", context={"user": user})


@app.get("/employee/explanation-page")
def employee_explanation_page(request: Request, db: Session = Depends(get_db)):
    user = page_user(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role != "employee":
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="employee_explanation.html", context={"user": user})


@app.get("/employee/assistant")
def employee_assistant_page(request: Request, db: Session = Depends(get_db)):
    user = page_user(request, db)
    if isinstance(user, RedirectResponse):
        return user
    if user.role != "employee":
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user})


def current_user(request: Request, db: Session):
    token = request.cookies.get("access_token")
    payload = decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="Please sign in again.")
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid session.")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    return user


def require_admin(request: Request, db: Session):
    user = current_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user


@app.get("/employee/progress")
def employee_progress(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user.role != "employee":
        raise HTTPException(status_code=403, detail="Employee access required.")
    processes = db.query(WorkProcess).filter(WorkProcess.created_by == user.id).order_by(WorkProcess.created_at.desc()).all()
    result = []
    for process in processes:
        rows = []
        for step in process.steps:
            progress = db.query(EmployeeProgress).filter_by(employee_id=user.id, step_id=step.id).first()
            rows.append({"id": step.id, "number": step.step_number, "title": step.title,
                         "description": step.description, "source": step.source_document,
                         "done": bool(progress and progress.is_completed)})
        result.append({"id": process.id, "title": process.title, "description": process.description,
                       "prerequisites": [line for line in (process.prerequisites or "").splitlines() if line.strip()],
                       "safety_notes": [line for line in (process.safety_notes or "").splitlines() if line.strip()],
                       "source": process.source_document, "status": process.status, "steps": rows,
                       "completed": sum(1 for row in rows if row["done"]), "total": len(rows)})
    return result


@app.post("/employee/processes/preview")
def preview_employee_process(data: QuestionRequest, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user.role != "employee":
        raise HTTPException(status_code=403, detail="Employee access required.")
    try:
        worksheet = generate_work_process(data.question)
    except Exception as exc:
        status_code = getattr(exc, "code", None)
        provider_status = str(getattr(exc, "status", "")).upper()
        if status_code == 503 or provider_status == "UNAVAILABLE":
            raise HTTPException(
                status_code=503,
                detail=("The AI model is temporarily busy. Your task was not saved. "
                        "Wait a little, then try again; your task description is still in the form."),
            ) from exc
        if isinstance(status_code, int) and status_code >= 500:
            raise HTTPException(
                status_code=503,
                detail=("The AI model is temporarily unavailable. Your task was not saved. "
                        "Please retry shortly."),
            ) from exc
        raise HTTPException(status_code=502, detail=f"Could not create work process: {exc}")
    if worksheet.get("status") == "insufficient_information":
        raise HTTPException(status_code=422, detail=worksheet.get("description", "No procedure found."))
    if worksheet.get("status") not in {"ready", "needs_review"} or not worksheet.get("steps"):
        raise HTTPException(status_code=422, detail="The documents did not provide any steps that could be safely added to a project.")
    save_token = create_access_token({"sub": str(user.id), "purpose": "save_process_preview", "worksheet": worksheet})
    return {**worksheet, "save_token": save_token}


@app.post("/employee/processes/save")
def save_employee_process(data: ProcessSaveRequest, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user.role != "employee":
        raise HTTPException(status_code=403, detail="Employee access required.")
    payload = decode_access_token(data.save_token)
    if not payload or payload.get("purpose") != "save_process_preview" or payload.get("sub") != str(user.id):
        raise HTTPException(status_code=400, detail="This process preview has expired. Please generate it again.")
    worksheet = payload.get("worksheet")
    if not isinstance(worksheet, dict) or worksheet.get("status") not in {"ready", "needs_review"} or not worksheet.get("steps"):
        raise HTTPException(status_code=400, detail="The process preview is invalid. Please generate it again.")
    process = WorkProcess(title=worksheet.get("title", "Work process"), description=worksheet.get("description"),
                          source_document=", ".join(worksheet.get("sources", []))[:255],
                          prerequisites="\n".join(worksheet.get("prerequisites", [])),
                          safety_notes="\n".join(worksheet.get("safety_notes", [])),
                          status=worksheet["status"], created_by=user.id)
    process.steps = [WorkStep(step_number=s["step_number"], title=s["title"], description=s["description"],
                              source_document=s.get("source"))
                     for s in worksheet["steps"]]
    db.add(process)
    db.commit()
    db.refresh(process)
    return {
        "id": process.id,
        "title": process.title,
        "description": process.description,
        "status": process.status,
        "prerequisites": worksheet.get("prerequisites", []),
        "safety_notes": worksheet.get("safety_notes", []),
        "sources": worksheet.get("sources", []),
        "steps": [
            {"number": step["step_number"], "title": step["title"],
             "description": step["description"], "source": step["source"]}
            for step in worksheet["steps"]
        ],
    }


@app.post("/employee/steps/{step_id}/complete")
def toggle_step(step_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user.role != "employee":
        raise HTTPException(status_code=403, detail="Employee access required.")
    step = db.query(WorkStep).filter(WorkStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found.")
    if step.process.created_by != user.id:
        raise HTTPException(status_code=403, detail="This checklist belongs to another employee.")
    progress = db.query(EmployeeProgress).filter_by(employee_id=user.id, step_id=step_id).first()
    if not progress:
        progress = EmployeeProgress(employee_id=user.id, step_id=step_id)
        db.add(progress)
    progress.is_completed = not progress.is_completed
    progress.completed_at = datetime.now(timezone.utc) if progress.is_completed else None
    db.commit()
    return {"completed": progress.is_completed}


@app.delete("/employee/processes/{process_id}")
def delete_completed_process(process_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user.role != "employee":
        raise HTTPException(status_code=403, detail="Employee access required.")
    process = db.query(WorkProcess).filter_by(id=process_id, created_by=user.id).first()
    if not process:
        raise HTTPException(status_code=404, detail="Checklist not found.")
    if not process.steps:
        raise HTTPException(status_code=409, detail="An empty checklist cannot be deleted as completed.")
    completed_count = db.query(EmployeeProgress).join(WorkStep).filter(
        WorkStep.process_id == process.id,
        EmployeeProgress.employee_id == user.id,
        EmployeeProgress.is_completed.is_(True),
    ).count()
    if completed_count != len(process.steps):
        raise HTTPException(status_code=409, detail="Complete every step before deleting this checklist.")
    db.query(EmployeeProgress).filter(
        EmployeeProgress.employee_id == user.id,
        EmployeeProgress.step_id.in_([step.id for step in process.steps]),
    ).delete(synchronize_session=False)
    db.delete(process)
    db.commit()
    return {"deleted": True}


def run_index_job():
    with index_lock:
        index_job.update(status="running", message="Reading documents and creating embeddings…", processed=0, total=0)
    try:
        def update_progress(stage, processed, total):
            index_job.update(status="running", message=f"Generating embeddings: {processed} of {total} chunks ({stage}).",
                             processed=processed, total=total)
        count = rebuild_index(progress=update_progress)
        index_job.update(status="complete", message=f"Indexed {count} text chunks.", processed=count, total=count)
    except Exception as exc:
        index_job.update(status="failed", message=str(exc))


@app.post("/admin/reindex")
def start_reindex(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    require_admin(request, db)
    with index_lock:
        if index_job["status"] == "running":
            return index_job
        index_job.update(status="queued", message="Indexing queued…", processed=0, total=0)
    background_tasks.add_task(run_index_job)
    return index_job


@app.get("/admin/reindex/status")
def reindex_status(request: Request, db: Session = Depends(get_db)):
    require_admin(request, db)
    return index_job


@app.get("/admin/overview")
def admin_overview(request: Request, db: Session = Depends(get_db)):
    require_admin(request, db)
    employees = db.query(User).filter(User.role == "employee").order_by(User.name).all()
    overview = []
    for employee in employees:
        total = (db.query(WorkStep).join(WorkProcess).filter(WorkProcess.created_by == employee.id).count())
        completed = db.query(EmployeeProgress).join(WorkStep).join(WorkProcess).filter(
            EmployeeProgress.employee_id == employee.id,
            EmployeeProgress.is_completed.is_(True),
            WorkProcess.created_by == employee.id,
        ).count()
        projects = []
        for process in db.query(WorkProcess).filter(WorkProcess.created_by == employee.id).order_by(WorkProcess.created_at.desc()).all():
            project_total = len(process.steps)
            project_completed = db.query(EmployeeProgress).join(WorkStep).filter(
                WorkStep.process_id == process.id,
                EmployeeProgress.employee_id == employee.id,
                EmployeeProgress.is_completed.is_(True),
            ).count()
            projects.append({"title": process.title, "status": process.status,
                             "completed": project_completed, "total": project_total})
        overview.append({"id": employee.id, "name": employee.name, "email": employee.email,
                         "is_active": employee.is_active, "completed": completed, "total": total,
                         "projects": projects})
    return overview


@app.patch("/admin/employees/{employee_id}/active")
def set_employee_active(employee_id: int, data: EmployeeActiveRequest, request: Request,
                        db: Session = Depends(get_db)):
    require_admin(request, db)
    employee = db.query(User).filter_by(id=employee_id, role="employee").first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    employee.is_active = data.is_active
    db.commit()
    return {"id": employee.id, "is_active": employee.is_active}

@app.get("/logout")
def logout():

    response = RedirectResponse(
        url="/login-page",
        status_code=302
    )

    response.delete_cookie("access_token")

    return response


@app.post("/ask")
def ask_question(
    data: QuestionRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    # Check login cookie
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Please login first"
        )

    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session"
        )

    user_id = int(payload["sub"])

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    question = data.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    result = ask_rag(question)

    return result
