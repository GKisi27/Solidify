from fastapi import APIRouter, UploadFile, File, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, HTTPException
from schemas import Users
from services.auth_services import login_user
from services.get_data import get_json
import redis
import uuid
from PIL import Image
import io
import json
from services.convert import convert_to_3d
from fastapi.responses import Response
import base64



router = APIRouter()

r = redis.Redis(host='localhost', port='6379', db=0)


@router.post("/login")
async def login(data: Users):
    try:
        result = login_user(data.username, data.password)

        if result:
            return {
                "success": True,
                "token": result["token"],
                "user_id": result["user_id"],
                "username": result["username"]
            }
        else:
            return {"success": False, "detail": "Invalid username or password"}

    except Exception as e:
        return {"success": False, "detail": str(e)}


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    contents = await file.read() 
    image_id = str(uuid.uuid4()) 
    
    data_to_store = {
        "file_name": file.filename,
        "content": contents.hex()
    }
    
    r.set(name=image_id, ex=600, value=json.dumps(data_to_store))
    
    
    return {"image_id": image_id, "message": "Image Uploaded successsfully"}


@router.post("/convert")
async def convert(image_id: str):
    # Fetch original image from Redis
    data = r.get(image_id)
    if not data:
        return {"error": "Image not found or expired"}

    data_dict = json.loads(data)
    file_name = data_dict["file_name"]
    image_bytes = bytes.fromhex(data_dict["content"])

    image = Image.open(io.BytesIO(image_bytes))

    doc_url, gemini_path, converted_path = convert_to_3d(image, file_name)  

    converted_bytes = io.BytesIO()
    image.save(converted_bytes, format="PNG")  
    converted_b64 = base64.b64encode(converted_bytes.getvalue()).decode("utf-8")

    results_data = {
        "converted_image": converted_b64,
        "doc_url": doc_url,
        "gemini_path": str(gemini_path),
        "converted_path": str(converted_path)
    }

    r.set(f"results:{image_id}", json.dumps(results_data), ex=3600)  

    return {"message": "Conversion completed", "image_id": image_id}

@router.get("/results/{image_id}")
async def get_results(image_id: str):
    results_data = r.get(f"results:{image_id}")
    if not results_data:
        return {"status": "pending"}  # conversion not finished

    data = json.loads(results_data)
    gemini_path = data['gemini_path']
    converted_path = data['converted_path']
    
    gemini_json, converted_json = get_json(gemini_path, converted_path)

    return {
        "status": "done",
        "converted_image": f"data:image/png;base64,{data['converted_image']}",
        "doc_url": data["doc_url"],
        "gemini_json": gemini_json,
        "converted_json": converted_json
    }