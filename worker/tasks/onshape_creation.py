"""
Celery task for creating 3D models in OnShape.
"""
from celery import shared_task

from app.models.history import HistoryType
from app.services.convert import (
    load_config,
    OnshapeSession,
)
from app.services.to_db import save_history


@shared_task(
    name="worker.tasks.create_onshape_model",
    bind=True,
    max_retries=3,
    default_retry_delay=90,
)
def create_onshape_model_task(
    self,
    previous_result: dict,
    user_id: int = None
) -> dict:
    """
    Create a 3D model in OnShape from the converted JSON.

    Args:
        previous_result: Result from clean_json_task containing:
            - converted_json: Cleaned and validated JSON
            - gemini_json: Original Gemini JSON
            - file_stem: Filename stem
            - image_bytes: Raw bytes of the image
            - part_type: "plate" or "shaft"
            - user_id: int

    Returns:
        dict: {
            "doc_url": str,
            "document_id": str,
            "workspace_id": str,
            "element_id": str,
            "history_id": int,
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
        print(f"[CANCELLED] create_onshape_model_task {self.request.id}")
        return {
            "doc_url": None,
            "document_id": None,
            "workspace_id": None,
            "element_id": None,
            "history_id": None,
            "user_id": previous_result.get("user_id", user_id),
            "success": False,
            "error": "Task was cancelled",
        }
    # ────────────────────────────────────────────────────────────────────────

    try:
        converted_json = previous_result["converted_json"]
        gemini_json = previous_result["gemini_json"]
        file_stem = previous_result["file_stem"]
        image_bytes = previous_result["image_bytes"]
        part_type = previous_result["part_type"]
        user_id = previous_result.get("user_id", user_id)

        cfg = load_config()

        session = OnshapeSession(
            access=cfg["onshape_access"],
            secret=cfg["onshape_secret"],
            base=cfg["onshape_base"],
        )

        did, wid, eid = session.create_document("3D Model - " + file_stem)
        features_url = session.features_url(did, wid, eid)

        is_shaft = "revolve_axis" in converted_json
        revolve_axis = converted_json.get("revolve_axis")
        views = converted_json.get("views", [])

        if is_shaft:
            session.build_shaft(
                features_url=features_url,
                views=views,
                revolve_axis=revolve_axis,
                stop_event=None,
            )
        else:
            session.build_plate(
                features_url=features_url,
                views=views,
                stop_event=None,
            )

        doc_url = f"{cfg['onshape_base']}/documents/{did}/w/{wid}/e/{eid}"

        history_entry = save_history(
            image_bytes=image_bytes,
            filename=file_stem,
            gemini_json=gemini_json,
            converted_json=converted_json,
            history_type=HistoryType.convert_to_3d,
            doc_url=doc_url,
            user_id=user_id,
        )

        return {
            "doc_url": doc_url,
            "document_id": did,
            "workspace_id": wid,
            "element_id": eid,
            "history_id": history_entry.id,
            "success": True,
            "error": None,
        }

    except Exception as exc:
        error_msg = f"OnShape model creation failed: {str(exc)}"
        print(f"[ERROR] {error_msg}")

        if "API" in str(exc) or "connection" in str(exc).lower() or "timeout" in str(exc).lower():
            raise self.retry(exc=exc, countdown=90)

        return {
            "doc_url": None,
            "document_id": None,
            "workspace_id": None,
            "element_id": None,
            "history_id": None,
            "user_id": user_id,
            "success": False,
            "error": error_msg,
        }