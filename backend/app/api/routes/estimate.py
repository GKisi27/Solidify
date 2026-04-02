import asyncio
import io

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional, List
import os, tempfile, json
from fastapi.responses import JSONResponse
from app.services.cost_estimator import (
    MATERIAL_DATABASE, run_pipeline, TopologyParser, CostCalculator, CostBreakdown
)
from PIL import Image
from app.services.to_db import save_history

router = APIRouter(tags=["estimate"])

@router.get("/materials")
def list_materials():
    return [{"key": k, "name": v["name"]} for k, v in MATERIAL_DATABASE.items()]

@router.post("/estimate")
async def estimate(
    image: UploadFile = File(...),
    quantity: int = Form(..., description="Production quantity"),
    user_input_thickness: float = Form(..., description="This thickness will only be used if the LLM fails to extract it or if it is not provided."),
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
    # ── Parse user input ──
    selected_processes = [p.strip() for p in processes.split(",") if p.strip()]
    selected_materials = [m.strip() for m in materials.split(",") if m.strip()]

    if not selected_processes:
        raise HTTPException(400, "No processes specified.")
    if not selected_materials:
        raise HTTPException(400, "No materials specified.")

    for mk in selected_materials:
        if mk not in MATERIAL_DATABASE:
            raise HTTPException(400, f"Unknown material key '{mk}'.")

    # ── Machine parameters ──
    machine_params = {}
    if "Laser Cutting" in selected_processes:
        machine_params["laser_cutting"] = {
            "cutting_speed": laser_speed,
            "machine_rate_per_hour": laser_rate if (laser_rate and laser_rate > 0) else round(laser_power * laser_elec, 4)
        }
    if "Waterjet Cutting" in selected_processes:
        machine_params["waterjet_cutting"] = {
            "cutting_speed": wj_speed,
            "machine_rate_per_hour": wj_rate if (wj_rate and wj_rate > 0) else round(wj_power * wj_elec, 4)
        }
    
    await image.seek(0)
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(400, "Uploaded file is empty.")
    
    suffix = os.path.splitext(image.filename or "image.png")[1] or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name


    try:
        # ── Run pipeline & parse geometry ──
        try:
            topology_json = run_pipeline(tmp_path)
        except Exception as e:
            raise HTTPException(500, f"Pipeline error: {e}")

        parser = TopologyParser(topology_json)
        geometry = parser.parse()
        thickness = geometry.thickness_from_side_view or user_input_thickness
        if thickness <= 0:
            raise HTTPException(400, "Thickness must be greater than 0.")
        
        # print(thickness)
        # print(machine_params)

        # ── Calculate costs ──
        calculator = CostCalculator(geometry, machine_params)
        cost_results: List[CostBreakdown] = []

        for mat_key in selected_materials:
            mat = MATERIAL_DATABASE[mat_key]
            for process in selected_processes:
                try:
                    if process == "Laser Cutting" and mat["laser_compatible"]:
                        cost_results.append(calculator.calculate_laser_cutting(mat_key, thickness, quantity))
                    elif process == "Waterjet Cutting" and mat["waterjet_compatible"]:
                        cost_results.append(calculator.calculate_waterjet_cutting(mat_key, thickness, quantity))
                except Exception as e:
                    cost_results.append(CostBreakdown(
                        process_name=process,
                        material_name=mat["name"],
                        quantity=quantity,
                        notes=[f"Error: {e}"],
                    ))
                    
        await asyncio.to_thread(save_history, image_bytes, image.filename, "cost_estimation", None, None)

        # ── Return response ──
        return JSONResponse({
            "geometry": {
                "outer_perimeter_mm": round(geometry.outer_perimeter, 4),
                "inner_perimeter_mm": round(geometry.inner_perimeter, 4),
                "total_edge_length_mm": round(geometry.total_edge_length, 4),
                "estimated_area_mm2": round(geometry.estimated_area, 4),
                "thickness_mm": round(thickness, 4),
                "hole_count": geometry.hole_count,
            },
            "cost_results": [
                {
                    "process": r.process_name,
                    "material": r.material_name,
                    "quantity": r.quantity,
                    "processing_cost_usd": round(r.processing_cost, 4),
                    "total_cost_usd": round(r.total_cost, 4),
                    "cost_per_unit_usd": round(r.cost_per_unit, 4),
                    "processing_time_min": r.processing_time,
                    "lead_time": r.lead_time,
                }
                for r in cost_results
            ],
        })

    finally:
        os.unlink(tmp_path)