from fastapi import APIRouter, UploadFile, File, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException
from app.schemas import Users
from app.services.auth_services import login_user
from app.services.get_data import get_json
import redis
import uuid
from PIL import Image
import io
import json
from app.services.convert import convert_to_3d
import base64
from app.services.auth_services import get_current_user 
from app.models.user import User
from app.core.database import Base, engine
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import Request
from pydantic import BaseModel
import threading

router = APIRouter()
executor = ThreadPoolExecutor() 
r = redis.Redis(host='redis', port=6379, db=0)

@router.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    try:
        result = login_user(username, password)
        if result:
            return {
                "access_token": result["token"],
                "token_type": "bearer",
                "username": result['username']
            }
        else:
            return {"detail": "Invalid username or password"}
    except Exception as e:
        return {"success": False, "detail": str(e)}


@router.post("/upload")
async def upload(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    contents = await file.read()
    image_id = str(uuid.uuid4())
    encoded_string = base64.b64encode(contents).decode("utf-8")
    data_to_store = {
        "file_name": file.filename,
        "content": encoded_string
    }
    r.set(name=image_id, ex=600, value=json.dumps(data_to_store))
    return {"image_id": image_id, "message": "Image Uploaded successfully"}


@router.post("/convert")
async def convert(request: Request, file: UploadFile = File(...)):
    contents = await file.read()
    file_name = file.filename
    encoded_string = base64.b64encode(contents).decode("utf-8")

    image_bytes = base64.b64decode(encoded_string)
    image = Image.open(io.BytesIO(image_bytes))

    loop = asyncio.get_event_loop()
    stop_event = threading.Event()

    future = loop.run_in_executor(executor, convert_to_3d, image, file_name, image_bytes, stop_event)

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

    converted_bytes = io.BytesIO()
    image.save(converted_bytes, format="PNG")
    converted_b64 = base64.b64encode(converted_bytes.getvalue()).decode("utf-8")

    # Resolve JSONs immediately so the frontend gets everything in one round trip
    gemini_json, converted_json = get_json(gemini_path, converted_path)

    return {
        "message": "Conversion completed",
        "converted_image": f"data:image/png;base64,{converted_b64}",
        "doc_url": doc_url,
        "gemini_json": gemini_json,
        "converted_json": converted_json,
    }