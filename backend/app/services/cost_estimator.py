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
qdrant = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant_vector_db:6333"), timeout=60)

# ─────────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE  (uploaded to Qdrant once on first run)
# ─────────────────────────────────────────────────────────────────────────
_KB_COLLECTION = "topology_rules"

TOPOLOGY_KB = [
    # ── SYSTEM PROMPT with full JSON schema ──────────────────────────────
    Document(page_content="""
        You are a CAD topology extraction expert.
        Analyze the PROVIDED ORIGINAL CAD IMAGE (NOT recolored).
        Output STRICT JSON inside markers. No explanation.

        <<<TOPOLOGY_START>>>
        {
          "views": [
            {
              "view": "front",
              "outer_closed_loops": [
                {
                  "loop_id": 1,
                  "region": "MATERIAL",
                  "nodes": 4,
                  "edges": 4,
                  "edge_type": { "straight": 4, "chamfer": 0, "arc": 0 },
                  "edge_1": { "type": "straight", "dimension": "..." },
                  "edge_2": { "type": "chamfer",  "leg": "...", "dimension": "leg × 1.41421" }
                }
              ],
              "inner_closed_loops": [
                {
                  "loop_id": 2, "nodes": 0, "edges": 0,
                  "type": "Concentric Circles",
                  "concentric_circle_details": {
                    "circles": 3,
                    "circle_1": { "type": "MATERIAL" },
                    "circle_2": { "type": "MATERIAL" },
                    "circle_3": { "type": "VOID", "x": "...", "y": "...", "diameter": "...", "circumference": "..." }
                  }
                },
                {
                  "loop_id": 3, "region": "VOID", "nodes": 0, "edges": 0,
                  "type": "Circle", "x": "...", "y": "...", "diameter": "...", "circumference": "..."
                },
                {
                  "loop_id": 4, "region": "VOID", "nodes": 4, "edges": 4,
                  "type": "Slot", "x": "...", "y": "...",
                  "edge_type": { "straight": 2, "arc": 2 },
                  "edge_1": { "type": "straight", "dimension": "..." },
                  "edge_2": { "type": "arc", "radius": "..." }
                },
                {
                  "loop_id": 5, "region": "VOID", "nodes": 4, "edges": 4,
                  "type": "Rectangle",
                  "edge_1": { "type": "straight", "dimension": "..." }
                }
              ],
              "total_edge_length_summary": {
                "outer_loop_perimeter": "value_mm",
                "inner_loops_total": "value_mm",
                "grand_total": "value_mm"
              }
            },
            {
              "view": "top",
              "outer_closed_loops": [], "inner_closed_loops": [],
              "total_edge_length_summary": { "outer_loop_perimeter": "value_mm", "inner_loops_total": "value_mm", "grand_total": "value_mm" }
            },
            {
              "view": "right",
              "outer_closed_loops": [], "inner_closed_loops": [],
              "total_edge_length_summary": { "outer_loop_perimeter": "value_mm", "inner_loops_total": "value_mm", "grand_total": "value_mm" }
            }
          ],
          "total_edge_dimension_missing_summary": {
            "straight": { "number": 0 }, "chamfer": { "number": 4 },
            "arc": { "number": 0 }, "fillet": { "number": 0 }, "curved": { "number": 0 }
          }
        }
        <<<TOPOLOGY_END>>>
    """),

    # ── FUNDAMENTAL RULES ────────────────────────────────────────────────
    Document(page_content="Inner loops are always VOID. Outer loops are always MATERIAL."),
    Document(page_content="Edge structure: Each edge MUST have 'type' and 'dimension'. Total_edges MUST be specified."),
    Document(page_content="Edge type counts must sum to total_edges. Format: {straight: X, curved: Y, fillet: Z, chamfer: W}"),

    # ── MULTI-VIEW RULES ─────────────────────────────────────────────────
    Document(page_content="MULTI-VIEW: If the CAD image contains multiple views (front, top, right, isometric, section), extract each view separately as its own entry in the 'views' array."),
    Document(page_content="MULTI-VIEW IDENTIFICATION: Common view labels are 'FRONT', 'TOP', 'RIGHT', 'LEFT', 'BOTTOM', 'ISO', 'SECTION A-A'. Detect and label them appropriately."),
    Document(page_content="MULTI-VIEW LOOPS: Each view independently has its own outer_closed_loops and inner_closed_loops. Do not mix features across views."),
    Document(page_content="If only ONE view is present, the views array has a single entry. Do not create empty placeholder views."),

    # ── CONCENTRIC CIRCLES ───────────────────────────────────────────────
    Document(page_content="For inner loop, if a circle is present inside of another circle, count them as ONE entry with type='Concentric Circles'. Outer circles are MATERIAL; only the innermost circle is VOID. Only provide dimensions for the innermost (VOID) circle."),
    Document(page_content="Concentric circles schema: use 'concentric_circle_details' with keys circles (count), circle_1, circle_2, ..., circle_N. All circles except the last are MATERIAL. The last/innermost is VOID with diameter and circumference."),
    Document(page_content="Circle entities: nodes=0, edges=0. Only mention type='circle' or type='Concentric Circles'."),

    # ── CHAMFER RULES ────────────────────────────────────────────────────
    Document(page_content='CHAMFER RULE: The drawing label (C4, 4×45°, 2×45°, or plain \'4\') gives the LEG. Store BOTH fields: "leg": <raw leg value> AND "dimension": leg × 1.41421 (hypotenuse = actual cut length). Examples: leg=4 → dimension=5.657 | leg=2 → dimension=2.828 | leg=3 → dimension=4.243 | leg=1 → dimension=1.414. NEVER store the raw leg value as dimension alone.'),
    Document(page_content="CHAMFER STRAIGHT EDGE RULE: When a straight edge is adjacent to chamfer(s) WITH KNOWN leg: dimension = nominal − chamfer_leg_prev − chamfer_leg_next. WHEN CHAMFER LEG IS UNKNOWN (null): treat the unknown leg as 0 and use the FULL nominal length. NEVER set a straight edge to null just because a neighbouring chamfer is null."),
    Document(page_content="CHAMFER RULE: Set dimension to null ONLY if the chamfer has absolutely NO label, value, or dimension line of any kind visible in the drawing."),
    Document(page_content="Chamfers are SEPARATE from straight edges in edge_type_counts."),

    # ── STRAIGHT EDGE RULES ──────────────────────────────────────────────
    Document(page_content="STRAIGHT EDGE DIMENSION: For straight edges with NO adjacent chamfers, use the FULL width or height. For straight edges adjacent to chamfer(s) with known leg, subtract each adjacent chamfer leg from the nominal. If adjacent chamfer leg is unknown (null), use the full nominal."),
    Document(page_content="PRIORITY 1: Extract explicit dimensions from visible dimension lines FIRST."),
    Document(page_content="PRIORITY 2: Calculate from overall dimensions if individual edge labels are absent."),
    Document(page_content="PRIORITY 3: Use null (JSON null, not a string) ONLY for genuinely unmeasurable values such as unlabeled chamfers or fillets."),
    Document(page_content="NEVER use 'variable', 'unknown', or 'N/A' for dimensions. Calculate, estimate from proportions, or use null."),

    # ── CIRCLE / DIAMETER ────────────────────────────────────────────────
    Document(page_content="Circle Diameter: If shown as '4-N8', that means 4 circles each with diameter 8."),
    Document(page_content="CIRCUMFERENCE MANDATORY: For every circle, calculate circumference = diameter × 3.14 (π = 3.14). Examples: Ø8 → 25.12, Ø10 → 31.40, Ø3.18 → 9.99."),
    Document(page_content="MULTIPLE IDENTICAL CIRCLES: If drawing shows 4X Ø2.5, create 4 separate loop entries, each with its own loop_id."),

    # ── PERIMETER & LENGTH ───────────────────────────────────────────────
    Document(page_content="Rectangle/polygon perimeter: sum all edge lengths (skip null edges)."),
    Document(page_content="Fillet arc length (90°): ≈ (π/2) × radius. Example: R1.5mm → 2.36mm."),
    Document(page_content="Slot perimeter: straight sections + curved ends. R5.0mm semicircle arc = π × radius = 15.71mm."),
    Document(page_content="Include total_edge_length_summary at end of each view with outer_loop_perimeter, inner_loops_total, and grand_total."),
    Document(page_content="FINAL TOTAL: final_length = outer_loop_perimeter + sum_of_all_inner_loop_circumferences/perimeters."),

    # ── POSITION & COORDINATES ───────────────────────────────────────────
    Document(page_content="Origin (0,0) is bottom-left corner of outer loop. X-axis→right, Y-axis→up."),
    Document(page_content="Feature positions refer to CENTER POINT (x, y). Extract from dimension lines."),
    Document(page_content="Position calculation: x = total_width - dimension_from_right. y = total_height - dimension_from_top."),

    # ── MISSING SUMMARY ──────────────────────────────────────────────────
    Document(page_content="total_edge_dimension_missing_summary: Count the total number of each edge type (across ALL views) where dimension is null."),

    # ── QUALITY ──────────────────────────────────────────────────────────
    Document(page_content="DATA QUALITY: Set data_quality to ACCURATE if all dimensions clearly visible. Set to PARTIAL if some dimensions missing or estimated."),
]


def _ensure_kb():
    """Upload KB docs to Qdrant only if collection doesn't exist."""
    existing = [c.name for c in qdrant.get_collections().collections]
    if _KB_COLLECTION in existing:
        print(f"✅ KB already exists → {_KB_COLLECTION}")
        return
    
    qdrant.create_collection(
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
    response = gemini.invoke([
        {
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    "Analyze this CAD technical drawing CAREFULLY and extract:\n\n"
                    "1. OUTER SHAPE - Trace the perimeter clockwise starting from top-left\n"
                    "   Identify each edge segment sequentially\n\n"
                    "2. OUTER DIMENSIONS - Extract dimensions for EACH edge in sequence:\n"
                    "   - PREFER dimension lines visible in drawing over calculations\n"
                    "   - Look for ALL dimension arrows and numbers along the perimeter\n"
                    "   - Record dimensions in order: edge1, edge2, edge3, etc. going around\n"
                    "   - Examples: 55.6, 27.8, 13.7, 8.5, 15.6, 36.9, 5.7, etc.\n\n"
                    "3. FILLETS AND RADII:\n"
                    "   - Look for 'R' followed by number (e.g., R1.5, R2.4, R5.0)\n"
                    "   - If marked as '4X R1.5', this means 4 fillets each with radius 1.5\n"
                    "   - Extract the EXACT radius value from the drawing\n\n"
                    "4. INNER HOLES - For EVERY circle/hole visible:\n"
                    "   - Extract EVERY diameter marked with Ø symbol\n"
                    "   - Include quantity if multiple circles are identical\n\n"
                    "5. CHAMFERS - Extract if dimensioned\n\n"
                    "CRITICAL: \n"
                    "- Use visible dimension lines from drawing, NOT subtraction/calculation\n"
                    "- If a dimension is labeled on the drawing, extract that EXACT value\n"
                    "- Do NOT estimate or derive from other dimensions\n"
                    "- Format: List all edge dimensions in sequence around the perimeter"
                )},
                {"type": "image_url", "image_url": data_uri}
            ],
        }
    ])
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
    """
    Generates topology JSON following the new multi-view schema.
    Concentric circles, chamfer dimension = hypotenuse (leg × √2),
    straight edge dimension = nominal − adjacent chamfer legs (or full nominal if chamfer leg unknown).
    """
    prompt = f"""
Using the following information:

Visual Features (shapes, dimensions, circles from all views):
{state['visual_features']}

Topology Rules (from knowledge base):
{state['retrieved_rules']}

═══════════════════════════════════════════════════════
SCHEMA RULES — FOLLOW EXACTLY
═══════════════════════════════════════════════════════

1. OUTPUT FORMAT
   - Wrap output between <<<TOPOLOGY_START>>> and <<<TOPOLOGY_END>>>
   - Output ONLY the JSON, no extra text

2. MULTI-VIEW DETECTION
   - Detect all views present in the image (front, top, right, isometric, section, etc.)
   - Create one entry per view in the "views" array
   - If only one view exists, the array has one entry only

3. OUTER CLOSED LOOPS (region = MATERIAL)

   CHAMFER EDGES (45° chamfers):
   - The drawing label (C4, 4×45°, or plain "4") gives the LEG of the chamfer triangle
   - dimension in JSON = leg × √2 = leg × 1.41421  (actual cut length = hypotenuse)
     Examples: leg=4 → dimension=5.657  |  leg=2 → dimension=2.828  |  leg=3 → dimension=4.243
   - Set dimension to null ONLY if there is absolutely NO label for that chamfer

   STRAIGHT EDGES:
   - Adjacent chamfer has KNOWN leg → dimension = nominal − chamfer_leg_prev − chamfer_leg_next
     Example: nominal=60mm, chamfer leg=4 on both ends → dimension = 60 − 4 − 4 = 52
   - Adjacent chamfer has UNKNOWN leg (null) → treat unknown leg as 0, use FULL nominal
     Example: nominal=70mm, adjacent chamfer is null → dimension = 70.0
   - No adjacent chamfer → dimension = full nominal length
   - :warning: NEVER set a straight edge to null just because a neighbouring chamfer is null

   FILLET EDGES:
   - dimension = radius value from drawing (e.g. R1.5 → 1.5). null if unlabeled

   - Count straight and chamfer SEPARATELY in edge_type object

4. INNER CLOSED LOOPS (region = VOID)
   a) CONCENTRIC CIRCLES:
      - If 2 or more circles share the same center → type = "Concentric Circles"
      - All outer circles → type: "MATERIAL" (no dimension needed)
      - Innermost circle → type: "VOID" with x, y, diameter, circumference
      - circumference = diameter × 3.14
   b) SIMPLE CIRCLE → type = "Circle", nodes=0, edges=0, x, y, diameter, circumference
   c) SLOT → type = "Slot", edge_type with straight+arc counts
   d) RECTANGLE → type = "Rectangle", list each edge

5. EDGE DIMENSION RULES
   - Use exact values from visible dimension lines (preferred)
   - Calculate from overall dimensions if individual labels absent
   - null ONLY when genuinely unmeasurable (unlabeled chamfers/fillets)
   - NEVER use "N/A", "unknown", or "variable"

6. TOTAL EDGE LENGTH SUMMARY (per view)
   - outer_loop_perimeter: sum of all edge 'dimension' values as stored in JSON (skip nulls)
   - inner_loops_total: sum of circumferences / perimeters of all inner loops
   - grand_total: outer + inner

7. TOTAL EDGE DIMENSION MISSING SUMMARY (root level, across all views)
   - Count how many edges of each type have null dimension
   - Format: {{ "straight": {{"number": 0}}, "chamfer": {{"number": 4}}, "arc": {{"number": 0}}, "fillet": {{"number": 0}}, "curved": {{"number": 0}} }}

═══════════════════════════════════════════════════════
CHAMFER CALCULATION EXAMPLES:

  CASE A — Chamfer leg IS labeled (e.g. 4×45°, C4, or plain '4'):
  Drawing: 100×60mm rectangle, 4mm chamfers all corners
  ✗ WRONG:  straight=100, straight=60, chamfer=4
  ✓ CORRECT (8 edges clockwise):
    edge_1: straight, dimension = 100 − 4 − 4 = 92
    edge_2: chamfer,  dimension = 4 × 1.41421 = 5.657
    edge_3: straight, dimension = 60 − 4 − 4 = 52
    edge_4: chamfer,  dimension = 5.657
    edge_5: straight, dimension = 92
    edge_6: chamfer,  dimension = 5.657
    edge_7: straight, dimension = 52
    edge_8: chamfer,  dimension = 5.657

  CASE B — Chamfer has NO label (unknown leg):
  Drawing: 70×50mm rectangle, chamfers present but no dimension shown
  ✗ WRONG:  straight=null, chamfer=null  ← NEVER null a straight edge
  ✓ CORRECT (unknown leg treated as 0 → use full nominal):
    edge_1: straight, dimension = 70.0
    edge_2: chamfer,  dimension = null
    edge_3: straight, dimension = 50.0
    edge_4: chamfer,  dimension = null
    edge_5: straight, dimension = 70.0
    edge_6: chamfer,  dimension = null
    edge_7: straight, dimension = 50.0
    edge_8: chamfer,  dimension = null
═══════════════════════════════════════════════════════
Now generate the topology JSON for the provided image.
═══════════════════════════════════════════════════════
"""

    response = gemini.invoke([
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
            ],
        }
    ])

    content = response.content
    if isinstance(content, list):
        content = " ".join([c if isinstance(c, str) else c.get("text", "") for c in content])
    elif isinstance(content, dict):
        content = content.get("text", "")

    raw = str(content).strip()

    # Extract JSON between markers
    import re
    match = re.search(r"<<<TOPOLOGY_START>>>(.*?)<<<TOPOLOGY_END>>>", raw, re.DOTALL)
    if match:
        topology_json = match.group(1).strip()
    else:
        topology_json = raw

    return {"topology_output": topology_json}


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
            if not isinstance(view, dict):
                continue
            view_name = view.get("view", "unknown")
            if self._is_side_view(view_name):
                self._extract_thickness(view)
            else:
                self._parse_outer_loops(view)
                self._parse_inner_loops(view)
        self.analysis.total_edge_length = self.analysis.outer_perimeter + self.analysis.inner_perimeter
        self._calculate_complexity()
        self._estimate_area()
        self._validate()
        return self.analysis

    @classmethod
    def _is_side_view(cls, name: str) -> bool:
        return any(kw in name.lower() for kw in cls.SIDE_VIEW_KEYWORDS)

    def _calculate_complexity(self):
        score = 0.0
        weights = {"straight": 1.0, "fillet": 1.5, "chamfer": 1.5, "curved": 2.0, "arc": 2.0, "circle": 1.2}
        for et, cnt in self.analysis.edge_type_counts.items():
            score += cnt * weights.get(et, 1.0)
        score += self.analysis.hole_count * 1.2
        if self.analysis.min_feature_size > 0 and self.analysis.min_feature_size < 2.0:
            score += 5.0
        self.analysis.complexity_score = score

    def _validate(self):
        missing = self.data.get("total_edge_dimension_missing_summary", {})
        if not isinstance(missing, dict):
            return
        for edge_type, data in missing.items():
            if isinstance(data, dict):
                count = data.get("number", 0)
                if count > 0:
                    self.analysis.warnings.append(f"{count} {edge_type} edge(s) have missing dimensions")
        if self.analysis.hole_count > 20:
            self.analysis.warnings.append(f"High number of holes ({self.analysis.hole_count})")

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

            # ---- Single circle ----
            if ltype == "Circle":
                self.analysis.hole_count += 1
                self.analysis.piercing_points += 1
                circ = loop.get("circumference")
                if circ:
                    try:
                        self.analysis.inner_perimeter += float(str(circ).replace("mm", ""))
                    except (ValueError, TypeError):
                        pass
                diameter = loop.get("diameter")
                if diameter:
                    try:
                        d = float(str(diameter).replace("mm", ""))
                        if self.analysis.min_feature_size == 0 or d < self.analysis.min_feature_size:
                            self.analysis.min_feature_size = d
                    except (ValueError, TypeError):
                        pass

            # ---- Concentric circles ----
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
                        diameter = cd.get("diameter")
                        if diameter:
                            try:
                                d = float(str(diameter).replace("mm", ""))
                                if self.analysis.min_feature_size == 0 or d < self.analysis.min_feature_size:
                                    self.analysis.min_feature_size = d
                            except (ValueError, TypeError):
                                pass

            # ---- Slot / Rectangle / Round slot ----
            elif ltype in ("Slot", "Rectangle") or "round" in ltype.lower():
                self.analysis.hole_count += 1
                self.analysis.piercing_points += 1

                total_edges      = loop.get("edges", 0)
                edge_type_counts = loop.get("edge_type", {})

                def _edge_length(ed: Dict) -> Optional[float]:
                    """Return the true arc/straight length for one edge dict."""
                    kind = ed.get("type", "")
                    if kind == "arc":
                        # Semicircle arc in slot: length = π × radius
                        r = ed.get("radius")
                        if r is not None and str(r) != "null":
                            try:
                                return np.pi * float(str(r).replace("mm", ""))
                            except (ValueError, TypeError):
                                pass
                        return self._edge_dim(ed)

                    elif kind == "fillet":
                        # 90° corner fillet: arc length = (π/2) × radius
                        r = ed.get("radius")
                        if r is not None and str(r) != "null":
                            try:
                                return (np.pi / 2) * float(str(r).replace("mm", ""))
                            except (ValueError, TypeError):
                                pass
                        v = self._edge_dim(ed)
                        return (np.pi / 2) * v if v else None

                    elif kind == "straight":
                        dim = ed.get("dimension")
                        if dim is not None and str(dim) != "null":
                            try:
                                return float(str(dim).replace("mm", ""))
                            except (ValueError, TypeError):
                                pass
                        return self._edge_dim(ed)

                    else:
                        return self._edge_dim(ed)

                perim = 0.0
                for i in range(1, total_edges + 1):
                    ed = loop.get(f"edge_{i}")
                    if not ed:
                        continue
                    length = _edge_length(ed)
                    if length:
                        perim += length

                self.analysis.inner_perimeter += perim
            
    def _estimate_area(self):
        if self.analysis.outer_perimeter > 0:
            estimated_side = self.analysis.outer_perimeter / 4
            self.analysis.estimated_area = estimated_side ** 2
            avg_hole_area = np.pi * (2.5 ** 2)
            self.analysis.estimated_area = max(0.0, self.analysis.estimated_area - self.analysis.hole_count * avg_hole_area)
            w = np.sqrt(self.analysis.estimated_area * 1.5)
            h = self.analysis.estimated_area / w if w > 0 else 0
            self.analysis.bounding_box = (w, h)


# ─────────────────────────────────────────────────────────────────────────
# MATERIAL DATABASE
# ─────────────────────────────────────────────────────────────────────────
MATERIAL_DATABASE: Dict[str, Dict] = {
    "mild_steel": {
        "name": "Mild Steel",
        "density": 7.85,
        "cost_per_kg": 2.50,
        "laser_compatible": True,
        "waterjet_compatible": True,
        "laser_speed_factor": 1.0,
        "typical_thickness": [1, 2, 3, 5, 10],
    },
    "stainless_steel": {
        "name": "Stainless Steel 304",
        "density": 8.0,
        "cost_per_kg": 4.50,
        "laser_compatible": True,
        "waterjet_compatible": True,
        "laser_speed_factor": 0.7,
        "typical_thickness": [1, 2, 3, 5, 10],
    },
    "aluminum": {
        "name": "Aluminum 6061",
        "density": 2.70,
        "cost_per_kg": 5.00,
        "laser_compatible": True,
        "waterjet_compatible": True,
        "laser_speed_factor": 1.2,
        "typical_thickness": [1, 2, 3, 5, 10, 15],
    },
    "acrylic": {
        "name": "Acrylic (PMMA)",
        "density": 1.18,
        "cost_per_kg": 8.00,
        "laser_compatible": True,
        "waterjet_compatible": True,
        "laser_speed_factor": 2.5,
        "typical_thickness": [3, 5, 8, 10],
    },
    "plywood": {
        "name": "Plywood",
        "density": 0.60,
        "cost_per_kg": 3.00,
        "laser_compatible": True,
        "waterjet_compatible": True,
        "laser_speed_factor": 1.8,
        "typical_thickness": [3, 6, 9, 12, 18],
    },
    "carbon_fiber": {
        "name": "Carbon Fiber Composite",
        "density": 1.60,
        "cost_per_kg": 50.00,
        "laser_compatible": False,
        "waterjet_compatible": True,
        "laser_speed_factor": None,
        "typical_thickness": [1, 2, 3, 5],
    },
}

PROCESS_RATES = {
    "laser_cutting": {
        "setup_cost": 30.0,
        "piercing_time_per_hole": 3.0,
        "min_feature_size": 0.1,
        "max_thickness": 25,
    },
    "waterjet_cutting": {
        "setup_cost": 40.0,
        "piercing_time_per_hole": 5.0,
        "min_feature_size": 0.3,
        "max_thickness": 150,
    },
}


# ─────────────────────────────────────────────────────────────────────────
# COST CALCULATOR
# ─────────────────────────────────────────────────────────────────────────
class CostCalculator:
    def __init__(self, geometry: GeometryAnalysis, machine_params: Dict):
        self.geometry       = geometry
        self.machine_params = machine_params

    def _calc(self, process_key: str, process_display: str,
              material_key: str, thickness: float, quantity: int) -> CostBreakdown:
        mat     = MATERIAL_DATABASE[material_key]
        mparams = self.machine_params.get(process_key, {})
        rates   = PROCESS_RATES[process_key]

        default_speed = 5.0 if process_key == "laser_cutting" else 2.5
        cutting_speed = mparams.get("cutting_speed", default_speed)   # mm/sec

        # Convert: (mm) / (mm/sec) = sec → /60 = min
        cutting_time  = (self.geometry.total_edge_length / cutting_speed) / 60
        piercing_time = (self.geometry.piercing_points * rates["piercing_time_per_hole"]) / 60
        total_time_per_unit = cutting_time + piercing_time

        machine_rate_per_hour = mparams.get("machine_rate_per_hour", 0.0)
        machine_rate_per_min  = machine_rate_per_hour / 60
        processing_cost = total_time_per_unit * machine_rate_per_min * quantity

        print(f"\nDEBUG _calc({process_key}):")
        print(f"  total_edge_length    = {self.geometry.total_edge_length}")
        print(f"  cutting_speed        = {cutting_speed}")
        print(f"  cutting_time (min)   = {cutting_time}")
        print(f"  piercing_points      = {self.geometry.piercing_points}")
        print(f"  piercing_time (min)  = {piercing_time}")
        print(f"  total_time_per_unit  = {total_time_per_unit}")
        print(f"  machine_rate_per_hour= {machine_rate_per_hour}")
        print(f"  machine_rate_per_min = {machine_rate_per_min}")
        print(f"  quantity             = {quantity}")
        print(f"  processing_cost      = {processing_cost}")

        # total_cost = processing_cost only (no material cost)
        b = CostBreakdown(
            process_name=process_display,
            material_name=mat["name"],
            quantity=quantity,
            processing_cost=processing_cost,
            total_cost=processing_cost,
            cost_per_unit=processing_cost / quantity if quantity else 0.0,
            processing_time=total_time_per_unit * quantity,
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

