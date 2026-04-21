import asyncio
import os
import sys
from pathlib import Path
from app.dependencies.auth import get_current_user
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from app.models.user import User
from app.services.convert import convert_to_3d
import base64, json, io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import threading
from fastapi import Request
from worker.utils.cancellation import request_cancellation
import yaml


router = APIRouter(prefix="/files", tags=["files"])

conversion_results = {}

executor = ThreadPoolExecutor()

# Add worker to path for Celery imports
worker_path = Path(__file__).resolve().parent.parent.parent.parent / "worker"
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

# Try to import Celery pipeline (may not be available if Celery not running)
USE_CELERY = os.getenv("USE_CELERY", "true").lower() == "true"
celery_available = False

if USE_CELERY:
    try:
        from worker.pipelines.conversion_pipeline import convert_image_to_3d
        celery_available = True
        print("✅ Celery pipeline loaded successfully")
    except Exception as e:
        print(f"⚠️  Celery not available, falling back to ThreadPoolExecutor: {e}")
        celery_available = False


@router.post("/convert")
async def convert_to_3d_endpoint(
    request: Request,
    file: UploadFile = File(...),
    prompt_file_content: str = Form(None),
    current_user: User = Depends(get_current_user),
):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))

    # ── Resolve prompt ────────────────────────────────────────────
    user_prompt = None
    if prompt_file_content and prompt_file_content.strip():
        try:
            data = yaml.safe_load(prompt_file_content)
            user_prompt = data.get("prompt") if isinstance(data, dict) else None
            if not user_prompt:
                raise HTTPException(status_code=400, detail="YML file must have a top-level 'prompt' key")
        except yaml.YAMLError as e:
            raise HTTPException(status_code=400, detail=f"Invalid YML file: {e}")
    # user_prompt=None → load_prompt() uses default file
    # ─────────────────────────────────────────────────────────────

    if celery_available:
        try:
            result = convert_image_to_3d(image_bytes, file.filename, current_user.id, user_prompt)
            return {
                "message": "Conversion started",
                "task_id": result.id,
                "status": "PENDING",
                "backend": "celery",
                "status_url": f"/files/task/{result.id}",
            }
        except Exception as e:
            print(f"❌ Celery execution failed: {e}, falling back to ThreadPoolExecutor")

    # ThreadPoolExecutor fallback
    loop = asyncio.get_event_loop()
    stop_event = threading.Event()
    future = loop.run_in_executor(
        executor, convert_to_3d, image, file.filename, image_bytes, stop_event, current_user.id, user_prompt
    )

    while not future.done():
        if await request.is_disconnected():
            stop_event.set()
            return {"message": "Cancelled"}
        await asyncio.sleep(0.5)

    result = future.result()
    if result is None:
        return {"message": "Cancelled mid-processing"}

    doc_url = result
    converted_bytes_io = io.BytesIO()
    image.save(converted_bytes_io, format="PNG")

    return {
        "message": "3D conversion done",
        "doc_url": doc_url,
        "backend": "threadpool",
    }


@router.delete("/task/{task_id}")
async def stop_task(task_id: str):
    if not celery_available:
        raise HTTPException(status_code=503, detail="Celery not available")
    try:
        from celery.result import AsyncResult
        from worker.celery_app import celery_app

        def revoke_chain(task_id: str):
            """Revoke a task AND all its children (downstream chain tasks)."""
            result = AsyncResult(task_id, app=celery_app)
            celery_app.control.revoke(task_id, terminate=True, signal='SIGTERM')

            # Traverse children (downstream), not parent (upstream)
            children = result.children
            if children:
                for child in children:
                    revoke_chain(child.id)  # recurse into each child

        revoke_chain(task_id)

        return {"message": f"Task {task_id} and its chain have been cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop task: {str(e)}")


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    if not celery_available:
        raise HTTPException(status_code=503, detail="Celery not available")

    try:
        from celery.result import AsyncResult
        from worker.celery_app import celery_app

        task_result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "status": task_result.state,
            "ready": task_result.ready(),
        }

        # ✅ Treat REVOKED as a terminal state so the frontend exits the poll loop
        if task_result.state == "REVOKED":
            response["ready"] = True
            response["success"] = False
            response["error"] = "Task was cancelled"
            return response

        if task_result.ready():
            if task_result.successful():
                result = task_result.result
                response["success"] = result.get("success", True) if isinstance(result, dict) else True
                response["result"] = result  # ❌ this includes image_bytes if pipeline failed
                if isinstance(result, dict) and "doc_url" in result:
                    response["doc_url"] = result["doc_url"]
                if isinstance(result, dict) and "history_id" in result:
                    response["history_id"] = result["history_id"]
            else:
                response["error"] = str(task_result.info)
                response["success"] = False
        elif task_result.state == "PENDING":
            response["message"] = "Task is waiting to be processed"
        elif task_result.state == "STARTED":
            response["message"] = "Task is currently being processed"

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching task status: {str(e)}")


@router.get("/results")
async def get_results(user_id: int = None, history_id: int = None):
    """
    Get conversion results.
    
    Args:
        user_id: User ID (fetches latest result for user)
        history_id: Specific history record ID (preferred for accurate results)
        
    Returns:
        Conversion results including doc_url, JSON data, and image
    """
    from app.core.database import SessionLocal
    from app.models.history import History

    if not user_id and not history_id:
        raise HTTPException(status_code=400, detail="Either user_id or history_id must be provided")

    db = SessionLocal()
    try:
        if history_id:
            # Fetch by specific history_id (accurate)
            result = db.query(History).filter(History.id == history_id).first()
        else:
            # Fallback to latest for user (may be inaccurate if multiple conversions)
            result = (
                db.query(History)
                .filter(History.user_id == user_id)
                .order_by(History.id.desc())
                .first()
            )
    finally:
        db.close()

    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    gemini_json, converted_json = result.gemini_data, result.converted_data

    return {
        "status": "done",
        "converted_image": f"data:image/png;base64,{result.image_base64}",
        "doc_url": result.doc_url,
        "gemini_json": gemini_json,
        "converted_json": converted_json,
    }