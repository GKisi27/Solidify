from fastapi import APIRouter, UploadFile, File
from app.services.auth_services import login_user
from app.schemas import Users
from app.services.test import process_uploaded_photo


router = APIRouter()

@router.post('/login')
def login(data: Users):
    return login_user(data.username, data.password)

@router.post('/upload')
def process_photo(file: UploadFile = File(...)):
    return process_uploaded_photo(file)