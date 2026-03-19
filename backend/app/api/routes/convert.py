import asyncio
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.models.user import User
from app.services.convert import convert_to_3d
import base64, json, io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import threading
from fastapi import Request


router = APIRouter(prefix="/files", tags=["files"])

conversion_results = {}

executor = ThreadPoolExecutor()

@router.post("/convert")
async def convert_to_3d_endpoint(request: Request, file: UploadFile = File(...)):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))
    
    loop = asyncio.get_event_loop()
    stop_event = threading.Event()

    future = loop.run_in_executor(executor, convert_to_3d, image, file.filename, image_bytes, stop_event)
    
    while not future.done():
        if await request.is_disconnected():
            stop_event.set()
            print("Client disconnected — stop_event set")
            return {"message": "Cancelled"}
        await asyncio.sleep(0.5)
    
    result = future.result()
    if result is None:
        return {"message": "Cancelled mid-processing"}


    doc_url, gemini_path, converted_path = result  

    converted_bytes_io = io.BytesIO()
    image.save(converted_bytes_io, format="PNG")
    converted_b64 = base64.b64encode(converted_bytes_io.getvalue()).decode("utf-8")

    return {
        "message": "3D conversion done",
        "doc_url": doc_url,
    }


@router.get("/results")
async def get_results(user_id: int):
    from app.core.database import SessionLocal
    from app.models.history import History

    db = SessionLocal()
    try:
        latest = (
            db.query(History)
            .filter(History.user_id == user_id)
            .order_by(History.id.desc())
            .first()
        )
    finally:
        db.close()

    if not latest:
        raise HTTPException(status_code=404, detail="Result not found")

    gemini_json, converted_json = latest.gemini_data, latest.converted_data

    return {
        "status": "done",
        "converted_image": f"data:image/png;base64,{latest.image_base64}",
        "doc_url": latest.doc_url,
        "gemini_json": gemini_json,
        "converted_json": converted_json,
    }