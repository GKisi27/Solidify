"""
Celery task for image processing and part type detection.
"""
from io import BytesIO
from PIL import Image
from celery import shared_task
import base64

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
        user_id: ID of the user requesting the conversion

    Returns:
        dict: {
            "part_type": "plate" or "shaft",
            "file_stem": str,
            "image_bytes": bytes,
            "user_id": int,
            "success": bool,
            "error": str (if success=False)
        }
    """
    from worker.utils.cancellation import is_cancelled, clear_cancellation

    # ── Cancellation check ──────────────────────────────────────────────────
    if is_cancelled(self.request.id):
        clear_cancellation(self.request.id)
        print(f"[CANCELLED] process_image_task {self.request.id}")
        return {
            "part_type": None,
            "file_stem": file_stem,
            "image_bytes": image_bytes,
            "user_id": user_id,
            "success": False,
            "error": "Task was cancelled",
        }
    # ────────────────────────────────────────────────────────────────────────

    try:
        cfg = load_config()

        image = open_image(image_bytes)
        image = prepare_image(image)

        gemini_client = get_gemini_client(cfg["gemini_api_key"])

        part_type = detect_part_type(
            image=image,
            client=gemini_client,
            model=cfg["gemini_model"],
            stop_event=None,
        )

        return {
            "part_type": part_type,
            "file_stem": file_stem,
            "image_bytes": base64.b64encode(image_bytes).decode("utf-8"),
            "user_id": user_id,
            "success": True,
            "error": None,
        }

    except Exception as exc:
        error_msg = f"Image processing failed: {str(exc)}"
        print(f"[ERROR] {error_msg}")

        if "API" in str(exc) or "connection" in str(exc).lower():
            raise self.retry(exc=exc, countdown=60)

        return {
            "part_type": None,
            "file_stem": file_stem,
            "user_id": user_id,
            "success": False,
            "error": error_msg,
        }