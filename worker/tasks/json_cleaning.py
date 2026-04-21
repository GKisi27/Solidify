"""
Celery task for JSON cleaning and validation.
"""
import json
from celery import shared_task

from app.services.convert import (
    convert_json_format,
)


@shared_task(
    name="worker.tasks.clean_json",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def clean_json_task(
    self,
    previous_result: dict,
    user_id: int = None
) -> dict:
    """
    Clean and validate the JSON output from Gemini.

    Args:
        previous_result: Result from generate_json_task containing:
            - gemini_json: Raw JSON from Gemini
            - file_stem: Filename stem for output files
            - image_bytes: Raw bytes of the image (for next task)
            - part_type: "plate" or "shaft"
            - user_id: int

    Returns:
        dict: {
            "converted_json": dict,
            "gemini_json": dict,
            "file_stem": str,
            "image_bytes": bytes,
            "part_type": str,
            "user_id": int,
            "success": bool,
            "error": str (if success=False)
        }
    """
    from worker.utils.cancellation import is_cancelled, clear_cancellation

    # Propagate failure from previous task — includes cancellations
    if not previous_result.get("success", False):
        return previous_result

    # ── Cancellation check ──────────────────────────────────────────────────
    if is_cancelled(self.request.id):
        clear_cancellation(self.request.id)
        print(f"[CANCELLED] clean_json_task {self.request.id}")
        return {
            "converted_json": None,
            "gemini_json": previous_result.get("gemini_json"),
            "file_stem": previous_result.get("file_stem"),
            "part_type": previous_result.get("part_type"),
            "user_id": previous_result.get("user_id", user_id),
            "success": False,
            "error": "Task was cancelled",
        }
    # ────────────────────────────────────────────────────────────────────────

    try:
        gemini_json = previous_result["gemini_json"]
        file_stem = previous_result["file_stem"]
        image_bytes = previous_result["image_bytes"]
        part_type = previous_result["part_type"]
        user_id = previous_result.get("user_id", user_id)

        converted_json = convert_json_format(gemini_json)

        return {
            "converted_json": converted_json,
            "gemini_json": gemini_json,
            "file_stem": file_stem,
            "image_bytes": image_bytes,
            "part_type": part_type,
            "user_id": user_id,
            "success": True,
            "error": None,
        }

    except Exception as exc:
        error_msg = f"JSON cleaning failed: {str(exc)}"
        print(f"[ERROR] {error_msg}")

        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)