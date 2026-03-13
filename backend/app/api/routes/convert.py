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

    conversion_results[file.filename] = {
        "converted_image": converted_b64,  
        "doc_url": doc_url,
        "gemini_path": gemini_path,       
        "converted_path": converted_path  
    }

    return {"message": "3D conversion done", "file": file.filename, "doc_url": doc_url}



@router.get("/results/")
async def get_results(file_name: str):
    result = conversion_results.get(file_name)

    if not result:
        return {"status": "pending"}

    # Read JSON files
    from app.services.get_data import get_json
    gemini_json, converted_json = get_json(result['gemini_path'], result['converted_path'])

    return {
        "status": "done",
        "converted_image": f"data:image/png;base64,{result['converted_image']}",  # original preview
        "doc_url": result["doc_url"],
        "gemini_json": gemini_json,         # read from gemini_path
        "converted_json": converted_json    # read from converted_path
    }