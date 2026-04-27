import json
import math
import os
import time
from io import BytesIO
from pathlib import Path

import numpy as np
import requests
import yaml
from dotenv import load_dotenv
from PIL import Image

import google.genai as genai
from google.genai import types
from app.services.to_db import save_history

# Cache for config to avoid reloading
_CONFIG_CACHE = None

def load_config() -> dict:
    """Load configuration from environment variables (lazy-loaded and cached)."""
    global _CONFIG_CACHE
    
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    
    load_dotenv()

    config = {
        "gemini_api_key": os.getenv("GEMINI_PAID_KEY"),
        "onshape_access":  os.getenv("access"),
        "onshape_secret":  os.getenv("secret"),
        "onshape_base":    "https://cad.onshape.com",
        "gemini_model":    "gemini-3.1-pro-preview",
    }

    missing = [k for k, v in config.items() if not v and k != "onshape_base"]
    if missing:
        raise EnvironmentError(f"Missing required environment variables for keys: {missing}")

    _CONFIG_CACHE = config
    return config


PROMPT_FILES = {
    "plate": "prompt1.yml",
    "shaft": "prompt2.yml",
}


def load_prompt(part_type: str = "plate", user_prompt: str = None) -> str:

    if user_prompt and user_prompt.strip():
        return user_prompt.strip()

    prompt_file = PROMPT_FILES.get(part_type)
    if not prompt_file:
        raise ValueError(f"Unknown part_type '{part_type}'. Must be one of: {list(PROMPT_FILES)}")

    base_dir = Path(__file__).resolve().parent
    full_path = base_dir / prompt_file

    with open(full_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    return data["prompt"]


def sanitize_name(name: str) -> str:
    """Strip unsafe characters from a filename stem."""
    return "".join(c for c in name if c.isalnum() or c in ("-", "_"))


#path for files if we want to save them locally
def make_output_paths(file_stem: str, output_dir: str | None = None) -> tuple[Path, Path]:
    file_name_only = Path(file_stem).stem
    data_dir = os.getenv("DATA_DIR")

    if output_dir:
        base = Path(output_dir)
    elif data_dir:
        base = Path(data_dir) / file_name_only
    elif Path("/solidify/data").exists():
        base = Path("/solidify/data") / file_name_only
    else:
        current_folder = Path(__file__).resolve().parent
        # Go up: services -> app -> backend -> Solidify
        base_project_folder = current_folder.parent.parent.parent
        base = base_project_folder / "data" / file_name_only

    base.mkdir(parents=True, exist_ok=True)

    safe = sanitize_name(file_name_only)
    gemini_path    = base / f"{safe}_gemini.json"
    converted_path = base / f"{safe}_converted.json"

    gemini_path.touch(exist_ok=True)
    converted_path.touch(exist_ok=True)

    return gemini_path, converted_path

def prepare_image(image: Image.Image) -> Image.Image:
    """Ensure the image is in RGB mode, converting if necessary."""
    if image.mode not in ("RGB", "RGBA"):
        return image.convert("RGB")
    return image


def open_image(source: str | Path | bytes | BytesIO) -> Image.Image:
    """Open an image from a file path or raw bytes."""
    if isinstance(source, (str, Path)):
        return Image.open(source)
    if isinstance(source, bytes):
        return Image.open(BytesIO(source))
    return Image.open(source)


def get_gemini_client(api_key: str) -> genai.Client:
    """Instantiate and return a Gemini client."""
    return genai.Client(api_key=api_key)


def detect_part_type(image: Image.Image, client: genai.Client, model: str, stop_event=None) -> str:
    """
    Ask Gemini to classify the image as a plate or shaft.

    Returns:
        ``"shaft"`` if the image is a shaft/cylindrical part, ``"plate"`` otherwise.
    """
    classification_prompt = (
        "You are an expert at reading 2D engineering drawings. "
        "Look at this drawing and classify the part as one of two types:\n"
        "- 'shaft': a cylindrical/rotational part (has a revolve axis, cross-section views, symmetric profile)\n"
        "- 'plate': a flat/prismatic part (extruded from top/front/side views, no revolve axis)\n"
        "Reply with only one word: shaft or plate."
    )

    response = client.models.generate_content(
        model=model,
        contents=[image, classification_prompt],
    )
    
    if stop_event and stop_event.is_set():
                    print("Cancelled during Detection of the Part")
                    return
    answer = response.text.strip().lower()
    part_type = "shaft" if "shaft" in answer else "plate"
    print(f"[detect_part_type] Gemini classified image as: '{part_type}' (raw response: '{answer}')")
    return part_type


# Gemini 3.1 or gemini 3?? (test going on)

def call_gemini(
    image: Image.Image,
    prompt: str,
    client: genai.Client,
    model: str = "gemini-3-pro-preview",
) -> dict:
    """
    Send an image + prompt to Gemini and return the parsed JSON response.

    Raises:
        ValueError: If the response cannot be parsed as JSON.
    """
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0,
    )

    response = client.models.generate_content(
        model=model,
        contents=[image, prompt],
        config=config,
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini returned non-JSON response: {exc}") from exc

def _unit_vector(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Return the unit direction vector from point *a* to point *b*."""
    direction = b - a
    norm = np.linalg.norm(direction)
    return direction / norm if norm else np.zeros(2)


def _arc_center(
    start: np.ndarray,
    end: np.ndarray,
    radius: float,
    prev_seg: dict | None,
    next_seg: dict | None,
) -> np.ndarray:
    """
    Compute the arc center that best satisfies tangency with adjacent segments.
    Falls back to the chord midpoint when tangency cannot be resolved.
    """
    dx, dy = end - start
    chord = math.hypot(dx, dy)

    if chord == 0:
        return start.copy()

    h = math.sqrt(max(radius**2 - (chord / 2) ** 2, 0))
    mid  = (start + end) / 2
    perp = np.array([-dy, dx]) / chord

    c1 = mid + h * perp
    c2 = mid - h * perp

    def tangency_score(center: np.ndarray, point: np.ndarray, seg: dict) -> float:
        to_c = center - point
        norm  = np.linalg.norm(to_c)
        if norm == 0:
            return 0.0
        to_c /= norm
        tangent   = np.array([-to_c[1], to_c[0]])
        seg_start = np.array([seg["start_point"][0], seg["start_point"][1]])
        seg_end   = np.array([seg["end_point"][0],   seg["end_point"][1]])
        return abs(np.dot(tangent, _unit_vector(seg_start, seg_end)))

    for seg, point in [(prev_seg, start), (next_seg, end)]:
        if seg is not None and seg["type"] == "line":
            return c1 if tangency_score(c1, point, seg) >= tangency_score(c2, point, seg) else c2

    return c1


def _cad_angle(point: np.ndarray, center: np.ndarray) -> float:
    """Compute the Onshape-convention angle (clockwise from +X) in degrees."""
    angle = math.degrees(math.atan2(point[1] - center[1], point[0] - center[0]))
    return (-angle) % 360


def _is_clockwise(start: np.ndarray, end: np.ndarray, center: np.ndarray) -> bool:
    """Return True if the arc from *start* to *end* around *center* is clockwise."""
    to_s = start - center
    to_e = end   - center
    return (to_s[0] * to_e[1] - to_s[1] * to_e[0]) < 0


def _normalize_cw_angles(start: float, end: float) -> tuple[float, float]:
    """Ensure end > start for a clockwise arc sweep."""
    start %= 360
    end   %= 360
    if end <= start:
        end += 360
    return start, end

#LLM generated json lai OnShape ko format ma lagna 

def _intermediate_entity(raw: dict) -> dict:
    """Convert a raw Gemini entity into a normalised intermediate dict."""
    kind = raw["type"].upper()
    if kind == "LINE":
        return {
            "type": "line",
            "start_point": [raw["start_x"], raw["start_y"]],
            "end_point":   [raw["end_x"],   raw["end_y"]],
        }
    if kind == "ARC":
        return {
            "type": "arc",
            "start_point": [raw["start_x"], raw["start_y"]],
            "end_point":   [raw["end_x"],   raw["end_y"]],
            "radius":       raw["radius"],
        }
    if kind == "CIRCLE":
        return {
            "type":     "circle",
            "center_x": raw["center_x"],
            "center_y": raw["center_y"],
            "radius":   raw["radius"],
        }
    raise ValueError(f"Unknown entity type: {raw['type']}")


def _convert_entity(entity: dict, idx: int, siblings: list[dict]) -> dict:
    """Convert an intermediate entity to the final Onshape-ready format."""
    kind = entity["type"]

    if kind == "line":
        sx, sy = entity["start_point"]
        ex, ey = entity["end_point"]
        return {
            "type":    "LINE",
            "start_x": round(sx, 2),
            "start_y": round(sy, 2),
            "end_x":   round(ex, 2),
            "end_y":   round(ey, 2),
        }

    if kind == "circle":
        return {
            "type":     "CIRCLE",
            "center_x": round(entity["center_x"], 2),
            "center_y": round(entity["center_y"], 2),
            "radius":   round(entity["radius"],   2),
        }

    if kind == "arc":
        prev_seg = siblings[idx - 1] if idx > 0 else None
        next_seg = siblings[idx + 1] if idx < len(siblings) - 1 else None

        start  = np.array(entity["start_point"])
        end    = np.array(entity["end_point"])
        center = _arc_center(start, end, entity["radius"], prev_seg, next_seg)

        if np.isnan(center).any():
            center = (start + end) / 2

        if not _is_clockwise(start, end, center):
            start, end = end, start

        sa = _cad_angle(start, center)
        ea = _cad_angle(end,   center)
        sa, ea = _normalize_cw_angles(sa, ea)

        return {
            "type":        "ARC",
            "center_x":    round(center[0],        2),
            "center_y":    round(center[1],        2),
            "radius":      round(entity["radius"], 2),
            "start_angle": round(sa, 2),
            "end_angle":   round(ea, 2),
            "clockwise":   True,
        }

    raise ValueError(f"Unhandled intermediate entity type: {kind}")


def _detect_section_view(views: list[dict]) -> dict | None:
    """Return the first view whose name suggests it is a section / cut view."""
    SECTION_KEYWORDS = {"section", "a-a", "aa", "cut"}
    for view in views:
        name = view.get("name", "").strip().lower()
        if any(kw in name for kw in SECTION_KEYWORDS):
            return view
    return None


def _extract_shaft_section_entities(section_view: dict) -> list[dict]:
    """
    Extract section-view inner contours for shaft parts.

    Matches the behaviour of app_RevolveFull_.py:
      - CIRCLEs are copied raw (center_x/y and radius taken directly from the
        section view, no projection or axis snapping).
      - ARCs are represented as full 360-degree circles (start_angle=0,
        end_angle=360) so they appear as inner bore profiles when revolved.
      - LINEs are ignored (section view lines are not meaningful for a revolved
        shaft profile).
    """
    result: list[dict] = []
    for e in section_view.get("entities", []):
        t = e.get("type", "").upper()
        if t == "CIRCLE":
            result.append({
                "type":     "CIRCLE",
                "center_x": round(e.get("center_x", 0.0), 2),
                "center_y": round(e.get("center_y", 0.0), 2),
                "radius":   round(e.get("radius",   0.0), 2),
            })
        elif t == "ARC":
            # Represent as a full circle so the revolve produces a complete
            result.append({
                "type":        "ARC",
                "center_x":    0.0,
                "center_y":    0.0,
                "radius":      round(e.get("radius", 0.0), 2),
                "start_angle": 0.0,
                "end_angle":   360.0,
                "clockwise":   True,
            })
    return result


def _convert_section_entities(
    section_view: dict,
    revolve_axis: dict | None,
) -> list[dict]:
    """
    Convert section-view entities into front-view-ready Onshape entities.

    Used by plates only (revolve_axis is None for plates):
      - CIRCLEs: copied as-is (no axis to project onto).
      - ARCs / LINEs: converted normally using the tangency-aware arc logic.
    """
    raw_entities = section_view.get("entities", [])
    intermediates = [_intermediate_entity(e) for e in raw_entities]
    result: list[dict] = []

    for idx, ent in enumerate(intermediates):
        result.append(_convert_entity(ent, idx, intermediates))

    return result


def convert_json_format(gemini_json: dict) -> dict:
    """
    Transform Gemini-output JSON into the Onshape-ready JSON format.

    Shaft workflow (revolve_axis present):
      1.  Detect an optional section / cut view.
      2.  Extract inner contours from the section view as raw circles / full-
          circle arcs (no projection, no geometry transformation) — matches
          app_RevolveFull_.py behaviour.
      3.  The section view is NOT skipped; it is output as its own view as
          normal, in addition to the section entities being merged into the
          front view.
      4.  For the front view, append the extracted section entities.

    Plate workflow (no revolve_axis):
      1.  Detect an optional section / cut view.
      2.  Convert section entities using the normal tangency-aware arc logic.
      3.  The section view IS skipped (its content is merged into front only).
      4.  For the front view, append the converted section entities.

    Both workflows preserve ``revolve_axis`` in the output when present.
    """
    output: dict = {"views": []}
    revolve_axis  = gemini_json.get("revolve_axis")
    is_shaft      = revolve_axis is not None

    if revolve_axis:
        output["revolve_axis"] = revolve_axis

    if "metadata" in gemini_json:
        output["metadata"] = gemini_json["metadata"]

    raw_views    = gemini_json.get("views", [])
    section_view = _detect_section_view(raw_views)

    # Pre-build the section entities list using the appropriate strategy.
    section_entities: list[dict] = []
    if section_view is not None:
        if is_shaft:
            # Shaft: raw copy — circles as-is, arcs as full 360° circles.
            section_entities = _extract_shaft_section_entities(section_view)
        else:
            # Plate: normal conversion via tangency-aware arc logic.
            section_entities = _convert_section_entities(section_view, revolve_axis)

    for view in raw_views:
        view_name = view.get("name", "").strip()

        # Plates: skip the section view — its content is merged into front.
        # Shafts: keep the section view as its own output view as well.
        if view is section_view and not is_shaft:
            continue

        intermediates = [_intermediate_entity(e) for e in view.get("entities", [])]
        converted = [
            _convert_entity(e, i, intermediates)
            for i, e in enumerate(intermediates)
        ]

        # Merge section geometry into the front view for both workflows.
        if view_name.lower() == "front" and section_entities:
            converted.extend(section_entities)

        output["views"].append({
            "name":     view["name"],
            "entities": converted,
            "metadata": view.get("metadata", {"units": "mm", "scale": 1}),
        })

    return output

_MM_TO_M = 1 / 1000


def _line_sketch_entity(entity: dict, uid: str) -> dict:
    dx = (entity["end_x"] - entity["start_x"]) * _MM_TO_M
    dy = (entity["end_y"] - entity["start_y"]) * _MM_TO_M
    return {
        "btType":       "BTMSketchCurveSegment-155",
        "startParam":   0.0,
        "endParam":     1.0,
        "geometry": {
            "btType": "BTCurveGeometryLine-117",
            "pntX":   entity["start_x"] * _MM_TO_M,
            "pntY":   entity["start_y"] * _MM_TO_M,
            "dirX":   dx,
            "dirY":   dy,
        },
        "entityId":      uid,
        "startPointId":  f"{uid}.start",
        "endPointId":    f"{uid}.end",
    }


def _arc_sketch_entity(entity: dict, uid: str) -> dict:
    return {
        "btType":     "BTMSketchCurveSegment-155",
        "startParam": math.radians(entity["start_angle"]),
        "endParam":   math.radians(entity["end_angle"]),
        "geometry": {
            "btType":    "BTCurveGeometryCircle-115",
            "radius":    entity["radius"]   * _MM_TO_M,
            "xCenter":   entity["center_x"] * _MM_TO_M,
            "yCenter":   entity["center_y"] * _MM_TO_M,
            "xDir":      1.0,
            "yDir":      0.0,
            "clockwise": entity.get("clockwise", True),
        },
        "entityId":     uid,
        "centerId":     f"{uid}.center",
        "startPointId": f"{uid}.start",
        "endPointId":   f"{uid}.end",
    }


def _circle_sketch_entity(entity: dict, uid: str) -> dict:
    return {
        "btType": "BTMSketchCurve-4",
        "geometry": {
            "btType":    "BTCurveGeometryCircle-115",
            "radius":    entity["radius"]   * _MM_TO_M,
            "xCenter":   entity["center_x"] * _MM_TO_M,
            "yCenter":   entity["center_y"] * _MM_TO_M,
            "xDir":      1.0,
            "yDir":      0.0,
            "clockwise": True,
        },
        "entityId": uid,
        "centerId": f"{uid}.center",
    }


def build_sketch_entities(
    view_entities: list[dict],
    *,
    return_last_id: bool = False,
) -> list[dict] | tuple[list[dict], str | None]:
    """
    Convert view entities into Onshape sketch entity dicts.

    Args:
        view_entities:  List of converted entities (LINE / ARC / CIRCLE).
        return_last_id: When True, also returns the last entity ID assigned.

    Returns:
        A list of sketch entity dicts, or a ``(list, last_id)`` tuple.
    """
    builders = {
        "LINE":   _line_sketch_entity,
        "ARC":    _arc_sketch_entity,
        "CIRCLE": _circle_sketch_entity,
    }
    prefix_map = {"LINE": "line", "ARC": "arc", "CIRCLE": "circle"}

    sketch_entities: list[dict] = []
    last_id: str | None = None
    counter = 0

    for entity in view_entities:
        kind = entity["type"]
        uid  = f"{prefix_map[kind]}-{counter}"
        sketch_entities.append(builders[kind](entity, uid))
        last_id = uid
        counter += 1

    return (sketch_entities, last_id) if return_last_id else sketch_entities

# HELPER FUNCTIONS
# ── Coincident-constraint helpers ─────────────────────────────────────────

def _pts_close(a: tuple, b: tuple, tol: float = 0.05) -> bool:
    """True if two (x, y) mm-coordinate pairs are within *tol* mm."""
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def _entity_endpoints(entity: dict, uid: str) -> list[tuple[tuple, str]]:
    """
    Return [(coord_mm, point_id), ...] for a converted entity.
    CIRCLEs are skipped (no endpoint concept).
    ARCs use the clockwise-from-+X angle convention stored in start/end_angle.
    """
    kind = entity["type"]
    if kind == "LINE":
        return [
            ((entity["start_x"], entity["start_y"]), f"{uid}.start"),
            ((entity["end_x"],   entity["end_y"]),   f"{uid}.end"),
        ]
    if kind == "ARC":
        cx, cy, r = entity["center_x"], entity["center_y"], entity["radius"]
        sa = math.radians(entity["start_angle"])
        ea = math.radians(entity["end_angle"])
        # CW convention: y-component is negated vs standard CCW math
        return [
            ((cx + r * math.cos(sa), cy - r * math.sin(sa)), f"{uid}.start"),
            ((cx + r * math.cos(ea), cy - r * math.sin(ea)), f"{uid}.end"),
        ]
    return []


def build_sketch_constraints(
    view_entities: list[dict],
    sketch_entities: list[dict],
) -> list[dict]:
    """
    Detect shared endpoints across sketch entities and emit COINCIDENT constraints.

    Args:
        view_entities:   The converted (mm) entity dicts — LINE/ARC/CIRCLE.
        sketch_entities: The BTM entity dicts returned by build_sketch_entities(),
                         used only to read entityId values.
    """
    prefix_map = {"LINE": "line", "ARC": "arc", "CIRCLE": "circle"}
    registry: list[tuple[tuple, str]] = []

    for counter, entity in enumerate(view_entities):
        kind = entity["type"]
        uid  = f"{prefix_map[kind]}-{counter}"
        registry.extend(_entity_endpoints(entity, uid))

    constraints: list[dict] = []
    seen: set = set()
    cid = 0

    for i, (ca, ida) in enumerate(registry):
        for cb, idb in registry[i + 1:]:
            if ida == idb:
                continue
            if not _pts_close(ca, cb):
                continue
            key = (min(ida, idb), max(ida, idb))
            if key in seen:
                continue
            seen.add(key)
            constraints.append({
                "btType":           "BTMSketchConstraint-2",
                "constraintType":   "COINCIDENT",
                "entityId":         f"coincident-{cid}",
                "parameters": [
                    {"btType": "BTMParameterString-149",
                     "value": ida, "parameterId": "localFirst"},
                    {"btType": "BTMParameterString-149",
                     "value": idb, "parameterId": "localSecond"},
                ],
            })
            cid += 1

    return constraints
class OnshapeSession:
    """Thin wrapper around the Onshape REST API for this converter."""

    SUPPORTED_VIEWS = {"front", "top", "right"}

    def __init__(self, access, secret, base):
        self.base = base
        self._session = requests.Session()
        self._session.auth = (access, secret)
        self._session.headers.update({
            "Accept":       "application/json;charset=UTF-8;qs=0.09",
            "Content-Type": "application/json;charset=UTF-8;qs=0.09",
        })

    def _post(self, url: str, body: dict) -> dict:
        resp = self._session.post(url, json=body)
        resp.raise_for_status()
        return resp.json()

    def _get(self, url: str) -> dict:
        resp = self._session.get(url)
        resp.raise_for_status()
        return resp.json()
    
    def _axis_data_valid(self, revolve_axis: dict | None) -> bool:
        if not revolve_axis or not isinstance(revolve_axis, dict):
            return False
        required = ("start_x", "start_y", "end_x", "end_y")
        if not all(k in revolve_axis for k in required):
            return False
        if revolve_axis["start_x"] == revolve_axis["end_x"] and \
        revolve_axis["start_y"] == revolve_axis["end_y"]:
            return False
        return True

    def _post_feature(self, url: str, body: dict, defer_eval: bool = False) -> dict:
        target_url = url + ("?rollbackBarIndex=999" if defer_eval else "")
        resp = self._session.post(target_url, json=body)
        resp.raise_for_status()
        return resp.json()

    def create_document(self, name: str = "3D model UI") -> tuple[str, str, str]:
        """
        Create a new Onshape document and locate its Part Studio element.

        Returns:
            (document_id, workspace_id, element_id)
        """
        doc  = self._post(f"{self.base}/api/documents", {"name": name})
        did  = doc["id"]
        wid  = doc["defaultWorkspace"]["id"]

        elements = self._get(
            f"{self.base}/api/documents/d/{did}/w/{wid}/elements"
            "?elementType=PARTSTUDIO&withThumbnails=false"
)
        eid = next(e["id"] for e in elements if e["elementType"] == "PARTSTUDIO")
        return did, wid, eid

        raise RuntimeError("No Part Studio found in the newly created document.")

    def features_url(self, did: str, wid: str, eid: str) -> str:
        return f"{self.base}/api/v7/partstudios/d/{did}/w/{wid}/e/{eid}/features"

    # Payloads  (OnShape ma sketch, other bodies banauna)

    def _sketch_payload(
        self,
        name: str,
        view_name: str,
        sketch_entities: list[dict],
        constraints: list[dict] | None = None,
    ) -> dict:
        plane_id = view_name.capitalize()
        return {
            "feature": {
                "btType":      "BTMSketch-151",
                "featureType": "newSketch",
                "name":        name,
                "parameters": [
                    {
                        "btType": "BTMParameterQueryList-148",
                        "queries": [
                            {
                                "btType":      "BTMIndividualQuery-138",
                                "queryString": (
                                    f"query = qCreatedBy(makeId(\"{plane_id}\"), EntityType.FACE);"
                                ),
                            }
                        ],
                        "parameterId": "sketchPlane",
                    }
                ],
                "entities":    sketch_entities,
                "constraints": constraints or [],
            }
        }

    def _extrude_payload(
        self,
        name: str,
        sketch_fid: str,
        *,
        operation: str = "NEW",
        depth: float = None,      
        symmetric: bool = True,
        opposite_direction: bool = False,
    ) -> dict:
        if depth is None:           
            raise ValueError(f"extrude_payload called without explicit depth for '{name}'")
        return {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType":      "BTMFeature-134",
                "featureType": "extrude",
                "name":        name,
                "suppressed":  False,
                "parameters": [
                    {"btType": "BTMParameterEnum-145",     "value": "SOLID",    "enumName": "ExtendedToolBodyType",  "parameterId": "bodyType"},
                    {"btType": "BTMParameterEnum-145",     "value": operation,  "enumName": "NewBodyOperationType",  "parameterId": "operationType"},
                    {
                        "btType": "BTMParameterQueryList-148",
                        "queries": [{"btType": "BTMIndividualQuery-138",
                                     "queryString": f"query = qSketchRegion(makeId(\"{sketch_fid}\"), true);",
                                     "hasUserCode": False}],
                        "parameterId": "entities",
                    },
                    {"btType": "BTMParameterEnum-145",     "value": "BLIND",   "enumName": "BoundingType",          "parameterId": "endBound"},
                    {"btType": "BTMParameterQuantity-147", "expression": depth,                                      "parameterId": "depth"},
                    {"btType": "BTMParameterBoolean-144",  "value": symmetric,                                       "parameterId": "symmetric"},
                    {"btType": "BTMParameterBoolean-144",  "value": opposite_direction,                              "parameterId": "oppositeDirection"},
                ],
            },
        }

    def _revolve_payload(
        self,
        name: str,
        sketch_fid: str,
        axis_sketch_fid: str,
        axis_entity_id: str,
        *,
        operation: str = "NEW",
    ) -> dict:
        return {
            "btType": "BTFeatureDefinitionCall-1406",
            "feature": {
                "btType":      "BTMFeature-134",
                "featureType": "revolve",
                "name":        name,
                "suppressed":  False,
                "parameters": [
                    {"btType": "BTMParameterEnum-145", "value": "SOLID",    "enumName": "ExtendedToolBodyType", "parameterId": "bodyType"},
                    {"btType": "BTMParameterEnum-145", "value": operation,  "enumName": "NewBodyOperationType", "parameterId": "operationType"},
                    {"btType": "BTMParameterEnum-145", "value": "FULL",     "enumName": "RevolveType",          "parameterId": "revolveType"},
                    {
                        "btType": "BTMParameterQueryList-148",
                        "queries": [{"btType": "BTMIndividualQuery-138",
                                     "queryString": f"query = qSketchRegion(makeId(\"{sketch_fid}\"), true);",
                                     "hasUserCode": False}],
                        "parameterId": "entities",
                    },
                    {
                        "btType": "BTMParameterQueryList-148",
                        "queries": [{"btType": "BTMIndividualQuery-138",
                                     "queryStatement": None,
                                     "queryString": (
                                         f"query = sketchEntityQuery(makeId(\"{axis_sketch_fid}\"), "
                                         f"EntityType.EDGE, \"{axis_entity_id}\");"
                                     ),
                                     "hasUserCode": False}],
                        "parameterId": "axis",
                    },
                ],
            },
        }

    def add_sketch(self, url, name, view_name, sketch_entities,
                view_entities=None, defer_eval=False):          
        constraints = (
            build_sketch_constraints(view_entities, sketch_entities)
            if view_entities else []
        )
        payload = self._sketch_payload(name, view_name, sketch_entities, constraints)
        data = self._post_feature(url, payload, defer_eval=defer_eval)
        return data["feature"]["featureId"]


    def add_extrude(self, url: str, name: str, sketch_fid: str, defer_eval: bool = False, **kwargs) -> str:
        payload = self._extrude_payload(name, sketch_fid, **kwargs)
        data = self._post_feature(url, payload, defer_eval=defer_eval)
        return data["feature"]["featureId"]

    def add_revolve(self, url: str, name: str, sketch_fid: str, axis_sketch_fid: str, axis_entity_id: str, defer_eval: bool = False, **kwargs) -> str:
        payload = self._revolve_payload(name, sketch_fid, axis_sketch_fid, axis_entity_id, **kwargs)
        data = self._post_feature(url, payload, defer_eval=defer_eval)
        return data["feature"]["featureId"]


    def _build_axis_entity(self, axis_data: dict, entity_id: str = "revolve-axis") -> dict:
        """Return a construction-line sketch entity dict for the revolve axis."""
        return {
            "btType":     "BTMSketchCurveSegment-155",
            "startParam": 0.0,
            "endParam":   1.0,
            "geometry": {
                "btType": "BTCurveGeometryLine-117",
                "pntX":   axis_data["start_x"] * _MM_TO_M,
                "pntY":   axis_data["start_y"] * _MM_TO_M,
                "dirX":   (axis_data["end_x"] - axis_data["start_x"]) * _MM_TO_M,
                "dirY":   (axis_data["end_y"] - axis_data["start_y"]) * _MM_TO_M,
            },
            "entityId":       entity_id,
            "startPointId":   f"{entity_id}.start",
            "endPointId":     f"{entity_id}.end",
            "isConstruction": True,
        }

    def _resolve_axis(
        self,
        features_url: str,
        view_name: str,
        idx: int,
        revolve_axis: dict | None,
        sketch_entities: list[dict],
        view_entities: list[dict],
    ) -> tuple[str | None, str | None, list[dict]]:
        """
        Attempt to post a dedicated axis sketch.  Falls back to appending a
        horizontal construction line to *sketch_entities* when the dedicated
        sketch fails or no axis data is available.

        Returns:
            (axis_sketch_fid, axis_entity_id, sketch_entities)
            axis_sketch_fid is None when the axis was appended inline.
        """
        axis_sketch_fid: str | None = None
        axis_entity_id:  str | None = None

        if self._axis_data_valid(revolve_axis):
            axis_id     = "revolve-axis"
            axis_entity = self._build_axis_entity(revolve_axis, axis_id)
            axis_sketch_fid = self.add_sketch(
                features_url,
                f"SketchAxis {idx} ({view_name})",
                view_name,
                [axis_entity],
            )
            axis_entity_id = axis_id


        # Fallback: embed axis as construction line in the profile sketch.
        if not axis_sketch_fid:
            max_x = max(
                (e.get("end_x", 0) for e in view_entities if "end_x" in e),
                default=100,
            ) * _MM_TO_M
            axis_id     = "revolve-axis-line"
            axis_entity = {
                "btType":     "BTMSketchCurveSegment-155",
                "startParam": 0.0,
                "endParam":   1.0,
                "geometry": {
                    "btType": "BTCurveGeometryLine-117",
                    "pntX":   0.0,
                    "pntY":   0.0,
                    "dirX":   max_x,
                    "dirY":   0.0,
                },
                "entityId":       axis_id,
                "startPointId":   f"{axis_id}.start",
                "endPointId":     f"{axis_id}.end",
                "isConstruction": True,
            }
            sketch_entities = [*sketch_entities, axis_entity]
            axis_entity_id  = axis_id

        return axis_sketch_fid, axis_entity_id, sketch_entities


    def build_plate(self, features_url: str, views: list[dict], stop_event=None, metadata: dict = None) -> None:
        """Extrude-intersect plate workflow."""
        prev_fid: str | None = None
        
         # ── NEW: flat-plate short-circuit ────────────────────────────────────
        meta = metadata or {}
        if meta.get("part_type") == "flat_plate":
            view = next((v for v in views if v.get("is_main_face")), views[0] if views else None)
            if view:
                depth     = meta.get("extrude_depth", 1000)
                view_name = view.get("name", "front").lower()
                entities  = view.get("entities", [])
                sketch_ents = build_sketch_entities(entities)
                sketch_fid  = self.add_sketch(features_url, f"Sketch ({view_name})", view_name, sketch_ents, view_entities=entities)
                self.add_extrude(features_url, f"Extrude ({view_name})", sketch_fid, depth=depth, symmetric=True)
            return
   

        for idx, view in enumerate(views, start=1):
            if stop_event and stop_event.is_set():
                print("Cancelled during build_plate")
                return
            view_name = view.get("name", f"view{idx}").lower()
            if view_name not in self.SUPPORTED_VIEWS:
                continue

            entities = view.get("entities", [])
            if not entities:
                continue

            sketch_entities = build_sketch_entities(entities)
            sketch_fid = self.add_sketch(
                    features_url,
                    f"Sketch {idx} ({view_name})",
                    view_name,
                    sketch_entities,
                    view_entities=entities,      
)

            operation         = "NEW" if prev_fid is None else "INTERSECT"
            opposite_dir      = prev_fid is None         

            prev_fid = self.add_extrude(
                features_url,
                f"Extrude {idx} ({view_name})",
                sketch_fid,
                operation=operation,
                opposite_direction=opposite_dir,
            )

    def build_shaft(
            self,
            features_url: str,
            views: list[dict],
            revolve_axis: dict | None,
            stop_event=None
        ) -> None:
            """Revolve-intersect shaft workflow."""
            prev_fid: str | None = None

            for idx, view in enumerate(views, start=1):
                if stop_event and stop_event.is_set():
                    print("Cancelled during build_shaft")
                    return
                view_name = view.get("name", f"view{idx}").lower()
                if view_name not in self.SUPPORTED_VIEWS:
                    continue

                entities = view.get("entities", [])
                if not entities:
                    continue

                sketch_entities, last_id = build_sketch_entities(entities, return_last_id=True)

                # --- Axis sketch (dedicated) ---
                axis_sketch_fid: str | None = None
                axis_entity_id: str | None  = None

                if revolve_axis and isinstance(revolve_axis, dict) and "start_x" in revolve_axis:
                    axis_id     = "revolve-axis"
                    axis_entity = self._build_axis_entity(revolve_axis, axis_id)
                    try:
                        axis_sketch_fid = self.add_sketch(
                            features_url,
                            f"SketchAxis {idx} ({view_name})",
                            view_name,
                            [axis_entity],
                        )
                        axis_entity_id = axis_id
                    except requests.HTTPError:
                        axis_sketch_fid = None
                # Fallback: append horizontal axis to profile sketch
                if not axis_sketch_fid:
                    max_x = max(
                        (e.get("end_x", 0) for e in entities if "end_x" in e),
                        default=100,
                    ) * _MM_TO_M
                    axis_id     = "revolve-axis-line"
                    axis_entity = {
                        "btType":     "BTMSketchCurveSegment-155",
                        "startParam": 0.0,
                        "endParam":   1.0,
                        "geometry": {
                            "btType": "BTCurveGeometryLine-117",
                            "pntX":   0.0,
                            "pntY":   0.0,
                            "dirX":   max_x,
                            "dirY":   0.0,
                        },
                        "entityId":       axis_id,
                        "startPointId":   f"{axis_id}.start",
                        "endPointId":     f"{axis_id}.end",
                        "isConstruction": True,
                    }
                    sketch_entities.append(axis_entity)
                    axis_entity_id = axis_id

                # Profile sketch
                sketch_fid = self.add_sketch(
                    features_url,
                    f"Sketch {idx} ({view_name})",
                    view_name,
                    sketch_entities,
                )

                axis_ref = axis_sketch_fid if axis_sketch_fid else sketch_fid
                if not axis_entity_id:
                    axis_entity_id = last_id

                operation = "NEW" if prev_fid is None else "INTERSECT"
                prev_fid  = self.add_revolve(
                    features_url,
                    f"Revolve {idx} ({view_name})",
                    sketch_fid,
                    axis_ref,
                    axis_entity_id,
                    operation=operation,
                )
                time.sleep(0.2)
            
# This pipeline is used to convert 2D images to 3D models in OnShape

def convert_to_3d(
    image: str | Path | bytes | BytesIO,
    file_stem: str,
    image_bytes: bytes,
    stop_event = None,
    user_id: int = None,     
    user_prompt: str = None,
    *,
    output_dir: str | None = None,
) -> tuple[str, Path, Path]:
    """
    Full pipeline: image → Gemini → JSON → Onshape 3D model.

    Args:
        image:        File path, raw bytes, or BytesIO of the input image.
        file_stem:    Stem used for output file names (e.g. ``"bracket"``).
        image_bytes:  Raw bytes of the image (saved to DB).
        stop_event:   Optional threading event to cancel the pipeline mid-run.
        output_dir:   Directory for output JSON files (defaults to project data dir).

    Returns:
        (onshape_document_url, gemini_json_path, converted_json_path)
    """
    def cancelled():
        """Returns True if the client cancelled the request"""
        return stop_event is not None and stop_event.is_set()

    cfg = load_config()
    # save_image(image_bytes)
    if cancelled():
        return None

    gemini_client = get_gemini_client(cfg["gemini_api_key"])
    
    # Auto-detect whether the image is a plate or shaft, then load the right prompt.
    part_type = detect_part_type(image, gemini_client, cfg["gemini_model"],stop_event=stop_event)
    if cancelled():
        return None

    prompt = load_prompt(part_type, user_prompt)
    print(f"prompt from voncert {prompt}")
    gemini_json = call_gemini(image, prompt, gemini_client, model=cfg["gemini_model"])
    print(gemini_json)
    if cancelled():
        return None
    # gemini_path, converted_path = make_output_paths(file_stem, output_dir)
    # gemini_path.write_text(json.dumps(gemini_json, indent=2, ensure_ascii=False), encoding="utf-8")

    converted_json = convert_json_format(gemini_json)
    # converted_path.write_text(json.dumps(converted_json, indent=2), encoding="utf-8")
    print(f"[DEBUG] converted_json keys: {list(converted_json.keys())}")        # ← add
    print(f"[DEBUG] metadata: {converted_json.get('metadata')}")                
    if cancelled():
        return None
    session = OnshapeSession(cfg["onshape_access"], cfg["onshape_secret"], cfg["onshape_base"])
    did, wid, eid = session.create_document("3D UI")
    features_url = session.features_url(did, wid, eid)
    if cancelled():
        return None
    is_shaft = "revolve_axis" in converted_json
    revolve_axis = converted_json.get("revolve_axis")
    views        = converted_json.get("views", [])

    if is_shaft:
        session.build_shaft(features_url, views, revolve_axis)
    else:
       session.build_plate(features_url, views, metadata=converted_json.get("metadata", {}))

    # print(gemini_path, converted_path)

    doc_url = f"{cfg['onshape_base']}/documents/{did}/w/{wid}/e/{eid}"
    save_history(
        image_bytes=image_bytes,
        user_id=user_id,
        filename=file_stem,
        gemini_json=gemini_json,
        converted_json=converted_json,
        history_type="convert_to_3d",
        doc_url=doc_url,
    )
    return doc_url