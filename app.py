# Full pipeline 

import streamlit as st
import os
import tempfile
from io import BytesIO
from PIL import Image, ImageOps
import json
import numpy as np
import math
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv
import requests
import time
from onshape_client.client import Client

st.set_page_config(page_title="2D to 3D Model Converter", layout="wide")
st.markdown(
    """
    <style>
    .block-container {
        padding-left: 300px;
        padding-right: 300px;
    }
    .stButton>button {
        background-color: #44b336;
        color: white;
        border-color: #44b336;
        margin-top: 30px;
    }

    .stButton>button:hover {
        background-color: #369629; 
        border-color: #369629;
        color: white;
    }
    html, body, [class*="stApp"], [class*="stBlock"] {
        font-family: Georgia, serif; 
    }
    
    /* Optionally, target the main title specifically if needed */
    h1 {
        font-family: 'Times New Roman', Times, serif; 
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("2D to 3D Model Converter")

st.markdown(
"""
Upload your 2D mechanical CAD image, get JSON data and generate 3D geometry using Gemini and Onshape.
"""
)

uploaded_file = st.file_uploader("Upload 2D raster image", type=["png", "jpg", "jpeg", "xlsx", "xlsm"])

FIXED_SIZE = (400, 300)  

if uploaded_file:
    filename = uploaded_file.name.lower()

    if not any(filename.endswith(ext) for ext in (".png", ".jpg", ".jpeg")):
        st.info("Uploaded file is not an image — preview disabled.")
    else:
        try:
            uploaded_bytes = uploaded_file.read()
            uploaded_file.seek(0)

            pil_image = Image.open(BytesIO(uploaded_bytes))

            if pil_image.mode not in ("RGB", "RGBA"):
                pil_image = pil_image.convert("RGB")

            # Fit image inside FIXED_SIZE (keep aspect ratio, no cropping)
            img_copy = pil_image.copy()
            img_copy.thumbnail(FIXED_SIZE, Image.LANCZOS)

            # Create padded background
            background = Image.new("RGB", FIXED_SIZE, (255, 255, 255))

            # Calculate centered position
            x = (FIXED_SIZE[0] - img_copy.width) // 2
            y = (FIXED_SIZE[1] - img_copy.height) // 2
            background.paste(img_copy, (x, y))

            st.image(
                background,
                caption=f"Uploaded Image — preview ({FIXED_SIZE[0]}x{FIXED_SIZE[1]})",
                use_container_width=False
            )

        except Exception as e:
            st.error(f"Could not open uploaded image: {e}")
            uploaded_file = None

if st.button("Convert to 3D"):
    if not uploaded_file:
        st.error("Please upload an image first!")
    else:
        # Remove extension from original file
        base_name = os.path.splitext(uploaded_file.name)[0]

        safe_name = "".join(c for c in base_name if c.isalnum() or c in ("-", "_"))

        tmp_dir = os.getcwd()

        # Create file paths with custom names
        gemini_output_path = os.path.join(tmp_dir, f"{safe_name}_1.json")
        converted_output_path = os.path.join(tmp_dir, f"{safe_name}_2.json")
        # jsonto3D_path = os.path.join(tmp_dir, f"{safe_name}_3.json")  

        # Optionally, create empty files
        open(gemini_output_path, "w").close()
        open(converted_output_path, "w").close()
        # open(jsonto3D_path, "w").close()

        with st.spinner("Processing... This may take a while."):
            try:

                load_dotenv()
                gemini_api_key = os.getenv("GEMINI_PAID_KEY")
                if not gemini_api_key:
                    st.error("GEMINI_PAID_KEY not found in environment variables.")
                    raise RuntimeError("Missing GEMINI_PAID_KEY")

                client = genai.Client(api_key=gemini_api_key)

                prompt = """
                Analyze the provided 2D mechanical CAD image that contains multiple views (front, top, right, etc.). If it is a plate then, perform the below activities. If the image is a shaft then avoid the "PLATE" instructions and head straight to "SHAFT" instructions.
                
                PLATE:
                
                The image contains a contour defined by a sequence of lines, arcs, and circles, along with associated 
                dimensions (lengths and radii). Your task is to accurately extract the coordinates of all unique 
                vertices, which include the endpoints of straight line segments and the tangency points of arc segments, 
                that define the main visible geometry's contour. Do NOT take dimensions and extension lines as part of 
                the geometry. 

                Steps for Coordinate Extraction:

                1. Determine the Bounding Box:
                - Calculate the absolute minimum X and minimum Y values for the entire visible geometry.

                2. Set the Origin:
                - Establish the origin (0.00, 0.00) at the absolute bottom-left corner of the geometry's 
                    bounding box. All extracted coordinates must be non-negative relative to this new origin.

                3. Trace the Contour:
                - Start the extraction from the lowest point on the leftmost side of the visible geometry 
                    and proceed sequentially along the contour.

                4. Calculate Coordinates:
                - Use the provided dimensional values (lengths and radii) to calculate the precise (X, Y) 
                    coordinates of each unique vertex (endpoints and tangency points) relative to the 
                    (0.00, 0.00) origin.

                Output Requirements:
                - Return a single, plain-text string containing only the extracted coordinates.
                - Format each coordinate pair as start_x,start_y,end_x,end_y and for arcs include radius.
                - Output must be in pure JSON format using labels L1, L2… for lines and A1, A2… for arcs.

                Strict JSON Schema:
                {
                "views": [
                    {
                    "name": "top",
                    "entities": [
                        {
                        "label": "L1",
                        "type": "LINE",
                        "start_x": 0.0,
                        "start_y": 0.0,
                        "end_x": 0.0,
                        "end_y": 29.98
                        },
                        {
                        "label": "A1",
                        "type": "ARC",
                        "start_x": 0.0,
                        "start_y": 0.0,
                        "end_x": 0.0,
                        "end_y": 37.93,
                        "radius": 10.00
                        }
                    ],
                    "metadata": {
                        "units": "mm",
                        "scale": 1
                    }
                    },
                    {
                    "name": "right",
                    "entities": [
                        {
                        "label": "L1",
                        "type": "LINE",
                        "start_x": 0.0,
                        "start_y": 5.0,
                        "end_x": 0.0,
                        "end_y": 93.78
                        },
                        {
                        "label": "C1",
                        "type": "CIRCLE",
                        "center_x": 12,
                        "center_y": 8,
                        "radius": 20
                        }
                    ],
                    "metadata": {
                        "units": "mm",
                        "scale": 1
                    }
                    }
                ]
                }

                Return ONLY the plain-text string of coordinates, nothing else. 
                
                SHAFT:
                
                If the image is a shaft then
                Analyze the provided 2D mechanical CAD image of a cylindrical shaft/pin. The image contains a front view (length and outer profile) and may contain a sectional view showing hollowness or internal bores.
                    Task:
                    1) Identify the revolve axis (centerline) and state its direction (horizontal or vertical). Include the axis in the final JSON as "revolve_axis".
                    2) Extract the outer contour from the FRONT view (upper-half profile for revolve).
                    3) If a SECTION view (labelled "section", "A-A", or similar) shows internal hollowness / bores:
                    - Measure inner diameters from that section.
                    - Project those inner profiles into the FRONT view coordinate system.
                    - Add these inner profiles as separate closed loops in the SAME "front" view entities.
                    - In section view, the solid parts are hashed and the hollow part is plain white space.
                    - Use the sectional view to detect hollowness or internal features.
                    - Include internal steps, hollowness, bore transitions, arcs, and chamfers revealed in the sectional view into the extracted geometry.
                    - Ensure all added internal segments connect end-to-end in order and match the front view's axis and coordinate system.
                    5)A fillet is a rounded corner between two intersecting lines.Fillet are same as ARC. convert fillet into arc type.
                    6)A chamfer is a straight edge connecting two intersecting lines, replacing a corner with a beveled line and are represented with distance*angle(with horizontal).Represent chamfers as LINE primitives.
                    7)If hidden lines passes through entire geometry the shaft is hollow.Strictly on such condition represent them as LINE primitives.
                        a)Section view are usually given for shafts/cylinders with internal blind or through holes.
                    8)Note:identify only mentioned primitives(LINE, CIRCLE, ARC).
                    9) Output ONLY a plain-text JSON string with coordinates in millimeters and this structure:
                    {
                    "views": [
                    {
                        "name": "front",
                        "entities": [
                        { "type":"LINE", "start_x":0.0, "start_y":0.0, "end_x":0.0, "end_y":29.98 },
                        { "type":"CIRCLE", "center_x":0.0, "center_y":0.0, "radius":16.0 }
                        ],
                        "metadata": {"units":"mm", "scale": 1 }
                    }
                    ],
                    "revolve_axis": {"start_x":0.0, "start_y":0.0, "end_x":100.0, "end_y":0.0 }
                    }
                    Notes:
                    - Use 'LINE' for straight segments, 'ARC' for curved arcs, 'CIRCLE' when an entire circle is present.
                    - Ensure the inner loop shares the same axis and center as the outer profile (concentric) whenever the drawing implies symmetry.
                    - Do not output any explanatory text — only the JSON.
                    - Check for symmetry if present.
                    - All linear, radial, angular, and diameter values MUST be copied EXACTLY as written
                      in the drawing annotations.

                """
                
                uploaded_file.seek(0)
                uploaded_bytes = uploaded_file.read()

                pil_image = Image.open(BytesIO(uploaded_bytes))

                if pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")

                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=1
                )

                response = client.models.generate_content(
                    model="gemini-3-pro-preview",
                    contents=[pil_image, prompt],
                    config=config
                )

                # Parse and save Gemini response to file (gemini_output_path)
                try:
                    response_json = json.loads(response.text)
                except Exception as e:
                    st.error("Failed to parse Gemini response as JSON.")
                    raise

                with open(gemini_output_path, "w", encoding="utf-8") as gf:
                    json.dump(response_json, gf, indent=2, ensure_ascii=False)

                

                def get_line_direction(start, end):
                    direction = end - start
                    norm = np.linalg.norm(direction)
                    if norm == 0:
                        return np.array([0.0, 0.0])
                    return direction / norm

                def calculate_arc_center_with_tangency(segment, prev_segment, next_segment):
                    start = np.array(segment['start_point'])
                    end = np.array(segment['end_point'])
                    radius = segment['radius']

                    dx = end[0] - start[0]
                    dy = end[1] - start[1]
                    chord_length = np.sqrt(dx**2 + dy**2)

                    if chord_length == 0:
                        return start

                    if chord_length > 2 * radius:
                        mid = (start + end) / 2
                        return mid
                    h_squared = radius**2 - (chord_length/2)**2
                    if h_squared < 0:
                        h_squared = 0
                    h = np.sqrt(h_squared)

                    mid = (start + end) / 2
                    if chord_length > 0:
                        perp = np.array([-dy, dx]) / chord_length
                    else:
                        perp = np.array([0.0, 1.0])

                    center1 = mid + h * perp
                    center2 = mid - h * perp

                    if prev_segment is not None and prev_segment['type'] == 'line':
                        prev_start = np.array(prev_segment['start_point'])
                        prev_end = np.array(prev_segment['end_point'])
                        line_dir = get_line_direction(prev_start, prev_end)

                        to_center1 = center1 - start
                        to_center2 = center2 - start
                        norm1 = np.linalg.norm(to_center1)
                        norm2 = np.linalg.norm(to_center2)

                        if norm1 > 0:
                            to_center1 = to_center1 / norm1
                        if norm2 > 0:
                            to_center2 = to_center2 / norm2

                        tangent1 = np.array([-to_center1[1], to_center1[0]])
                        tangent2 = np.array([-to_center2[1], to_center2[0]])

                        dot1 = abs(np.dot(tangent1, line_dir))
                        dot2 = abs(np.dot(tangent2, line_dir))

                        return center1 if dot1 > dot2 else center2

                    if next_segment is not None and next_segment['type'] == 'line':
                        next_start = np.array(next_segment['start_point'])
                        next_end = np.array(next_segment['end_point'])
                        line_dir = get_line_direction(next_start, next_end)

                        to_center1 = center1 - end
                        to_center2 = center2 - end
                        norm1 = np.linalg.norm(to_center1)
                        norm2 = np.linalg.norm(to_center2)

                        if norm1 > 0:
                            to_center1 = to_center1 / norm1
                        if norm2 > 0:
                            to_center2 = to_center2 / norm2

                        tangent1 = np.array([-to_center1[1], to_center1[0]])
                        tangent2 = np.array([-to_center2[1], to_center2[0]])

                        dot1 = abs(np.dot(tangent1, line_dir))
                        dot2 = abs(np.dot(tangent2, line_dir))

                        return center1 if dot1 > dot2 else center2

                    return center1

                def calculate_cad_angle(point, center):
                    dx = point[0] - center[0]
                    dy = point[1] - center[1]
                    angle_rad = np.arctan2(dy, dx)
                    angle_deg = np.degrees(angle_rad)
                    angle_deg = -angle_deg
                    if angle_deg < 0:
                        angle_deg += 360
                    return angle_deg

                def is_arc_clockwise(start, end, center):
                    to_start = start - center
                    to_end = end - center
                    cross = to_start[0] * to_end[1] - to_start[1] * to_end[0]
                    return cross < 0

                def normalize_angles_for_clockwise(start_angle, end_angle):
                    start_angle = start_angle % 360
                    end_angle = end_angle % 360
                    if end_angle <= start_angle:
                        end_angle += 360
                    return start_angle, end_angle

                def convert_json_format(input_json):
                    output_json = {"views": []}
                    
                    if "revolve_axis" in input_json:
                        output_json["revolve_axis"] = input_json["revolve_axis"]

                    for view in input_json["views"]:
                        view_name = view["name"]
                        input_entities = view["entities"]
                        output_entities = []

                        intermediate_entities = []
                        for entity in input_entities:
                            if entity["type"] == "LINE":
                                intermediate_entities.append({
                                    "type": "line",
                                    "start_point": [entity["start_x"], entity["start_y"]],
                                    "end_point": [entity["end_x"], entity["end_y"]]
                                })
                            elif entity["type"].upper() == "ARC":
                                intermediate_entities.append({
                                    "type": "arc",
                                    "start_point": [entity["start_x"], entity["start_y"]],
                                    "end_point": [entity["end_x"], entity["end_y"]],
                                    "radius": entity["radius"]
                                })
                            elif entity["type"].upper() == "CIRCLE":
                                intermediate_entities.append({
                                    "type": "circle",
                                    "center_x": entity["center_x"],
                                    "center_y": entity["center_y"],
                                    "radius": entity["radius"]
                                })

                        for i, entity in enumerate(intermediate_entities):
                            if entity["type"] == "line":
                                output_entities.append({
                                    "type": "LINE",
                                    "start_x": round(entity["start_point"][0], 2),
                                    "start_y": round(entity["start_point"][1], 2),
                                    "end_x": round(entity["end_point"][0], 2),
                                    "end_y": round(entity["end_point"][1], 2)
                                })
                            elif entity["type"] == "circle":
                                output_entities.append({
                                    "type": "CIRCLE",
                                    "center_x": round(entity["center_x"], 2),
                                    "center_y": round(entity["center_y"], 2),
                                    "radius": round(entity["radius"], 2)
                                })
                            elif entity["type"] == "arc":
                                prev_seg = intermediate_entities[i-1] if i > 0 else None
                                next_seg = intermediate_entities[i+1] if i < len(intermediate_entities)-1 else None

                                start = np.array(entity["start_point"])
                                end = np.array(entity["end_point"])
                                center = calculate_arc_center_with_tangency(entity, prev_seg, next_seg)

                                if np.isnan(center).any():
                                    center = (start + end) / 2

                                if is_arc_clockwise(start, end, center):
                                    arc_start = start
                                    arc_end = end
                                else:
                                    arc_start = end
                                    arc_end = start

                                start_angle = calculate_cad_angle(arc_start, center)
                                end_angle = calculate_cad_angle(arc_end, center)

                                start_angle, end_angle = normalize_angles_for_clockwise(start_angle, end_angle)
                                
                                if "revolve_axis" in input_json:
                                    output_json["revolve_axis"] = input_json["revolve_axis"]

                                output_entities.append({
                                    "type": "ARC",
                                    "center_x": round(center[0], 2),
                                    "center_y": round(center[1], 2),
                                    "radius": round(entity["radius"], 2),
                                    "start_angle": round(start_angle, 2),
                                    "end_angle": round(end_angle, 2),
                                    "clockwise": True
                                })

                        output_json["views"].append({
                            "name": view_name,
                            "entities": output_entities,
                            "metadata": view.get("metadata", {"units": "mm", "scale": 1})
                        })

                    return output_json

                # Read the gemini output JSON file (we just saved one)
                try:
                    with open(gemini_output_path, "r", encoding="utf-8") as rf:
                        input_json = json.load(rf)
                except FileNotFoundError:
                    st.error("Gemini output file not found.")
                    raise
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON from Gemini: {e}")
                    raise

                # Convert and save converted JSON
                output_json = convert_json_format(input_json)
                with open(converted_output_path, "w", encoding="utf-8") as of:
                    json.dump(output_json, of, indent=2)
                    
                has_revolve_axis = "revolve_axis" in output_json
                revolve_axis_data = output_json.get("revolve_axis", None)


                # Load Onshape credentials from env
                access = os.getenv("access")
                secret = os.getenv("secret")
                if not access or not secret:
                    st.error("Onshape 'access' or 'secret' keys not found in environment.")
                    raise RuntimeError("Missing Onshape credentials")

                auth = (access, secret)
                headers = {
                    "Accept": "application/json;charset=UTF-8;qs=0.09",
                    "Content-Type": "application/json;charset=UTF-8;qs=0.09"
                }
                base = "https://cad.onshape.com"

                onshape_client = Client(configuration={
                    "base_url": base,
                    "access_key": access,
                    "secret_key": secret
                })
                time.sleep(0.5)

                def create_sketch_entities(view_entities, return_last_id=False):
                    sketch_entities = []
                    entity_id_counter = 0
                    last_entity_id = None

                    for entity in view_entities:
                        if entity["type"] == "LINE":
                            entity_id = f"line-{entity_id_counter}"
                            line_entity = {
                                "btType": "BTMSketchCurveSegment-155",
                                "startParam": 0.0,
                                "endParam": 1.0,
                                "geometry": {
                                    "btType": "BTCurveGeometryLine-117",
                                    "pntX": entity["start_x"] / 1000,
                                    "pntY": entity["start_y"] / 1000,
                                    "dirX": (entity["end_x"] - entity["start_x"]) / 1000,
                                    "dirY": (entity["end_y"] - entity["start_y"]) / 1000
                                },
                                "entityId": entity_id,
                                "startPointId": f"{entity_id}.start",
                                "endPointId": f"{entity_id}.end"
                            }
                            sketch_entities.append(line_entity)
                            entity_id_counter += 1
                            last_entity_id = entity_id
                        elif entity["type"] == "ARC":
                            entity_id = f"arc-{entity_id_counter}"
                            arc_entity = {
                                "btType": "BTMSketchCurveSegment-155",
                                "startParam": math.radians(entity["start_angle"]),
                                "endParam": math.radians(entity["end_angle"]),
                                "geometry": {
                                    "btType": "BTCurveGeometryCircle-115",
                                    "radius": entity["radius"] / 1000,
                                    "xCenter": entity["center_x"] / 1000,
                                    "yCenter": entity["center_y"] / 1000,
                                    "xDir": 1.0,
                                    "yDir": 0.0,
                                    "clockwise": entity.get("clockwise", True)
                                },
                                "entityId": entity_id,
                                "centerId": f"{entity_id}.center",
                                "startPointId": f"{entity_id}.start",
                                "endPointId": f"{entity_id}.end"
                            }
                            sketch_entities.append(arc_entity)
                            entity_id_counter += 1
                            last_entity_id = entity_id
                        elif entity["type"] == "CIRCLE":
                            entity_id = f"circle-{entity_id_counter}"
                            circle_entity = {
                                "btType": "BTMSketchCurve-4",
                                "geometry": {
                                    "btType": "BTCurveGeometryCircle-115",
                                    "radius": entity["radius"] / 1000,
                                    "xCenter": entity["center_x"] / 1000,
                                    "yCenter": entity["center_y"] / 1000,
                                    "xDir": 1.0,
                                    "yDir": 0.0,
                                    "clockwise": True
                                },
                                "centerId": f"{entity_id}.center",
                                "entityId": entity_id
                            }
                            sketch_entities.append(circle_entity)
                            last_entity_id = entity_id
                            entity_id_counter += 1

                    if return_last_id:
                        return sketch_entities, last_entity_id
                    else:
                        return sketch_entities
                

                # Create new doc in Onshape
                doc_url = f"{base}/api/documents"
                body = {"name": "CNavi Plates"}
                doc_response = requests.post(doc_url, params={}, json=body, auth=auth, headers=headers)
                if doc_response.status_code != 200:
                    st.error(f"Document creation failed: {doc_response.text}")
                    raise RuntimeError("Onshape document creation failed")

                document_data = doc_response.json()
                did = document_data["id"]
                wid = document_data["defaultWorkspace"]["id"]

                # Find part studio element
                elements_url = f"{base}/api/documents/d/{did}/w/{wid}/elements"
                elements_response = requests.get(elements_url, auth=auth, headers=headers)
                element_data = elements_response.json()
                partstudio_id = None
                for element in element_data:
                    if element.get("elementType") == "PARTSTUDIO":
                        partstudio_id = element["id"]
                        break
                if not partstudio_id:
                    st.error("No Part Studio found in the created document.")
                    raise RuntimeError("No Part Studio in document")
                eid = partstudio_id


                # Read converted JSON (the one we created)
                with open(converted_output_path, "r", encoding="utf-8") as cf:
                    json_data = json.load(cf)

                full_url = f"{base}/api/v7/partstudios/d/{did}/w/{wid}/e/{eid}/features"

# Loop through views
                for i, view in enumerate(json_data.get("views", []), start=1):
                    view_name = view.get("name", f"view{i}").lower()

                    if view_name not in ["front", "top", "right"]:
                        continue

                    entities = view.get("entities", [])
                    if not entities:
                        continue
                
                    response_json = json.loads(response.text)

                    # 1. CHECK IF IT IS A SHAFT OR A PLATE
                    is_shaft = "revolve_axis" in response_json
                    
                    if is_shaft:
                        previous_extrude_fid = None

                        for i, view in enumerate(output_json.get("views", []), start=1):
                            view_name = view.get("name", f"view{i}").lower()
                            if view_name not in ["front", "top", "right"]:
                                continue
                            entities = view.get("entities", [])
                            if not entities:
                                st.warning(f"No entities found for view: {view_name}")
                                continue

                            sketch_entities, last_id = create_sketch_entities(entities, return_last_id=True)

                            # Prepare axis creation. We'll either create a separate axis sketch (if revolve_axis present)
                            # or append the axis into the same sketch as the profile so we can reference it reliably.
                            axis_sketch_fid = None
                            axis_entity_id = None
                            meta = view.get("metadata", {})
                            revolve_axis = output_json.get("revolve_axis") or meta.get("revolve_axis")

                            if revolve_axis and isinstance(revolve_axis, dict) and "start_x" in revolve_axis:
                                # create a dedicated sketch which only contains the construction axis
                                axis_entity_id = "revolve-axis"
                                axis_entity = {
                                    "btType": "BTMSketchCurveSegment-155",
                                    "startParam": 0.0,
                                    "endParam": 1.0,
                                    "geometry": {
                                        "btType": "BTCurveGeometryLine-117",
                                        "pntX": revolve_axis["start_x"] / 1000.0,
                                        "pntY": revolve_axis["start_y"] / 1000.0,
                                        "dirX": (revolve_axis["end_x"] - revolve_axis["start_x"]) / 1000.0,
                                        "dirY": (revolve_axis["end_y"] - revolve_axis["start_y"]) / 1000.0
                                    },
                                    "entityId": axis_entity_id,
                                    "startPointId": f"{axis_entity_id}.start",
                                    "endPointId": f"{axis_entity_id}.end",
                                    "isConstruction": True
                                }
                                axis_sketch_payload = {
                                    "feature": {
                                        "btType": "BTMSketch-151",
                                        "featureType": "newSketch",
                                        "name": f"SketchAxis {i} ({view_name})",
                                        "parameters": [
                                            {
                                                "btType": "BTMParameterQueryList-148",
                                                "queries": [
                                                    {
                                                        "btType": "BTMIndividualQuery-138",
                                                        "queryString": f"query = qCreatedBy(makeId(\"{view_name.capitalize()}\"), EntityType.FACE);"
                                                    }
                                                ],
                                                "parameterId": "sketchPlane"
                                            }
                                        ],
                                        "entities": [axis_entity],
                                        "constraints": []
                                    }
                                }
                                axis_sketch_response = requests.post(full_url, json=axis_sketch_payload, auth=auth, headers=headers)
                                if axis_sketch_response.status_code in (200, 201):
                                    axis_sketch_fid = axis_sketch_response.json()["feature"]["featureId"]
                                else:
                                    st.warning(f"Axis sketch creation failed for {view_name}: {axis_sketch_response.text}")
                                    axis_sketch_fid = None

                            if not axis_sketch_fid:
                                # no explicit axis sketch created; append a fallback horizontal axis to the profile sketch entities
                                max_x = max((e.get("end_x", 0) for e in entities if "end_x" in e), default=100) / 1000.0
                                axis_id = "revolve-axis-line"
                                axis_entity = {
                                    "btType": "BTMSketchCurveSegment-155",
                                    "startParam": 0.0,
                                    "endParam": 1.0,
                                    "geometry": {
                                        "btType": "BTCurveGeometryLine-117",
                                        "pntX": 0.0,
                                        "pntY": 0.0,
                                        "dirX": max_x,
                                        "dirY": 0.0
                                    },
                                    "entityId": axis_id,
                                    "startPointId": f"{axis_id}.start",
                                    "endPointId": f"{axis_id}.end",
                                    "isConstruction": True
                                }
                                sketch_entities.append(axis_entity)
                                axis_entity_id = axis_entity["entityId"]

                            sketch_payload = {
                                "feature": {
                                    "btType": "BTMSketch-151",
                                    "featureType": "newSketch",
                                    "name": f"Sketch {i} ({view_name})",
                                    "parameters": [
                                        {
                                            "btType": "BTMParameterQueryList-148",
                                            "queries": [
                                                {
                                                    "btType": "BTMIndividualQuery-138",
                                                    "queryString": f"query = qCreatedBy(makeId(\"{view_name.capitalize()}\"), EntityType.FACE);"
                                                }
                                            ],
                                            "parameterId": "sketchPlane"
                                        }
                                    ],
                                    "entities": sketch_entities,
                                    "constraints": []
                                }
                            }
                            sketch_response = requests.post(full_url, json=sketch_payload, auth=auth, headers=headers)
                            if sketch_response.status_code not in (200, 201):
                                st.error(f"Sketch creation failed for {view_name}: {sketch_response.text}")
                                continue
                            sketch_response_data = sketch_response.json()
                            sketch_fid = sketch_response_data['feature']['featureId']

                            # determine which sketch contains the axis entity to reference in the revolve call
                            axis_ref_sketch_fid = axis_sketch_fid if axis_sketch_fid else sketch_fid
                            if not axis_entity_id:
                                # fallback: use last_id from created sketch if axis_entity_id wasn't set explicitly
                                axis_entity_id = last_id

                            # revolve parameters: use the axis entity id and the sketch feature id that contains it
                            if previous_extrude_fid is None:
                                body_type = "SOLID"
                                operation_type = "NEW"
                            else:
                                body_type = "SOLID"
                                operation_type = "INTERSECT"

                            revolve_payload = {
                                "btType": "BTFeatureDefinitionCall-1406",
                                "feature": {
                                    "btType": "BTMFeature-134",
                                    "featureType": "revolve",
                                    "name": f"Revolve {i} ({view_name})",
                                    "suppressed": False,
                                    "parameters": [
                                        {
                                            "btType": "BTMParameterEnum-145",
                                            "value": body_type,
                                            "enumName": "ExtendedToolBodyType",
                                            "parameterId": "bodyType"
                                        },
                                        {
                                            "btType": "BTMParameterEnum-145",
                                            "value": operation_type,
                                            "enumName": "NewBodyOperationType",
                                            "parameterId": "operationType"
                                        },
                                        {
                                            "btType": "BTMParameterEnum-145",
                                            "value": "FULL",
                                            "enumName": "RevolveType",
                                            "parameterId": "revolveType"
                                        },
                                        {
                                            "btType": "BTMParameterQueryList-148",
                                            "queries": [
                                                {
                                                    "btType": "BTMIndividualQuery-138",
                                                    "queryString": f"query = qSketchRegion(makeId(\"{sketch_fid}\"), true);",
                                                    "hasUserCode": False
                                                }
                                            ],
                                            "parameterId": "entities"
                                        },
                                        {
                                            "btType": "BTMParameterQueryList-148",
                                            "queries": [
                                                {
                                                    "btType": "BTMIndividualQuery-138",
                                                    "queryStatement": None,
                                                    "queryString": f"query = sketchEntityQuery(makeId(\"{axis_ref_sketch_fid}\"), EntityType.EDGE, \"{axis_entity_id}\");",
                                                    "hasUserCode": False
                                                }
                                            ],
                                            "parameterId": "axis"
                                        }
                                    ]
                                }
                            }

                            response_revolve = requests.post(full_url, json=revolve_payload, auth=auth, headers=headers)
                            if response_revolve.status_code not in (200, 201):
                                st.error(f"Revolve failed for {view_name}: {response_revolve.status_code} {response_revolve.text}")
                                continue

                            extrude_response_data = response_revolve.json()
                            extrude_fid = extrude_response_data['feature']['featureId']
                            previous_extrude_fid = extrude_fid
                            time.sleep(0.2)
                            
                            response_revolve = requests.post(full_url, json=revolve_payload, auth=auth, headers=headers)
                            if response_revolve.status_code not in (200, 201):
                                st.error(f"Revolve failed for {view_name}: {response_revolve.status_code} {response_revolve.text}")
                                continue

                            extrude_response_data = response_revolve.json()
                            extrude_fid = extrude_response_data['feature']['featureId']
                            previous_extrude_fid = extrude_fid
                            time.sleep(0.2)
                    else:
                        previous_extrude_fid = None
                        output_json = convert_json_format(input_json)
                        # Loop through views
                        for i, view in enumerate(json_data.get("views", []), start=1):
                            view_name = view.get("name", f"view{i}")
                            if view_name not in ["front", "top", "right"]:
                                st.write(f"Skipping unsupported view name: {view_name}")
                                continue
                            entities = view.get("entities", [])
                            if not entities:
                                st.write(f"No entities found for view: {view_name}")
                                continue

                            sketch_entities = create_sketch_entities(entities)

                            plane_id = view_name.capitalize()

                            sketch_payload = {
                                "feature": {
                                    "btType": "BTMSketch-151",
                                    "featureType": "newSketch",
                                    "name": f"Sketch {i} ({view_name})",
                                    "parameters": [
                                        {
                                            "btType": "BTMParameterQueryList-148",
                                            "queries": [
                                                {
                                                    "btType": "BTMIndividualQuery-138",
                                                    "queryString": f"query = qCreatedBy(makeId(\"{plane_id}\"), EntityType.FACE);"
                                                }
                                            ],
                                            "parameterId": "sketchPlane"
                                        }
                                    ],
                                    "entities": sketch_entities,
                                    "constraints": []
                                }
                            }
                            sketch_response = requests.post(full_url, json=sketch_payload, auth=auth, headers=headers)
                            if sketch_response.status_code != 200:
                                st.warning(f"Sketch creation failed for {view_name}: {sketch_response.text}")
                                continue
                            sketch_response_data = sketch_response.json()
                            sketch_fid = sketch_response_data['feature']['featureId']

                            operation_type = "NEW" if previous_extrude_fid is None else "INTERSECT"

                            if previous_extrude_fid is None:
                                body_type = "SOLID"
                                end_bound = "BLIND"
                                extrude_depth = 1000
                                opposite_direction = True
                            else:
                                body_type = "SOLID"
                                end_bound = "BLIND"
                                extrude_depth = 1000
                                opposite_direction = False

                            extrude_payload = {
                                "btType": "BTFeatureDefinitionCall-1406",
                                "feature": {
                                    "btType": "BTMFeature-134",
                                    "featureType": "extrude",
                                    "name": f"Extrude {i} ({view_name})",
                                    "suppressed": False,
                                    "parameters": [
                                        {
                                            "btType": "BTMParameterEnum-145",
                                            "value": body_type,
                                            "enumName": "ExtendedToolBodyType",
                                            "parameterId": "bodyType"
                                        },
                                        {
                                            "btType": "BTMParameterEnum-145",
                                            "value": operation_type,
                                            "enumName": "NewBodyOperationType",
                                            "parameterId": "operationType"
                                        },
                                        {
                                            "btType": "BTMParameterQueryList-148",
                                            "queries": [
                                                {
                                                    "btType": "BTMIndividualQuery-138",
                                                    "queryString": f"query = qSketchRegion(makeId(\"{sketch_fid}\"), true);",
                                                    "hasUserCode": False
                                                }
                                            ],
                                            "parameterId": "entities"
                                        },
                                        {
                                            "btType": "BTMParameterEnum-145",
                                            "value": end_bound,
                                            "enumName": "BoundingType",
                                            "parameterId": "endBound"
                                        },
                                        {
                                            "btType": "BTMParameterQuantity-147",
                                            "expression": extrude_depth,
                                            "parameterId": "depth"
                                        },
                                        {
                                            "btType": "BTMParameterBoolean-144",
                                            "value": True,
                                            "parameterId": "symmetric"
                                        },
                                        {
                                            "btType": "BTMParameterBoolean-144",
                                            "value": opposite_direction,
                                            "parameterId": "oppositeDirection"
                                        }
                                    ]
                                }
                            }

                            response_extrude = requests.post(full_url, json=extrude_payload, auth=auth, headers=headers)
                            if response_extrude.status_code != 200:
                                st.warning(f"Extrude failed for {view_name}: {response_extrude.text}")
                                continue
                            extrude_response_data = response_extrude.json()
                            extrude_fid = extrude_response_data['feature']['featureId']
                            previous_extrude_fid = extrude_fid
                    


                doc_url = f"{base}/documents/{did}/w/{wid}/e/{eid}"
                st.success("3D Model conversion completed successfully!")
                # st.markdown(f"[Open Onshape Document]({doc_url})", unsafe_allow_html=True)
                st.markdown(
                f'<a href="{doc_url}" target="_blank" style="font-size:20px; font-weight:bold;">Open Onshape Document</a>',
                unsafe_allow_html=True )


                if os.path.exists(gemini_output_path) and os.path.exists(converted_output_path):
                    col1, col2 = st.columns(2)

                    #with col1:
                        #st.subheader("Gemini Output")
                        #with open(gemini_output_path, "r", encoding="utf-8") as f:
                         #   gemini_content = f.read()
                        #st.text_area(
                         #   label="",
                          #  value=gemini_content,
                           # height=400,  
                            #max_chars=None
                        #)

                    with col1:
                        st.subheader("Converted JSON")
                        with open(converted_output_path, "r", encoding="utf-8") as f:
                            converted_content = f.read()
                        st.text_area(
                            label="",
                            value=converted_content,
                            height=400, 
                            max_chars=None
                        )
                    with col2:
                        st.subheader("Logs:")
                        st.write(f"Gemini output: `{gemini_output_path}`")
                        st.write(f"Converted JSON: `{converted_output_path}`")

            except Exception as e:
                st.error(f"Error during conversion: {e}")