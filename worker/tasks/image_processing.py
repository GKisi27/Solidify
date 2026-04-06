"""
Celery task for image processing and part type detection.
"""
import os
from io import BytesIO
from pathlib import Path
from PIL import Image
from celery import shared_task
from typing import Tuple

from app.services.convert import (
    load_config,
    get_gemini_client,
    detect_part_type,
    prepare_image,
    open_image,
)


@shared_task(
    name="worker.tasks.process_image",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_image_task(
    self,
    image_bytes: bytes,
    file_stem: str,
    user_id: int
) -> dict:
    """
    Process an uploaded image and detect its part type.
    
    Args:
        image_bytes: Raw bytes of the uploaded image
        file_stem: Filename stem for output files
        
    Returns:
        dict: {
            "part_type": "plate" or "shaft",
            "file_stem": str,
            "success": bool,
            "error": str (if success=False)
        }
    """
    print(f"Processing image for user_id={user_id}, file_stem={file_stem}")  # Debug log to check input data
    try:
        # Load configuration
        cfg = load_config()
        
        # Open and prepare image
        image = open_image(image_bytes)
        image = prepare_image(image)
        
        # Initialize Gemini client
        gemini_client = get_gemini_client(cfg["gemini_api_key"])
        
        # Detect part type
        part_type = detect_part_type(
            image=image,
            client=gemini_client,
            model=cfg["gemini_model"],
            stop_event=None  # No cancellation support in Celery tasks
        )
        
        return {
            "part_type": part_type,
            "file_stem": file_stem,
            "image_bytes": image_bytes,  # Pass along for next task
            "user_id": user_id,
            "success": True,
            "error": None,
        }
        
    except Exception as exc:
        error_msg = f"Image processing failed: {str(exc)}"
        print(f"[ERROR] {error_msg}")
        
        # Retry on transient errors
        if "API" in str(exc) or "connection" in str(exc).lower():
            raise self.retry(exc=exc, countdown=60)
        
        return {
            "part_type": None,
            "file_stem": file_stem,
            "user_id": user_id,
            "success": False,
            "error": error_msg,
        }
