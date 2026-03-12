# import json
# import math
# import os
# import time
# from io import BytesIO
# from pathlib import Path

# import numpy as np
# import requests
# import yaml
# from dotenv import load_dotenv
# from PIL import Image

# import google.genai as genai
# from google.genai import types
# from onshape_client.client import Client
# from app.services.to_db import save_image, save_json


# def load_config() -> dict:
#     """Load environment variables and return a config dict."""
#     load_dotenv()

#     config = {
#         "gemini_api_key": os.getenv("GEMINI_PAID_KEY"),
#         "onshape_access":  os.getenv("access"),
#         "onshape_secret":  os.getenv("secret"),
#         "onshape_base":    "https://cad.onshape.com",
#         "gemini_model":    "gemini-3-pro-preview",
#     }

#     missing = [k for k, v in config.items() if not v and k != "onshape_base"]
#     if missing:
#         raise EnvironmentError(f"Missing required environment variables for keys: {missing}")

#     return config


# def load_prompt(prompt_file: str = "prompt.yml") -> str:
#     """Load the Gemini prompt from a YAML file."""
    
#     base_dir = Path(__file__).resolve().parent
#     full_path = base_dir / prompt_file 


#     with open(full_path, "r", encoding="utf-8") as fh:
#         data = yaml.safe_load(fh)

#     return data["prompt"]

# def sanitize_name(name: str) -> str:
#     """Strip unsafe characters from a filename stem."""
#     return "".join(c for c in name if c.isalnum() or c in ("-", "_"))

# def make_output_paths(file_stem: str, output_dir: str | None = None) -> tuple[Path, Path]:
#     file_name_only = Path(file_stem).stem

#     # Use environment variable first
#     data_dir = os.getenv("DATA_DIR")

#     if output_dir:
#         base = Path(output_dir)
#     elif data_dir:
#         base = Path(data_dir) / file_name_only
#     else:
#         # fallback for local dev (optional)
#         current_folder = Path(__file__).resolve().parent
#         base_project_folder = current_folder
#         while base_project_folder.name != "Solidify":
#             if base_project_folder.parent == base_project_folder:
#                 raise FileNotFoundError("Could not find 'Solidify' folder in parent hierarchy")
#             base_project_folder = base_project_folder.parent
#         base = base_project_folder / "data" / file_name_only

#     base.mkdir(parents=True, exist_ok=True)

#     safe = sanitize_name(file_name_only)

#     gemini_path    = base / f"{safe}_gemini.json"
#     converted_path = base / f"{safe}_converted.json"

#     gemini_path.touch(exist_ok=True)
#     converted_path.touch(exist_ok=True)

#     return gemini_path, converted_path


# def prepare_image(image: Image.Image) -> Image.Image:
#     """Ensure the image is in RGB mode, converting if necessary."""
#     if image.mode not in ("RGB", "RGBA"):
#         return image.convert("RGB")
#     return image


# def open_image(source: str | Path | bytes | BytesIO) -> Image.Image:
#     """Open an image from a file path or raw bytes."""
#     if isinstance(source, (str, Path)):
#         return Image.open(source)
#     if isinstance(source, bytes):
#         return Image.open(BytesIO(source))
#     return Image.open(source)


# def get_gemini_client(api_key: str) -> genai.Client:
#     """Instantiate and return a Gemini client."""
#     return genai.Client(api_key=api_key)


# def call_gemini(
#     image: Image.Image,
#     prompt: str,
#     client: genai.Client,
#     model: str = "gemini-3.1-pro-preview",
# ) -> dict:
#     """
#     Send an image + prompt to Gemini and return the parsed JSON response.

#     Raises:
#         ValueError: If the response cannot be parsed as JSON.
#     """
#     config = types.GenerateContentConfig(
#         response_mime_type="application/json",
#         temperature=0.2,
#     )

#     response = client.models.generate_content(
#         model=model,
#         contents=[image, prompt],
#         config=config,
#     )

#     try:
#         return json.loads(response.text)
#     except json.JSONDecodeError as exc:
#         raise ValueError(f"Gemini returned non-JSON response: {exc}") from exc



# def _unit_vector(a: np.ndarray, b: np.ndarray) -> np.ndarray:
#     """Return the unit direction vector from point *a* to point *b*."""
#     direction = b - a
#     norm = np.linalg.norm(direction)
#     return direction / norm if norm else np.zeros(2)


# def _arc_center(
#     start: np.ndarray,
#     end: np.ndarray,
#     radius: float,
#     prev_seg: dict | None,
#     next_seg: dict | None,
# ) -> np.ndarray:
#     """
#     Compute the arc center that best satisfies tangency with adjacent segments.
#     Falls back to the chord midpoint when tangency cannot be resolved.
#     """
#     dx, dy = end - start
#     chord = math.hypot(dx, dy)

#     if chord == 0:
#         return start.copy()

#     h = math.sqrt(max(radius**2 - (chord / 2) ** 2, 0))
#     mid  = (start + end) / 2
#     perp = np.array([-dy, dx]) / chord

#     c1 = mid + h * perp
#     c2 = mid - h * perp

#     def tangency_score(center: np.ndarray, point: np.ndarray, seg: dict) -> float:
#         """Dot product of arc tangent with adjacent line direction at *point*."""
#         to_c = center - point
#         norm  = np.linalg.norm(to_c)
#         if norm == 0:
#             return 0.0
#         to_c /= norm
#         tangent   = np.array([-to_c[1], to_c[0]])
#         seg_start = np.array([seg["start_point"][0], seg["start_point"][1]])
#         seg_end   = np.array([seg["end_point"][0],   seg["end_point"][1]])
#         return abs(np.dot(tangent, _unit_vector(seg_start, seg_end)))

#     for seg, point in [(prev_seg, start), (next_seg, end)]:
#         if seg is not None and seg["type"] == "line":
#             return c1 if tangency_score(c1, point, seg) >= tangency_score(c2, point, seg) else c2

#     return c1


# def _cad_angle(point: np.ndarray, center: np.ndarray) -> float:
#     """
#     Compute the Onshape-convention angle (clockwise from +X) in degrees.
#     """
#     angle = math.degrees(math.atan2(point[1] - center[1], point[0] - center[0]))
#     angle = (-angle) % 360
#     return angle


# def _is_clockwise(start: np.ndarray, end: np.ndarray, center: np.ndarray) -> bool:
#     """Return True if the arc from *start* to *end* around *center* is clockwise."""
#     to_s = start - center
#     to_e = end   - center
#     return (to_s[0] * to_e[1] - to_s[1] * to_e[0]) < 0


# def _normalize_cw_angles(start: float, end: float) -> tuple[float, float]:
#     """Ensure end > start for a clockwise arc sweep."""
#     start %= 360
#     end   %= 360
#     if end <= start:
#         end += 360
#     return start, end



# def _intermediate_entity(raw: dict) -> dict:
#     """Convert a raw Gemini entity into a normalised intermediate dict."""
#     kind = raw["type"].upper()
#     if kind == "LINE":
#         return {
#             "type": "line",
#             "start_point": [raw["start_x"], raw["start_y"]],
#             "end_point":   [raw["end_x"],   raw["end_y"]],
#         }
#     if kind == "ARC":
#         return {
#             "type": "arc",
#             "start_point": [raw["start_x"], raw["start_y"]],
#             "end_point":   [raw["end_x"],   raw["end_y"]],
#             "radius":       raw["radius"],
#         }
#     if kind == "CIRCLE":
#         return {
#             "type":     "circle",
#             "center_x": raw["center_x"],
#             "center_y": raw["center_y"],
#             "radius":   raw["radius"],
#         }
#     raise ValueError(f"Unknown entity type: {raw['type']}")


# def _convert_entity(entity: dict, idx: int, siblings: list[dict]) -> dict:
#     """Convert an intermediate entity to the final Onshape-ready format."""
#     kind = entity["type"]

#     if kind == "line":
#         sx, sy = entity["start_point"]
#         ex, ey = entity["end_point"]
#         return {
#             "type":    "LINE",
#             "start_x": round(sx, 2),
#             "start_y": round(sy, 2),
#             "end_x":   round(ex, 2),
#             "end_y":   round(ey, 2),
#         }

#     if kind == "circle":
#         return {
#             "type":     "CIRCLE",
#             "center_x": round(entity["center_x"], 2),
#             "center_y": round(entity["center_y"], 2),
#             "radius":   round(entity["radius"],   2),
#         }

#     if kind == "arc":
#         prev_seg = siblings[idx - 1] if idx > 0 else None
#         next_seg = siblings[idx + 1] if idx < len(siblings) - 1 else None

#         start  = np.array(entity["start_point"])
#         end    = np.array(entity["end_point"])
#         center = _arc_center(start, end, entity["radius"], prev_seg, next_seg)

#         if np.isnan(center).any():
#             center = (start + end) / 2

#         if not _is_clockwise(start, end, center):
#             start, end = end, start

#         sa = _cad_angle(start, center)
#         ea = _cad_angle(end,   center)
#         sa, ea = _normalize_cw_angles(sa, ea)

#         return {
#             "type":        "ARC",
#             "center_x":    round(center[0],        2),
#             "center_y":    round(center[1],        2),
#             "radius":      round(entity["radius"], 2),
#             "start_angle": round(sa, 2),
#             "end_angle":   round(ea, 2),
#             "clockwise":   True,
#         }

#     raise ValueError(f"Unhandled intermediate entity type: {kind}")


# def convert_json_format(gemini_json: dict) -> dict:
#     """
#     Transform Gemini-output JSON into the Onshape-ready JSON format.

#     - For plates → convert all views normally.
#     - For shafts (revolve_axis present) →
#         * Convert FRONT normally
#         * Detect SECTION view
#         * Project SECTION entities into FRONT
#         * Return only FRONT view
#     """

#     output: dict = {"views": []}
#     revolve_axis = gemini_json.get("revolve_axis")

#     if revolve_axis:
#         output["revolve_axis"] = revolve_axis

#     # --------------------------------------------------
#     # Normalize view names
#     # --------------------------------------------------
#     raw_views: dict[str, dict] = {}
#     for view in gemini_json.get("views", []):
#         name = view.get("name", "").strip().lower()
#         raw_views[name] = view

#     # --------------------------------------------------
#     # Detect section view robustly
#     # --------------------------------------------------
#     section_view = None
#     for name, view in raw_views.items():
#         if any(key in name for key in ["section", "a-a", "aa", "cut"]):
#             section_view = view
#             break

#     # --------------------------------------------------
#     # SHAFT CASE (revolve)
#     # --------------------------------------------------
#     if revolve_axis:

#         front_view = raw_views.get("front")
#         if not front_view:
#             raise ValueError("Front view is required for shaft conversion.")

#         # ---- Convert FRONT normally using your arc logic ----
#         front_intermediates = [
#             _intermediate_entity(e) for e in front_view.get("entities", [])
#         ]
#         converted_front = [
#             _convert_entity(e, i, front_intermediates)
#             for i, e in enumerate(front_intermediates)
#         ]

#         # ---- If section exists, project into FRONT ----
#         if section_view:

#             axis_start = np.array([revolve_axis["start_x"], revolve_axis["start_y"]])
#             axis_end   = np.array([revolve_axis["end_x"], revolve_axis["end_y"]])
#             axis_vec   = axis_end - axis_start

#             horizontal_axis = abs(axis_vec[1]) < abs(axis_vec[0])

#             section_intermediates = [
#                 _intermediate_entity(e) for e in section_view.get("entities", [])
#             ]

#             for ent in section_intermediates:

#                 if ent["type"] == "circle":

#                     if horizontal_axis:
#                         projected = {
#                             "type": "CIRCLE",
#                             "center_x": round(ent["center_x"], 2),
#                             "center_y": round(axis_start[1], 2),
#                             "radius": round(ent["radius"], 2),
#                         }
#                     else:
#                         projected = {
#                             "type": "CIRCLE",
#                             "center_x": round(axis_start[0], 2),
#                             "center_y": round(ent["center_y"], 2),
#                             "radius": round(ent["radius"], 2),
#                         }

#                     converted_front.append(projected)

#                 elif ent["type"] in ["line", "arc"]:
#                     # Convert section geometry using same arc logic
#                     idx = section_intermediates.index(ent)
#                     converted = _convert_entity(ent, idx, section_intermediates)
#                     converted_front.append(converted)

#         output["views"].append({
#             "name": "front",
#             "entities": converted_front,
#             "metadata": front_view.get("metadata", {"units": "mm", "scale": 1}),
#         })

#         return output

#     # --------------------------------------------------
#     # PLATE CASE (normal multi-view workflow)
#     # --------------------------------------------------
#     for view in gemini_json.get("views", []):
#         intermediates = [_intermediate_entity(e) for e in view["entities"]]
#         converted     = [
#             _convert_entity(e, i, intermediates)
#             for i, e in enumerate(intermediates)
#         ]

#         output["views"].append({
#             "name": view["name"],
#             "entities": converted,
#             "metadata": view.get("metadata", {"units": "mm", "scale": 1}),
#         })

#     return output

# _MM_TO_M = 1 / 1000

# def _line_sketch_entity(entity: dict, uid: str) -> dict:
#     dx = (entity["end_x"] - entity["start_x"]) * _MM_TO_M
#     dy = (entity["end_y"] - entity["start_y"]) * _MM_TO_M
#     return {
#         "btType":       "BTMSketchCurveSegment-155",
#         "startParam":   0.0,
#         "endParam":     1.0,
#         "geometry": {
#             "btType": "BTCurveGeometryLine-117",
#             "pntX":   entity["start_x"] * _MM_TO_M,
#             "pntY":   entity["start_y"] * _MM_TO_M,
#             "dirX":   dx,
#             "dirY":   dy,
#         },
#         "entityId":      uid,
#         "startPointId":  f"{uid}.start",
#         "endPointId":    f"{uid}.end",
#     }


# def _arc_sketch_entity(entity: dict, uid: str) -> dict:
#     return {
#         "btType":     "BTMSketchCurveSegment-155",
#         "startParam": math.radians(entity["start_angle"]),
#         "endParam":   math.radians(entity["end_angle"]),
#         "geometry": {
#             "btType":    "BTCurveGeometryCircle-115",
#             "radius":    entity["radius"]   * _MM_TO_M,
#             "xCenter":   entity["center_x"] * _MM_TO_M,
#             "yCenter":   entity["center_y"] * _MM_TO_M,
#             "xDir":      1.0,
#             "yDir":      0.0,
#             "clockwise": entity.get("clockwise", True),
#         },
#         "entityId":     uid,
#         "centerId":     f"{uid}.center",
#         "startPointId": f"{uid}.start",
#         "endPointId":   f"{uid}.end",
#     }


# def _circle_sketch_entity(entity: dict, uid: str) -> dict:
#     return {
#         "btType": "BTMSketchCurve-4",
#         "geometry": {
#             "btType":    "BTCurveGeometryCircle-115",
#             "radius":    entity["radius"]   * _MM_TO_M,
#             "xCenter":   entity["center_x"] * _MM_TO_M,
#             "yCenter":   entity["center_y"] * _MM_TO_M,
#             "xDir":      1.0,
#             "yDir":      0.0,
#             "clockwise": True,
#         },
#         "entityId": uid,
#         "centerId": f"{uid}.center",
#     }


# def build_sketch_entities(
#     view_entities: list[dict],
#     *,
#     return_last_id: bool = False,
# ) -> list[dict] | tuple[list[dict], str | None]:
#     """
#     Convert view entities into Onshape sketch entity dicts.

#     Args:
#         view_entities:  List of converted entities (LINE / ARC / CIRCLE).
#         return_last_id: When True, also returns the last entity ID assigned.

#     Returns:
#         A list of sketch entity dicts, or a ``(list, last_id)`` tuple.
#     """
#     builders = {
#         "LINE":   _line_sketch_entity,
#         "ARC":    _arc_sketch_entity,
#         "CIRCLE": _circle_sketch_entity,
#     }
#     prefix_map = {"LINE": "line", "ARC": "arc", "CIRCLE": "circle"}

#     sketch_entities: list[dict] = []
#     last_id: str | None = None
#     counter = 0

#     for entity in view_entities:
#         kind = entity["type"]
#         uid  = f"{prefix_map[kind]}-{counter}"
#         sketch_entities.append(builders[kind](entity, uid))
#         last_id = uid
#         counter += 1

#     return (sketch_entities, last_id) if return_last_id else sketch_entities


# class OnshapeSession:
#     """Thin wrapper around the Onshape REST API for this converter."""

#     SUPPORTED_VIEWS = {"front", "top", "right"}

#     def __init__(self, access: str, secret: str, base: str = "https://cad.onshape.com"):
#         self.auth    = (access, secret)
#         self.base    = base
#         self.headers = {
#             "Accept":       "application/json;charset=UTF-8;qs=0.09",
#             "Content-Type": "application/json;charset=UTF-8;qs=0.09",
#         }

#     def _post(self, url: str, body: dict) -> dict:
#         resp = requests.post(url, json=body, auth=self.auth, headers=self.headers)
#         resp.raise_for_status()
#         return resp.json()

#     def _get(self, url: str) -> dict:
#         resp = requests.get(url, auth=self.auth, headers=self.headers)
#         resp.raise_for_status()
#         return resp.json()


#     def create_document(self, name: str = "3D model UI") -> tuple[str, str, str]:
#         """
#         Create a new Onshape document and locate its Part Studio element.

#         Returns:
#             (document_id, workspace_id, element_id)
#         """
#         doc  = self._post(f"{self.base}/api/documents", {"name": name})
#         did  = doc["id"]
#         wid  = doc["defaultWorkspace"]["id"]

#         elements = self._get(f"{self.base}/api/documents/d/{did}/w/{wid}/elements")
#         for el in elements:
#             if el.get("elementType") == "PARTSTUDIO":
#                 return did, wid, el["id"]

#         raise RuntimeError("No Part Studio found in the newly created document.")

#     def features_url(self, did: str, wid: str, eid: str) -> str:
#         return f"{self.base}/api/v7/partstudios/d/{did}/w/{wid}/e/{eid}/features"


#     def _sketch_payload(
#         self,
#         name: str,
#         view_name: str,
#         sketch_entities: list[dict],
#     ) -> dict:
#         plane_id = view_name.capitalize()
#         return {
#             "feature": {
#                 "btType":      "BTMSketch-151",
#                 "featureType": "newSketch",
#                 "name":        name,
#                 "parameters": [
#                     {
#                         "btType": "BTMParameterQueryList-148",
#                         "queries": [
#                             {
#                                 "btType":      "BTMIndividualQuery-138",
#                                 "queryString": (
#                                     f"query = qCreatedBy(makeId(\"{plane_id}\"), EntityType.FACE);"
#                                 ),
#                             }
#                         ],
#                         "parameterId": "sketchPlane",
#                     }
#                 ],
#                 "entities":    sketch_entities,
#                 "constraints": [],
#             }
#         }

#     def _extrude_payload(
#         self,
#         name: str,
#         sketch_fid: str,
#         *,
#         operation: str = "NEW",
#         depth: float = 1000,
#         symmetric: bool = True,
#         opposite_direction: bool = False,
#     ) -> dict:
#         return {
#             "btType": "BTFeatureDefinitionCall-1406",
#             "feature": {
#                 "btType":      "BTMFeature-134",
#                 "featureType": "extrude",
#                 "name":        name,
#                 "suppressed":  False,
#                 "parameters": [
#                     {"btType": "BTMParameterEnum-145",     "value": "SOLID",    "enumName": "ExtendedToolBodyType",  "parameterId": "bodyType"},
#                     {"btType": "BTMParameterEnum-145",     "value": operation,  "enumName": "NewBodyOperationType",  "parameterId": "operationType"},
#                     {
#                         "btType": "BTMParameterQueryList-148",
#                         "queries": [{"btType": "BTMIndividualQuery-138",
#                                      "queryString": f"query = qSketchRegion(makeId(\"{sketch_fid}\"), true);",
#                                      "hasUserCode": False}],
#                         "parameterId": "entities",
#                     },
#                     {"btType": "BTMParameterEnum-145",     "value": "BLIND",   "enumName": "BoundingType",          "parameterId": "endBound"},
#                     {"btType": "BTMParameterQuantity-147", "expression": depth,                                      "parameterId": "depth"},
#                     {"btType": "BTMParameterBoolean-144",  "value": symmetric,                                       "parameterId": "symmetric"},
#                     {"btType": "BTMParameterBoolean-144",  "value": opposite_direction,                              "parameterId": "oppositeDirection"},
#                 ],
#             },
#         }

#     def _revolve_payload(
#         self,
#         name: str,
#         sketch_fid: str,
#         axis_sketch_fid: str,
#         axis_entity_id: str,
#         *,
#         operation: str = "NEW",
#     ) -> dict:
#         return {
#             "btType": "BTFeatureDefinitionCall-1406",
#             "feature": {
#                 "btType":      "BTMFeature-134",
#                 "featureType": "revolve",
#                 "name":        name,
#                 "suppressed":  False,
#                 "parameters": [
#                     {"btType": "BTMParameterEnum-145", "value": "SOLID",    "enumName": "ExtendedToolBodyType", "parameterId": "bodyType"},
#                     {"btType": "BTMParameterEnum-145", "value": operation,  "enumName": "NewBodyOperationType", "parameterId": "operationType"},
#                     {"btType": "BTMParameterEnum-145", "value": "FULL",     "enumName": "RevolveType",          "parameterId": "revolveType"},
#                     {
#                         "btType": "BTMParameterQueryList-148",
#                         "queries": [{"btType": "BTMIndividualQuery-138",
#                                      "queryString": f"query = qSketchRegion(makeId(\"{sketch_fid}\"), true);",
#                                      "hasUserCode": False}],
#                         "parameterId": "entities",
#                     },
#                     {
#                         "btType": "BTMParameterQueryList-148",
#                         "queries": [{"btType": "BTMIndividualQuery-138",
#                                      "queryString": (
#                                          f"query = sketchEntityQuery(makeId(\"{axis_sketch_fid}\"), "
#                                          f"EntityType.EDGE, \"{axis_entity_id}\");"
#                                      ),
#                                      "hasUserCode": False}],
#                         "parameterId": "axis",
#                     },
#                 ],
#             },
#         }

#     def add_sketch(
#         self, url: str, name: str, view_name: str, sketch_entities: list[dict]
#     ) -> str:
#         """Post a sketch feature; return its featureId."""
#         payload = self._sketch_payload(name, view_name, sketch_entities)
#         data = self._post(url, payload)
#         return data["feature"]["featureId"]

#     def add_extrude(self, url: str, name: str, sketch_fid: str, **kwargs) -> str:
#         payload = self._extrude_payload(name, sketch_fid, **kwargs)
#         data    = self._post(url, payload)
#         return data["feature"]["featureId"]

#     def add_revolve(
#         self,
#         url: str,
#         name: str,
#         sketch_fid: str,
#         axis_sketch_fid: str,
#         axis_entity_id: str,
#         **kwargs,
#     ) -> str:
#         payload = self._revolve_payload(name, sketch_fid, axis_sketch_fid, axis_entity_id, **kwargs)
#         data    = self._post(url, payload)
#         return data["feature"]["featureId"]

#     def _build_axis_entity(self, axis_data: dict, entity_id: str = "revolve-axis") -> dict:
#         """Return a construction-line sketch entity dict for the revolve axis."""
#         return {
#             "btType":     "BTMSketchCurveSegment-155",
#             "startParam": 0.0,
#             "endParam":   1.0,
#             "geometry": {
#                 "btType": "BTCurveGeometryLine-117",
#                 "pntX":   axis_data["start_x"] * _MM_TO_M,
#                 "pntY":   axis_data["start_y"] * _MM_TO_M,
#                 "dirX":   (axis_data["end_x"] - axis_data["start_x"]) * _MM_TO_M,
#                 "dirY":   (axis_data["end_y"] - axis_data["start_y"]) * _MM_TO_M,
#             },
#             "entityId":      entity_id,
#             "startPointId":  f"{entity_id}.start",
#             "endPointId":    f"{entity_id}.end",
#             "isConstruction": True,
#         }

#     def build_plate(self, features_url: str, views: list[dict]) -> None:
#         """Extrude-intersect plate workflow."""
#         prev_fid: str | None = None

#         for idx, view in enumerate(views, start=1):
#             view_name = view.get("name", f"view{idx}").lower()
#             if view_name not in self.SUPPORTED_VIEWS:
#                 continue

#             entities = view.get("entities", [])
#             if not entities:
#                 continue

#             sketch_entities = build_sketch_entities(entities)
#             sketch_fid = self.add_sketch(
#                 features_url,
#                 f"Sketch {idx} ({view_name})",
#                 view_name,
#                 sketch_entities,
#             )

#             operation         = "NEW" if prev_fid is None else "INTERSECT"
#             opposite_dir      = prev_fid is None         

#             prev_fid = self.add_extrude(
#                 features_url,
#                 f"Extrude {idx} ({view_name})",
#                 sketch_fid,
#                 operation=operation,
#                 opposite_direction=opposite_dir,
#             )

#     def build_shaft(
#         self,
#         features_url: str,
#         views: list[dict],
#         revolve_axis: dict | None,
#     ) -> None:
#         """Revolve-intersect shaft workflow."""
#         prev_fid: str | None = None

#         for idx, view in enumerate(views, start=1):
#             view_name = view.get("name", f"view{idx}").lower()
#             if view_name not in self.SUPPORTED_VIEWS:
#                 continue

#             entities = view.get("entities", [])
#             if not entities:
#                 continue

#             sketch_entities, last_id = build_sketch_entities(entities, return_last_id=True)

#             # --- Axis sketch (dedicated) ---
#             axis_sketch_fid: str | None = None
#             axis_entity_id: str | None  = None

#             if revolve_axis and isinstance(revolve_axis, dict) and "start_x" in revolve_axis:
#                 axis_id     = "revolve-axis"
#                 axis_entity = self._build_axis_entity(revolve_axis, axis_id)
#                 try:
#                     axis_sketch_fid = self.add_sketch(
#                         features_url,
#                         f"SketchAxis {idx} ({view_name})",
#                         view_name,
#                         [axis_entity],
#                     )
#                     axis_entity_id = axis_id
#                 except requests.HTTPError:
#                     axis_sketch_fid = None

#             # Fallback: append horizontal axis to profile sketch
#             if not axis_sketch_fid:
#                 max_x = max(
#                     (e.get("end_x", 0) for e in entities if "end_x" in e),
#                     default=100,
#                 ) * _MM_TO_M
#                 axis_id     = "revolve-axis-line"
#                 axis_entity = {
#                     "btType":     "BTMSketchCurveSegment-155",
#                     "startParam": 0.0,
#                     "endParam":   1.0,
#                     "geometry": {
#                         "btType": "BTCurveGeometryLine-117",
#                         "pntX":   0.0,
#                         "pntY":   0.0,
#                         "dirX":   max_x,
#                         "dirY":   0.0,
#                     },
#                     "entityId":       axis_id,
#                     "startPointId":   f"{axis_id}.start",
#                     "endPointId":     f"{axis_id}.end",
#                     "isConstruction": True,
#                 }
#                 sketch_entities.append(axis_entity)
#                 axis_entity_id = axis_id

#             # Profile sketch
#             sketch_fid = self.add_sketch(
#                 features_url,
#                 f"Sketch {idx} ({view_name})",
#                 view_name,
#                 sketch_entities,
#             )

#             axis_ref = axis_sketch_fid if axis_sketch_fid else sketch_fid
#             if not axis_entity_id:
#                 axis_entity_id = last_id

#             operation = "NEW" if prev_fid is None else "INTERSECT"
#             prev_fid  = self.add_revolve(
#                 features_url,
#                 f"Revolve {idx} ({view_name})",
#                 sketch_fid,
#                 axis_ref,
#                 axis_entity_id,
#                 operation=operation,
#             )
#             time.sleep(0.2)


# def convert_to_3d(
#     image: str | Path | bytes | BytesIO,
#     file_stem: str,
#     image_bytes: bytes,
#     *,
#     prompt_file: str = "prompt.yml",
#     output_dir: str | None = None
# ) -> str:
#     """
#     Full pipeline: image → Gemini → JSON → Onshape 3D model.

#     Args:
#         image_source: File path, raw bytes, or BytesIO of the input image.
#         file_stem:    Stem used for output file names (e.g. ``"bracket"``).
#         prompt_file:  Path to the YAML file containing the Gemini prompt.
#         output_dir:   Directory for output JSON files (defaults to cwd).

#     Returns:
#         URL to the generated Onshape document.
#     """
#     cfg = load_config()
    
#     save_image(image_bytes)


#     gemini_client = get_gemini_client(cfg["gemini_api_key"])
#     prompt = load_prompt(prompt_file)
#     gemini_json = call_gemini(image, prompt, gemini_client, model=cfg["gemini_model"])

#     gemini_path, converted_path = make_output_paths(file_stem, output_dir)
#     gemini_path.write_text(json.dumps(gemini_json, indent=2, ensure_ascii=False), encoding="utf-8")

#     converted_json = convert_json_format(gemini_json)
#     converted_path.write_text(json.dumps(converted_json, indent=2), encoding="utf-8")
    
#     save_json(gemini_json, converted_json)

#     session = OnshapeSession(cfg["onshape_access"], cfg["onshape_secret"], cfg["onshape_base"])
#     did, wid, eid = session.create_document("3D UI")
#     features_url = session.features_url(did, wid, eid)

#     is_shaft = "revolve_axis" in converted_json
#     revolve_axis = converted_json.get("revolve_axis")
#     views = converted_json.get("views", [])

#     if is_shaft:
#         session.build_shaft(features_url, views, revolve_axis)
#     else:
#         session.build_plate(features_url, views)
        
#     print(gemini_path, converted_path)

#     doc_url = f"{cfg['onshape_base']}/documents/{did}/w/{wid}/e/{eid}"
#     return doc_url, gemini_path, converted_path




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
from onshape_client.client import Client
from app.services.to_db import save_image, save_json


def load_config() -> dict:
    """Load environment variables and return a config dict."""
    load_dotenv()

    config = {
        "gemini_api_key": os.getenv("GEMINI_PAID_KEY"),
        "onshape_access":  os.getenv("access"),
        "onshape_secret":  os.getenv("secret"),
        "onshape_base":    "https://cad.onshape.com",
        "gemini_model":    "gemini-3-pro-preview",
    }

    missing = [k for k, v in config.items() if not v and k != "onshape_base"]
    if missing:
        raise EnvironmentError(f"Missing required environment variables for keys: {missing}")

    return config


def load_prompt(prompt_file: str = "prompt.yml") -> str:
    """Load the Gemini prompt from a YAML file."""
    
    base_dir = Path(__file__).resolve().parent
    full_path = base_dir / prompt_file 


    with open(full_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    return data["prompt"]

def sanitize_name(name: str) -> str:
    """Strip unsafe characters from a filename stem."""
    return "".join(c for c in name if c.isalnum() or c in ("-", "_"))

def make_output_paths(file_stem: str, output_dir: str | None = None) -> tuple[Path, Path]:
    file_name_only = Path(file_stem).stem

    # Use environment variable first
    data_dir = os.getenv("DATA_DIR")

    if output_dir:
        base = Path(output_dir)
    elif data_dir:
        base = Path(data_dir) / file_name_only
    else:
        # fallback for local dev (optional)
        current_folder = Path(__file__).resolve().parent
        base_project_folder = current_folder
        while base_project_folder.name != "Solidify":
            if base_project_folder.parent == base_project_folder:
                raise FileNotFoundError("Could not find 'Solidify' folder in parent hierarchy")
            base_project_folder = base_project_folder.parent
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


def call_gemini(
    image: Image.Image,
    prompt: str,
    client: genai.Client,
    model: str = "gemini-3.1-pro-preview",
) -> dict:
    """
    Send an image + prompt to Gemini and return the parsed JSON response.

    Raises:
        ValueError: If the response cannot be parsed as JSON.
    """
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
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
        """Dot product of arc tangent with adjacent line direction at *point*."""
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
    """
    Compute the Onshape-convention angle (clockwise from +X) in degrees.
    """
    angle = math.degrees(math.atan2(point[1] - center[1], point[0] - center[0]))
    angle = (-angle) % 360
    return angle


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


def convert_json_format(gemini_json: dict) -> dict:
    """
    Transform Gemini-output JSON into the Onshape-ready JSON format.

    - All views (plates and shafts) are converted in a single unified loop.
    - Section view detection uses keywords: "section", "a-a", "aa"
      (note: "cut" is intentionally excluded to match app.py behaviour).
    - Section entities (CIRCLE and ARC) are appended to ANY "front" view,
      regardless of whether the part is a shaft or a plate.
    - Section ARCs are hardcoded to center (0, 0), angles 0→360 (app.py behaviour).
    - No axis-direction-based projection is applied to section circles;
      coordinates are copied as-is from the section view.
    """

    output: dict = {"views": []}
    revolve_axis = gemini_json.get("revolve_axis")

    if revolve_axis:
        output["revolve_axis"] = revolve_axis

    # --------------------------------------------------
    # Detect section view — "cut" keyword excluded
    # --------------------------------------------------
    section_view = None
    for view in gemini_json.get("views", []):
        name = view.get("name", "").strip().lower()
        if any(key in name for key in ["section", "a-a", "aa"]):
            section_view = view
            break

    # --------------------------------------------------
    # Collect section inner entities (CIRCLE and ARC only)
    # These will be appended as-is to the front view.
    # --------------------------------------------------
    section_inner_entities: list[dict] = []
    if section_view:
        for e in section_view.get("entities", []):
            t = e.get("type", "").upper()
            if t == "CIRCLE":
                # Copy coordinates as-is — no axis projection
                section_inner_entities.append({
                    "type":     "CIRCLE",
                    "center_x": round(e.get("center_x", 0.0), 2),
                    "center_y": round(e.get("center_y", 0.0), 2),
                    "radius":   round(e.get("radius",   0.0), 2),
                })
            elif t == "ARC":
                # Hardcode center/angles as per app.py behaviour
                section_inner_entities.append({
                    "type":        "ARC",
                    "center_x":    0.0,
                    "center_y":    0.0,
                    "radius":      round(e.get("radius", 0.0), 2),
                    "start_angle": 0.0,
                    "end_angle":   360.0,
                    "clockwise":   True,
                })

    # --------------------------------------------------
    # Convert ALL views in a single unified loop
    # (no separate shaft / plate branching)
    # --------------------------------------------------
    for view in gemini_json.get("views", []):
        view_name = view.get("name", "")

        intermediates = [_intermediate_entity(e) for e in view.get("entities", [])]
        converted = [
            _convert_entity(e, i, intermediates)
            for i, e in enumerate(intermediates)
        ]

        # Append section-derived entities to any "front" view
        if view_name.strip().lower() == "front" and section_inner_entities:
            converted.extend(section_inner_entities)

        output["views"].append({
            "name":     view_name,
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


class OnshapeSession:
    """Thin wrapper around the Onshape REST API for this converter."""

    SUPPORTED_VIEWS = {"front", "top", "right"}

    def __init__(self, access: str, secret: str, base: str = "https://cad.onshape.com"):
        self.auth    = (access, secret)
        self.base    = base
        self.headers = {
            "Accept":       "application/json;charset=UTF-8;qs=0.09",
            "Content-Type": "application/json;charset=UTF-8;qs=0.09",
        }

    def _post(self, url: str, body: dict) -> dict:
        resp = requests.post(url, json=body, auth=self.auth, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def _get(self, url: str) -> dict:
        resp = requests.get(url, auth=self.auth, headers=self.headers)
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

        elements = self._get(f"{self.base}/api/documents/d/{did}/w/{wid}/elements")
        for el in elements:
            if el.get("elementType") == "PARTSTUDIO":
                return did, wid, el["id"]

        raise RuntimeError("No Part Studio found in the newly created document.")

    def features_url(self, did: str, wid: str, eid: str) -> str:
        return f"{self.base}/api/v7/partstudios/d/{did}/w/{wid}/e/{eid}/features"


    def _sketch_payload(
        self,
        name: str,
        view_name: str,
        sketch_entities: list[dict],
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
                "constraints": [],
            }
        }

    def _extrude_payload(
        self,
        name: str,
        sketch_fid: str,
        *,
        operation: str = "NEW",
        depth: float = 1000,
        symmetric: bool = True,
        opposite_direction: bool = False,
    ) -> dict:
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

    def add_sketch(
        self, url: str, name: str, view_name: str, sketch_entities: list[dict]
    ) -> str:
        """Post a sketch feature; return its featureId."""
        payload = self._sketch_payload(name, view_name, sketch_entities)
        data = self._post(url, payload)
        return data["feature"]["featureId"]

    def add_extrude(self, url: str, name: str, sketch_fid: str, **kwargs) -> str:
        payload = self._extrude_payload(name, sketch_fid, **kwargs)
        data    = self._post(url, payload)
        return data["feature"]["featureId"]

    def add_revolve(
        self,
        url: str,
        name: str,
        sketch_fid: str,
        axis_sketch_fid: str,
        axis_entity_id: str,
        **kwargs,
    ) -> str:
        payload = self._revolve_payload(name, sketch_fid, axis_sketch_fid, axis_entity_id, **kwargs)
        data    = self._post(url, payload)
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
            "entityId":      entity_id,
            "startPointId":  f"{entity_id}.start",
            "endPointId":    f"{entity_id}.end",
            "isConstruction": True,
        }

    def build_plate(self, features_url: str, views: list[dict], stop_event=None) -> None:
        """Extrude-intersect plate workflow."""
        prev_fid: str | None = None

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


def convert_to_3d(
    image: str | Path | bytes | BytesIO,
    file_stem: str,
    image_bytes: bytes,
    stop_event = None,
    *,
    prompt_file: str = "prompt.yml",
    output_dir: str | None = None,
    
) -> str:
    """
    Full pipeline: image → Gemini → JSON → Onshape 3D model.

    Args:
        image_source: File path, raw bytes, or BytesIO of the input image.
        file_stem:    Stem used for output file names (e.g. ``"bracket"``).
        prompt_file:  Path to the YAML file containing the Gemini prompt.
        output_dir:   Directory for output JSON files (defaults to cwd).

    Returns:
        URL to the generated Onshape document.
    """
    def cancelled():
        """Returns True if the client cancelled the request"""
        return stop_event is not None and stop_event.is_set()
    
    cfg = load_config()
    save_image(image_bytes)
    if cancelled():
        return None
    gemini_client = get_gemini_client(cfg["gemini_api_key"])
    prompt = load_prompt(prompt_file)
    gemini_json = call_gemini(image, prompt, gemini_client, model=cfg["gemini_model"])
    if cancelled():
        return None
    gemini_path, converted_path = make_output_paths(file_stem, output_dir)
    gemini_path.write_text(json.dumps(gemini_json, indent=2, ensure_ascii=False), encoding="utf-8")

    converted_json = convert_json_format(gemini_json)
    converted_path.write_text(json.dumps(converted_json, indent=2), encoding="utf-8")
    
    save_json(gemini_json, converted_json)
    if cancelled():
        return None
    session = OnshapeSession(cfg["onshape_access"], cfg["onshape_secret"], cfg["onshape_base"])
    did, wid, eid = session.create_document("3D UI")
    features_url = session.features_url(did, wid, eid)
    if cancelled():
        return None
    is_shaft = "revolve_axis" in converted_json
    revolve_axis = converted_json.get("revolve_axis")
    views = converted_json.get("views", [])

    if is_shaft:
        session.build_shaft(features_url, views, revolve_axis)
    else:
        session.build_plate(features_url, views)
        
    print(gemini_path, converted_path)

    doc_url = f"{cfg['onshape_base']}/documents/{did}/w/{wid}/e/{eid}"
    return doc_url, gemini_path, converted_path