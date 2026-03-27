"""
Celery task for JSON generation from image using Gemini AI.
"""
import json
from pathlib import Path
from io import BytesIO
from PIL import Image
from celery import shared_task

from app.services.convert import (
    load_config,
    load_prompt,
    get_gemini_client,
    call_gemini,
    open_image,
    prepare_image,
    make_output_paths,
)


@shared_task(
    name="worker.tasks.generate_json",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_json_task(
    self,
    previous_result: dict
) -> dict:
    """
    Generate coordinate JSON from image using Gemini AI.
    
    Args:
        previous_result: Result from process_image_task containing:
            - part_type: "plate" or "shaft"
            - image_bytes: Raw bytes of the image
            - file_stem: Filename stem for output files
        
    Returns:
        dict: {
            "gemini_json": dict,
            "gemini_path": str,
            "file_stem": str,
            "image_bytes": bytes,
            "part_type": str,
            "success": bool,
            "error": str (if success=False)
        }
    """
    try:
        # Extract data from previous task result
        part_type = previous_result["part_type"]
        image_bytes = previous_result["image_bytes"]
        file_stem = previous_result["file_stem"]
        
        # Load configuration and prompt
        cfg = load_config()
        prompt = load_prompt(part_type)
        
        # Open and prepare image
        image = open_image(image_bytes)
        image = prepare_image(image)
        
        # Initialize Gemini client
        gemini_client = get_gemini_client(cfg["gemini_api_key"])
        
        # Call Gemini to generate JSON
        gemini_json = call_gemini(
            image=image,
            prompt=prompt,
            client=gemini_client,
            model=cfg["gemini_model"]
        )
        
        # Save JSON to file
        gemini_path, _ = make_output_paths(file_stem)
        gemini_path.write_text(
            json.dumps(gemini_json, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        return {
            "gemini_json": gemini_json,
            "gemini_path": str(gemini_path),
            "file_stem": file_stem,
            "image_bytes": image_bytes,
            "part_type": part_type,
            "success": True,
            "error": None,
        }
        
    except Exception as exc:
        error_msg = f"JSON generation failed: {str(exc)}"
        print(f"[ERROR] {error_msg}")
        
        # Retry on transient errors
        if "API" in str(exc) or "connection" in str(exc).lower():
            raise self.retry(exc=exc, countdown=60)
        
        return {
            "gemini_json": None,
            "gemini_path": None,
            "file_stem": previous_result.get("file_stem"),
            "success": False,
            "error": error_msg,
        }
