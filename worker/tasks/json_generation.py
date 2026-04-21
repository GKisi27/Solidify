"""
Celery task for JSON generation from image using Gemini AI.
"""
import json
from io import BytesIO
from PIL import Image
from celery import shared_task
import base64

from app.services.convert import (
    load_config,
    load_prompt,
    get_gemini_client,
    call_gemini,
    open_image,
    prepare_image,
)


@shared_task(
    name="worker.tasks.generate_json",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_json_task(
    self,
    previous_result: dict,
    user_id: int = None,
    user_prompt: str = None,
) -> dict:
    """
    Generate coordinate JSON from image using Gemini AI.

    Args:
        previous_result: Result from process_image_task containing:
            - part_type: "plate" or "shaft"
            - image_bytes: Raw bytes of the image
            - file_stem: Filename stem for output files
            - user_id: int

    Returns:
        dict: {
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
        print(f"[CANCELLED] generate_json_task {self.request.id}")
        return {
            "gemini_json": None,
            "file_stem": previous_result.get("file_stem"),
            "part_type": previous_result.get("part_type"),
            "user_id": previous_result.get("user_id", user_id),
            "success": False,
            "error": "Task was cancelled",
        }
    # ────────────────────────────────────────────────────────────────────────

    try:
        part_type = previous_result["part_type"]
        file_stem = previous_result["file_stem"]
        user_id = previous_result.get("user_id", user_id)

        cfg = load_config()
        prompt = load_prompt(part_type, user_prompt)

        image_bytes_encoded = previous_result["image_bytes"]  # still a string
        image_bytes_raw = base64.b64decode(image_bytes_encoded)
        image = open_image(image_bytes_raw)  # ✅ decode for PIL
        image = prepare_image(image)


        gemini_client = get_gemini_client(cfg["gemini_api_key"])

        print(f"Final prompt {prompt}")

        gemini_json = call_gemini(
            image=image,
            prompt=prompt,
            client=gemini_client,
            model=cfg["gemini_model"],
        )

        return {
            "gemini_json": gemini_json,
            "file_stem": file_stem,
            "image_bytes": image_bytes_encoded,
            "part_type": part_type,
            "user_id": user_id,
            "success": True,
            "error": None,
        }

    except Exception as exc:
        error_msg = f"JSON generation failed: {str(exc)}"
        print(f"[ERROR] {error_msg}")

        if "API" in str(exc) or "connection" in str(exc).lower():
            raise self.retry(exc=exc, countdown=60)

        return {
            "gemini_json": None,
            "file_stem": previous_result.get("file_stem"),
            "part_type": previous_result.get("part_type"),
            "user_id": user_id,
            "success": False,
            "error": error_msg,
        }