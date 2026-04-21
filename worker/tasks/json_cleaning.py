"""
Celery task for JSON cleaning and validation.
"""
import json
from pathlib import Path
from celery import shared_task

from app.services.convert import (
    convert_json_format,
    make_output_paths,
)


@shared_task(
    name="worker.tasks.clean_json",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def clean_json_task(
    self,
    previous_result: dict
) -> dict:
    """
    Clean and validate the JSON output from Gemini.
    
    Args:
        previous_result: Result from generate_json_task containing:
            - gemini_json: Raw JSON from Gemini
            - file_stem: Filename stem for output files
            - image_bytes: Raw bytes of the image (for next task)
            - part_type: "plate" or "shaft"
            - gemini_path: Path to saved Gemini JSON
        
    Returns:
        dict: {
            "converted_json": dict,
            "converted_path": str,
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
        gemini_json = previous_result["gemini_json"]
        file_stem = previous_result["file_stem"]
        image_bytes = previous_result["image_bytes"]
        gemini_path = previous_result["gemini_path"]
        
        # Convert JSON format
        converted_json = convert_json_format(gemini_json)
        
        # Save converted JSON to file
        _, converted_path = make_output_paths(file_stem)
        converted_path.write_text(
            json.dumps(converted_json, indent=2),
            encoding="utf-8"
        )
        
        return {
            "converted_json": converted_json,
            "converted_path": str(converted_path),
            "gemini_json": gemini_json,
            "gemini_path": gemini_path,
            "file_stem": file_stem,
            "image_bytes": image_bytes,
            "success": True,
            "error": None,
        }
        
    except Exception as exc:
        error_msg = f"JSON cleaning failed: {str(exc)}"
        print(f"[ERROR] {error_msg}")
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)
