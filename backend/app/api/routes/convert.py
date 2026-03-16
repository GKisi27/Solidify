import asyncio
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.services.auth_services import get_current_user
from app.models.user import User
from app.services.convert import convert_to_3d
import base64, json, io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import threading
from fastapi import Request
import uuid



router = APIRouter(prefix="/files", tags=["files"])

conversion_results = {}

executor = ThreadPoolExecutor()

@router.post("/convert")
async def convert_to_3d_endpoint(request: Request, file: UploadFile = File(...)):
    image_bytes = await file.read()
    image = Image.open(io.BytesIO(image_bytes))
    
    loop = asyncio.get_event_loop()
    stop_event = threading.Event()
    conversion_id = str(uuid.uuid4())

    future = loop.run_in_executor(executor, convert_to_3d, image, file.filename, image_bytes, stop_event, conversion_id)
    
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
        "conversion_id": conversion_id,  
        "doc_url": doc_url,
    }


@router.get("/results")
async def get_results(user_id: int):
    from app.core.database import SessionLocal
    from app.models.history import History

    db = SessionLocal()
    try:
        record = (
            db.query(History)
            .filter(History.user_id == user_id).first()
        )
    finally:
        db.close()

    if not record:
        raise HTTPException(status_code=404, detail="Result not found")

    from app.services.get_data import get_json
    gemini_json, converted_json = record.gemini_data, record.converted_data

    return {
        "status": "done",
        "converted_image": f"data:image/png;base64,{record.image_base64}",
        "doc_url": record.doc_url,
        "gemini_json": gemini_json,
        "converted_json": converted_json,
    }