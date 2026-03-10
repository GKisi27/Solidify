"""
FastAPI wrapper for the 2D CAD Cost Estimation pipeline.

POST /estimate
  - image      : CAD image file (multipart/form-data)
  - quantity   : int
  - processes  : comma-separated string  e.g. "Laser Cutting,Waterjet Cutting"
  - materials  : comma-separated string  e.g. "mild_steel,aluminum"
  - laser_speed: float (default 5.0 mm/sec)
  - laser_power: float (default 2.0 kW)
  - laser_elec : float (default 0.12 $/kWh)
  - laser_rate : float (optional — auto-computed from power × elec if omitted)
  - wj_speed   : float (default 2.5 mm/sec)
  - wj_power   : float (default 50.0 kW)
  - wj_elec    : float (default 0.12 $/kWh)
  - wj_rate    : float (optional — auto-computed if omitted)

GET /health   → {"status": "ok"}
GET /materials → list of available material keys + names
"""

# ── Standard library ──────────────────────────────────────────────────────
import os
import re
import json
import base64
import mimetypes
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TypedDict

# ── Third-party ───────────────────────────────────────────────────────────
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langgraph.graph import StateGraph, END
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from typing import Optional, Annotated


# ── Env ───────────────────────────────────────────────────────────────────
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_PAID_KEY")

# ─────────────────────────────────────────────────────────────────────────
# GLOBAL SINGLETONS  (initialised once at startup)
# ─────────────────────────────────────────────────────────────────────────
gemini = ChatGoogleGenerativeAI(
    model="gemini-3-pro-preview",
    temperature=0,
    api_key=GEMINI_KEY,
)
embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    api_key=GEMINI_KEY,
)
qdrant = QdrantClient(url="http://localhost:6333")

# ─────────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE  (uploaded to Qdrant once on first run)
# ─────────────────────────────────────────────────────────────────────────
_KB_COLLECTION = "topology_rules"

TOPOLOGY_KB = [
    Document(page_content="Inner loops are always VOID. Outer loops are always MATERIAL."),
    Document(page_content="Edge structure: Each edge MUST have 'type' and 'dimension'. Total_edges MUST be specified."),
    Document(page_content="CHAMFER RULE: Store BOTH fields for every chamfer edge: \"leg\": <raw leg from drawing> AND \"dimension\": leg / cos(given angle) (hypotenuse = actual cut length). Examples: leg=2 → dimension=2.828 | leg=4 → dimension=5.657 | leg=3 → dimension=4.243. NEVER set dimension = raw leg value."),
    Document(page_content="CHAMFER STRAIGHT EDGE RULE: WITH KNOWN leg: dimension = nominal − leg_prev − leg_next. WHEN CHAMFER LEG IS UNKNOWN (null): treat as 0, use FULL nominal. NEVER set straight edge to null."),
    Document(page_content="Circle entities: nodes=0, edges=0. Only mention type='circle' or type='Concentric Circles'."),
    Document(page_content="For concentric circles: all outer circles are MATERIAL; only the innermost is VOID with diameter and circumference."),
    Document(page_content="CIRCUMFERENCE MANDATORY: circumference = diameter × 3.14."),
    Document(page_content="MULTIPLE IDENTICAL CIRCLES: 4X Ø2.5 → 4 separate loop entries."),
    Document(page_content="Include total_edge_length_summary per view and total_edge_dimension_missing_summary at root."),
]


def _ensure_kb():
    """Upload KB docs to Qdrant if the collection doesn't already exist."""
    existing = [c.name for c in qdrant.get_collections().collections]
    if _KB_COLLECTION in existing:
        return
    qdrant.recreate_collection(
        collection_name=_KB_COLLECTION,
        vectors_config={"size": 3072, "distance": "Cosine"},
    )
    points = [
        PointStruct(id=i, vector=embeddings.embed_query(doc.page_content),
                    payload={"text": doc.page_content})
        for i, doc in enumerate(TOPOLOGY_KB)
    ]
    qdrant.upload_points(collection_name=_KB_COLLECTION, points=points)
    print(f"✅ KB uploaded ({len(points)} docs) → {_KB_COLLECTION}")


# ─────────────────────────────────────────────────────────────────────────
# LANGGRAPH PIPELINE
# ─────────────────────────────────────────────────────────────────────────
class CADState(TypedDict):
    image_path: str
    visual_features: Optional[str]
    decision: Optional[str]
    retrieved_rules: Optional[List[str]]
    topology_output: Optional[str]


def extract_features(state: CADState):
    image_path = state["image_path"]
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    mime, _ = mimetypes.guess_type(image_path)
    data_uri = f"data:{mime or 'image/png'};base64,{b64}"
    response = gemini.invoke([{
        "role": "user",
        "content": [
            {"type": "text", "text": (
                "Analyze this CAD technical drawing CAREFULLY and extract:\n"
                "1. OUTER SHAPE — trace perimeter clockwise from top-left, list each edge.\n"
                "2. OUTER DIMENSIONS — extract exact values from visible dimension lines.\n"
                "3. FILLETS AND RADII — look for R followed by number.\n"
                "4. INNER HOLES — every circle/hole with Ø diameter.\n"
                "5. CHAMFERS — Extract ALL chamfer annotations:\n"
                "   - Record the EXACT label as written: e.g. '2×45°', '4×45°', 'C2', 'C4', '2X45', '4X45'\n"
                "   - The number before ×45° (or after C) is the LEG — record it explicitly\n"
                "   - Example: '2×45°' means leg=2, '4×45°' means leg=4\n"
                "   - If multiple corners have the same chamfer, note the count (e.g. '4× C2')\n"
                "   - Do NOT calculate the hypotenuse here — just record the raw label\n\n"
                "Use visible dimension lines; do NOT estimate or derive."
            )},
            {"type": "image_url", "image_url": data_uri},
        ],
    }])
    content = response.content
    if isinstance(content, list):
        content = " ".join(c if isinstance(c, str) else c.get("text", "") for c in content)
    elif isinstance(content, dict):
        content = content.get("text", "")
    return {"visual_features": str(content).strip()}


def decide_topology(state: CADState):
    response = gemini.invoke(
        f"Given: {state['visual_features']}\n\nShould topology rules be applied? Answer ONLY YES or NO."
    )
    text = str(response.content).strip().upper()
    return {"decision": "YES" if "YES" in text else "NO"}


def retrieve_topology_rules(state: CADState):
    vec = embeddings.embed_query(str(state["visual_features"]))
    hits = qdrant.query_points(collection_name=_KB_COLLECTION, query=vec, limit=3).points
    return {"retrieved_rules": [h.payload["text"] for h in hits]}


def generate_topology(state: CADState):
    prompt = f"""
Using the following information:
Visual Features: {state['visual_features']}
Topology Rules: {state['retrieved_rules']}

SCHEMA RULES:
- Wrap output between <<<TOPOLOGY_START>>> and <<<TOPOLOGY_END>>>
- Output ONLY JSON, no extra text.
- CHAMFER edges: store TWO fields:
    "leg": <raw leg value from drawing label e.g. 2×45°=2, 4×45°=4>
    "dimension": leg × 1.41421  (hypotenuse, the actual cut length)
  Examples: 2×45° → leg=2, dimension=2.828 | 4×45° → leg=4, dimension=5.657
  ⚠ NEVER set dimension = raw leg (dimension=2 for a 2×45° chamfer is WRONG)
- STRAIGHT edges adjacent to KNOWN chamfer: dimension = nominal − leg_prev − leg_next
- STRAIGHT edges adjacent to NULL chamfer: dimension = full nominal (treat unknown as 0)
- NEVER set a straight edge to null.
- Circles: nodes=0, edges=0; include circumference = diameter × 3.14
- total_edge_length_summary per view; total_edge_dimension_missing_summary at root.

Generate the topology JSON for the provided image.
"""
    response = gemini.invoke([{"role": "user", "content": [{"type": "text", "text": prompt}]}])
    content = response.content
    if isinstance(content, list):
        content = " ".join(c if isinstance(c, str) else c.get("text", "") for c in content)
    elif isinstance(content, dict):
        content = content.get("text", "")
    raw = str(content).strip()
    match = re.search(r"<<<TOPOLOGY_START>>>(.*?)<<<TOPOLOGY_END>>>", raw, re.DOTALL)
    return {"topology_output": match.group(1).strip() if match else raw}


def should_retrieve(state: CADState):
    return state["decision"] == "YES"


_graph = StateGraph(CADState)
_graph.add_node("vision",    extract_features)
_graph.add_node("decision",  decide_topology)
_graph.add_node("rag",       retrieve_topology_rules)
_graph.add_node("reasoning", generate_topology)
_graph.set_entry_point("vision")
_graph.add_edge("vision", "decision")
_graph.add_conditional_edges("decision", should_retrieve, {True: "rag", False: END})
_graph.add_edge("rag", "reasoning")
_graph.add_edge("reasoning", END)
pipeline_app = _graph.compile()


def run_pipeline(image_path: str) -> dict:
    """Run the full LangGraph pipeline; return parsed topology JSON dict."""
    result = pipeline_app.invoke({"image_path": image_path})
    if not result.get("topology_output"):
        fallback = {
            "image_path": image_path,
            "visual_features": result.get("visual_features", ""),
            "decision": "YES",
            "retrieved_rules": [],
            "topology_output": None,
        }
        fallback.update(retrieve_topology_rules(fallback))
        fallback.update(generate_topology(fallback))
        result = fallback

    raw = result["topology_output"]
    # Strip Markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────────────
# DATACLASSES
# ─────────────────────────────────────────────────────────────────────────
@dataclass
class GeometryAnalysis:
    total_edge_length: float = 0.0
    outer_perimeter: float = 0.0
    inner_perimeter: float = 0.0
    hole_count: int = 0
    piercing_points: int = 0
    complexity_score: float = 0.0
    estimated_area: float = 0.0
    bounding_box: Tuple[float, float] = (0.0, 0.0)
    edge_type_counts: Dict[str, int] = field(default_factory=dict)
    min_feature_size: float = 0.0
    warnings: List[str] = field(default_factory=list)
    thickness_from_side_view: Optional[float] = None


@dataclass
class CostBreakdown:
    process_name: str
    material_name: str
    quantity: int
    processing_cost: float = 0.0
    total_cost: float = 0.0
    cost_per_unit: float = 0.0
    processing_time: float = 0.0
    lead_time: str = ""
    notes: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────
# TOPOLOGY PARSER
# ─────────────────────────────────────────────────────────────────────────
class TopologyParser:
    SIDE_VIEW_KEYWORDS = ("side", "right", "left", "depth", "profile", "bottom", "top", "rear", "back")

    def __init__(self, json_data: Dict):
        self.data = json_data
        self.views = json_data.get("views", [])
        self.analysis = GeometryAnalysis()

    def parse(self) -> GeometryAnalysis:
        for view in self.views:
            view_name = view.get("view", "unknown")
            if self._is_side_view(view_name):
                self._extract_thickness(view)
            else:
                self._parse_outer_loops(view)
                self._parse_inner_loops(view)
        self.analysis.total_edge_length = self.analysis.outer_perimeter + self.analysis.inner_perimeter
        self._estimate_area()
        return self.analysis

    @classmethod
    def _is_side_view(cls, name: str) -> bool:
        return any(kw in name.lower() for kw in cls.SIDE_VIEW_KEYWORDS)

    def _extract_thickness(self, view: Dict):
        dims = []
        for loop in view.get("outer_closed_loops", []):
            for i in range(1, loop.get("edges", 0) + 1):
                ed = loop.get(f"edge_{i}")
                if ed:
                    d = ed.get("dimension")
                    if d and str(d) != "null":
                        try:
                            v = float(str(d).replace("mm", "").strip())
                            if v > 0:
                                dims.append(v)
                        except (ValueError, TypeError):
                            pass
        if dims and self.analysis.thickness_from_side_view is None:
            self.analysis.thickness_from_side_view = min(dims)

    def _edge_dim(self, edge_data: Dict) -> Optional[float]:
        d = edge_data.get("dimension")
        if d is None or str(d) == "null":
            return None
        try:
            return float(str(d).replace("mm", "").strip())
        except (ValueError, TypeError):
            return None

    def _parse_outer_loops(self, view: Dict):
        for loop in view.get("outer_closed_loops", []):
            for et, cnt in loop.get("edge_type", {}).items():
                self.analysis.edge_type_counts[et] = self.analysis.edge_type_counts.get(et, 0) + cnt
            perim = 0.0
            for i in range(1, loop.get("edges", 0) + 1):
                ed = loop.get(f"edge_{i}")
                if ed:
                    v = self._edge_dim(ed)
                    if v and v > 0:
                        # fillet/arc edges: dimension stored as radius → arc length = (π/2) × r
                        if ed.get("type", "") in ("fillet", "arc"):
                            v = (np.pi / 2) * v
                        perim += v
            self.analysis.outer_perimeter += perim

    def _parse_inner_loops(self, view: Dict):
        for loop in view.get("inner_closed_loops", []):
            ltype = loop.get("type", "")
            if ltype == "Circle":
                self.analysis.hole_count += 1
                self.analysis.piercing_points += 1
                circ = loop.get("circumference")
                if circ:
                    try:
                        self.analysis.inner_perimeter += float(str(circ).replace("mm", ""))
                    except (ValueError, TypeError):
                        pass
            elif "concentric_circle_details" in loop:
                details = loop["concentric_circle_details"]
                for i in range(1, details.get("circles", 0) + 1):
                    cd = details.get(f"circle_{i}", {})
                    if cd.get("type") == "VOID":
                        self.analysis.hole_count += 1
                        self.analysis.piercing_points += 1
                        circ = cd.get("circumference")
                        if circ:
                            try:
                                self.analysis.inner_perimeter += float(str(circ).replace("mm", ""))
                            except (ValueError, TypeError):
                                pass
            elif ltype in ("Slot", "Rectangle") or "round" in ltype.lower():
                self.analysis.hole_count += 1
                self.analysis.piercing_points += 1
                total_edges = loop.get("edges", 0)
                edge_type_counts = loop.get("edge_type", {})
                rep: Dict[str, float] = {}
                for i in range(1, total_edges + 1):
                    ed = loop.get(f"edge_{i}")
                    if not ed:
                        continue
                    kind = ed.get("type", "")
                    if kind in rep:
                        continue
                    length = None
                    if kind == "arc":
                        # semicircle arc in slot: length = π × radius
                        r = ed.get("radius")
                        if r is not None and str(r) != "null":
                            try:
                                length = np.pi * float(str(r).replace("mm", ""))
                            except (ValueError, TypeError):
                                pass
                        if length is None:
                            length = self._edge_dim(ed)
                    elif kind == "fillet":
                        # 90° corner fillet: arc length = (π/2) × radius
                        r = ed.get("radius")
                        if r is not None and str(r) != "null":
                            try:
                                length = (np.pi / 2) * float(str(r).replace("mm", ""))
                            except (ValueError, TypeError):
                                pass
                        if length is None:
                            v = self._edge_dim(ed)
                            if v:
                                length = (np.pi / 2) * v
                    else:
                        length = self._edge_dim(ed)
                    if length:
                        rep[kind] = length

                # Normalize fillet/arc keys — LLM sometimes writes
                # edge_type_counts as {"arc": N} but individual edges as
                # {"type": "fillet"} or vice-versa.  Bridge the gap.
                if "fillet" in rep and "arc" not in rep:
                    rep["arc"] = rep["fillet"]
                if "arc" in rep and "fillet" not in rep:
                    rep["fillet"] = rep["arc"]

                perim = sum(rep.get(k, 0) * c for k, c in edge_type_counts.items()) if edge_type_counts else sum(rep.values())
                self.analysis.inner_perimeter += perim

    def _estimate_area(self):
        if self.analysis.outer_perimeter > 0:
            side = self.analysis.outer_perimeter / 4
            area = side ** 2 - self.analysis.hole_count * np.pi * (2.5 ** 2)
            self.analysis.estimated_area = max(0.0, area)
            w = np.sqrt(self.analysis.estimated_area * 1.5)
            h = self.analysis.estimated_area / w if w > 0 else 0
            self.analysis.bounding_box = (w, h)


# ─────────────────────────────────────────────────────────────────────────
# MATERIAL DATABASE
# ─────────────────────────────────────────────────────────────────────────
MATERIAL_DATABASE: Dict[str, Dict] = {
    "mild_steel": {
        "name": "Mild Steel",
        "density": 7.85, "cost_per_kg": 1.20,
        "laser_compatible": True, "waterjet_compatible": True,
    },
    "stainless_steel": {
        "name": "Stainless Steel 304",
        "density": 7.93, "cost_per_kg": 4.50,
        "laser_compatible": True, "waterjet_compatible": True,
    },
    "aluminum": {
        "name": "Aluminum 6061",
        "density": 2.70, "cost_per_kg": 3.50,
        "laser_compatible": True, "waterjet_compatible": True,
    },
    "copper": {
        "name": "Copper",
        "density": 8.96, "cost_per_kg": 9.00,
        "laser_compatible": True, "waterjet_compatible": True,
    },
    "brass": {
        "name": "Brass",
        "density": 8.50, "cost_per_kg": 7.00,
        "laser_compatible": True, "waterjet_compatible": True,
    },
    "acrylic": {
        "name": "Acrylic (PMMA)",
        "density": 1.18, "cost_per_kg": 8.00,
        "laser_compatible": True, "waterjet_compatible": True,
    },
    "plywood": {
        "name": "Plywood",
        "density": 0.60, "cost_per_kg": 3.00,
        "laser_compatible": True, "waterjet_compatible": True,
    },
    "carbon_fiber": {
        "name": "Carbon Fiber Composite",
        "density": 1.60, "cost_per_kg": 50.00,
        "laser_compatible": False, "waterjet_compatible": True,
    },
}

PROCESS_RATES = {
    "laser_cutting":    {"piercing_time_per_hole": 3.0},
    "waterjet_cutting": {"piercing_time_per_hole": 5.0},
}


# ─────────────────────────────────────────────────────────────────────────
# COST CALCULATOR
# ─────────────────────────────────────────────────────────────────────────
class CostCalculator:
    def __init__(self, geometry: GeometryAnalysis, machine_params: Dict):
        self.geometry = geometry
        self.machine_params = machine_params

    def _calc(self, process_key: str, process_display: str,
              material_key: str, thickness: float, quantity: int) -> CostBreakdown:
        mat = MATERIAL_DATABASE[material_key]
        mparams = self.machine_params.get(process_key, {})
        rates   = PROCESS_RATES[process_key]

        cutting_speed = mparams.get("cutting_speed", 5.0)
        cutting_time  = (self.geometry.total_edge_length / cutting_speed) / 60
        piercing_time = (self.geometry.piercing_points * rates["piercing_time_per_hole"]) / 60
        total_time    = cutting_time + piercing_time
  
        machine_rate_hr  = mparams.get("machine_rate_per_hour", 0.0)
        processing_cost  = total_time * (machine_rate_hr / 60) * quantity
        
        b = CostBreakdown(
            process_name=process_display,
            material_name=mat["name"],
            quantity=quantity,
            processing_cost=processing_cost,
            total_cost=processing_cost,
            cost_per_unit=processing_cost / quantity if quantity else 0,
            processing_time=total_time * quantity,
        )
        if quantity <= 10:
            b.lead_time = "1-2 days"
        elif quantity <= 100:
            b.lead_time = "2-3 days"
        else:
            b.lead_time = "3-5 days"
        return b

    def calculate_laser_cutting(self, material_key: str, thickness: float, quantity: int) -> CostBreakdown:
        return self._calc("laser_cutting", "Laser Cutting", material_key, thickness, quantity)

    def calculate_waterjet_cutting(self, material_key: str, thickness: float, quantity: int) -> CostBreakdown:
        return self._calc("waterjet_cutting", "Waterjet Cutting", material_key, thickness, quantity)


# ─────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="2D CAD Cost Estimator API",
    description="Upload a 2D CAD image and get manufacturing cost estimates.",
    version="1.0.0",
)


@app.on_event("startup")
def startup():
    _ensure_kb()
    print("✅ API ready.")


@app.get("/")
def root():
    return {
        "message": "2D CAD Cost Estimator API is running",
        "docs":     "http://localhost:8000/docs",
        "health":   "http://localhost:8000/health",
        "materials":"http://localhost:8000/materials",
        "estimate": "POST http://localhost:8000/estimate",
    }

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/materials")
def list_materials():
    return [{"key": k, "name": v["name"]} for k, v in MATERIAL_DATABASE.items()]


@app.post("/estimate")
async def estimate(
    image: UploadFile = File(..., description="2D CAD image (PNG/JPG/PDF)"),
    quantity: int = Form(..., description="Production quantity"),
    user_input_thickness: int = Form(..., description="This thickness will only be used if the LLM fails to extract it or if it is not provided."),
    processes: str = Form(..., description="Comma-separated: 'Laser Cutting,Waterjet Cutting'"),
    materials: str = Form(..., description="Comma-separated material keys e.g. 'mild_steel,aluminum'"),
    laser_speed: float = Form(5.0,   description="Laser cutting speed mm/sec"),
    laser_power: float = Form(2.0,   description="Laser power kW"),
    laser_elec:  float = Form(0.12,  description="Electricity rate $/kWh"),
    laser_rate:  Optional[float] = Form(None, description="Machine rate $/hr (auto = power × elec)"),
    wj_speed:    float = Form(2.5,   description="Waterjet cutting speed mm/sec"),
    wj_power:    float = Form(50.0,  description="Waterjet power kW"),
    wj_elec:     float = Form(0.12,  description="Electricity rate $/kWh"),
    wj_rate:  Optional[float] = Form(None, description="Machine rate $/hr (auto = power × elec)"),

):
    
    # ── Validate inputs ──────────────────────────────────────────────────
    selected_processes = [p.strip() for p in processes.split(",") if p.strip()]
    selected_materials = [m.strip() for m in materials.split(",") if m.strip()]

    if not selected_processes:
        raise HTTPException(400, "No processes specified.")
    if not selected_materials:
        raise HTTPException(400, "No materials specified.")
    for mk in selected_materials:
        if mk not in MATERIAL_DATABASE:
            raise HTTPException(400, f"Unknown material key '{mk}'. Use GET /materials.")

    valid_processes = {"Laser Cutting", "Waterjet Cutting"}
    for p in selected_processes:
        if p not in valid_processes:
            raise HTTPException(400, f"Unknown process '{p}'. Valid: {sorted(valid_processes)}")

    # ── Machine params ───────────────────────────────────────────────────
    machine_params: Dict = {}
    if "Laser Cutting" in selected_processes:
        machine_params["laser_cutting"] = {
            "cutting_speed":         laser_speed,
            "machine_rate_per_hour": laser_rate if (laser_rate is not None and laser_rate > 0) else round(laser_power * laser_elec, 4),
        }
        
    if "Waterjet Cutting" in selected_processes:
        machine_params["waterjet_cutting"] = {
            "cutting_speed":         wj_speed,
            "machine_rate_per_hour": wj_rate if (wj_rate is not None and wj_rate > 0) else round(wj_power * wj_elec, 4)       
            }
        
    print(machine_params)

    # ── Save uploaded image to temp file ────────────────────────────────
    suffix = os.path.splitext(image.filename or "image.png")[1] or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await image.read())
        tmp_path = tmp.name

    try:
        # ── Run pipeline ─────────────────────────────────────────────────
        try:
            topology_json = run_pipeline(tmp_path)
        except json.JSONDecodeError as e:
            raise HTTPException(500, f"Failed to parse topology JSON from LLM: {e}")
        except Exception as e:
            raise HTTPException(500, f"Pipeline error: {e}")

        # ── Parse geometry ────────────────────────────────────────────────
        parser   = TopologyParser(topology_json)
        geometry = parser.parse()

        thickness = geometry.thickness_from_side_view
        if thickness is None or thickness <= 0:
            thickness = user_input_thickness

        # validate final thickness
        if thickness <= 0:
            raise HTTPException(status_code=400, detail="Thickness must be greater than 0.")
        
        print(thickness)
        
        # ── Calculate costs ───────────────────────────────────────────────
        calculator = CostCalculator(geometry, machine_params)
        cost_results: List[CostBreakdown] = []

        for mat_key in selected_materials:
            mat = MATERIAL_DATABASE[mat_key]
            for process in selected_processes:
                try:
                    if process == "Laser Cutting" and mat["laser_compatible"]:
                        cost_results.append(
                            calculator.calculate_laser_cutting(mat_key, thickness, quantity)
                        )
                    elif process == "Waterjet Cutting" and mat["waterjet_compatible"]:
                        cost_results.append(
                            calculator.calculate_waterjet_cutting(mat_key, thickness, quantity)
                        )
                except Exception as e:
                    cost_results.append(CostBreakdown(
                        process_name=process,
                        material_name=mat["name"],
                        quantity=quantity,
                        notes=[f"Error: {e}"],
                    ))

        # ── Build response ────────────────────────────────────────────────
        return JSONResponse({
            "geometry": {
                "outer_perimeter_mm":  round(geometry.outer_perimeter, 4),
                "inner_perimeter_mm":  round(geometry.inner_perimeter, 4),
                "total_edge_length_mm": round(geometry.total_edge_length, 4),
                "estimated_area_mm2":  round(geometry.estimated_area, 4),
                "thickness_mm":        round(thickness, 4),
                "hole_count":          geometry.hole_count,
            },
            "cost_results": [
                {
                    "process":            r.process_name,
                    "material":           r.material_name,
                    "quantity":           r.quantity,
                    "processing_cost_usd": r.processing_cost,
                    "total_cost_usd":      r.total_cost,
                    "cost_per_unit_usd":   r.cost_per_unit,
                    "processing_time_min": r.processing_time,
                    "lead_time":           r.lead_time,
                }
                for r in cost_results
            ],
        })

    finally:
        os.unlink(tmp_path)


# ─────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
