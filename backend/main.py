import asyncio
import uvicorn
import shutil
import os
import uuid
import json
import time
import base64
import cv2
import numpy as np

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Any

# Import the new Orchestrator
from orchestrator import AnalysisOrchestrator
from logger import get_logger

logger = get_logger("DrPetAPI")

app = FastAPI(title="Dr. PET - Behavior Intelligence System")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://frontend-coemxo2q4-aadiljm2007-8313s-projects.vercel.app",
        "https://frontend-cts.vercel.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the async orchestrator pipeline
orchestrator = AnalysisOrchestrator()

# Ensure directories exist
UPLOAD_DIR = "data/uploads"
RESULTS_DIR = "data/results"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


# --- Session Memory ---
# Tracks live markers per WebSocket session
live_sessions: Dict[str, Dict] = {}

class LiveSynthesisRequest(BaseModel):
    session_id: str

@app.get("/api/health")
async def root():
    return {"message": "Dr. PET Multi-Modal API", "status": "healthy"}


@app.post("/analyze/video")
async def analyze_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Kicks off the asynchronous multi-modal pipeline in the background.
    """
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    
    # Save the uploaded file for processing
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    logger.info(f"Accepted upload {file.filename} -> assigned ID {file_id}")
    
    # Trigger the optimized, non-blocking pipeline
    background_tasks.add_task(orchestrator.run_analysis_pipeline, file_path, file_id)
    
    return {"status": "processing", "file_id": file_id, "message": "Analysis pipeline triggered asynchronously."}


@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket, node_id: str = "anonymous"):
    """
    Live Analysis Stream with Persistent Session State.
    """
    await websocket.accept()
    session_id = node_id # Use the stable ID from the client
    
    # 0. Send Immediate Confirmation
    await websocket.send_json({"status": "connected", "message": "Neural Link Handshake Successful"})
    
    # Only initialize if this is a fresh node or session was previously cleared
    if session_id not in live_sessions or not live_sessions[session_id].get("markers"):
        live_sessions[session_id] = {
            "markers": [],
            "last_snapshot": 0,
            "last_detection_time": 0,
            "last_known_type": "pet",
            "pet_breed": "Unknown",
            "primary_state": "Searching",
            "marker_threshold": 8
        }
    
    try:
        while True:
            # High-speed binary blob reception (from canvas.toBlob)
            data = await websocket.receive_bytes()
            frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            
            if frame is not None:
                # 1. High-Speed Movement Tracking
                live_update = orchestrator.vision_engine.process_frame(frame)
                current_time = time.time()
                session = live_sessions.get(session_id)
                if not session: continue

                # Resilience Layer: Keep detection state if lost for < 3s
                if live_update.get("pet_detected"):
                    session["last_detection_time"] = current_time
                    session["last_known_type"] = live_update["type"]
                elif current_time - session.get("last_detection_time", 0) < 3.0:
                    live_update["pet_detected"] = True
                    live_update["type"] = session.get("last_known_type", "pet")
                    live_update["status"] = "PERSISTED-TRACKING"

                # 2. Snapshot Intelligence (Keywords)
                deep_insight = None
                if live_update.get("pet_detected") and (current_time - session["last_snapshot"] > 5):
                    session["last_snapshot"] = current_time
                    try:
                        # Extract ROI (Crop to pet)
                        snapshot_img = frame
                        bbox = live_update.get("bbox")
                        if bbox:
                            x1, y1, x2, y2 = bbox
                            h, w = frame.shape[:2]
                            # Add 20% padding
                            px, py = int((x2-x1)*0.2), int((y2-y1)*0.2)
                            nx1, ny1 = max(0, x1-px), max(0, y1-py)
                            nx2, ny2 = min(w, x2+px), min(h, y2+py)
                            
                            # Safety check: ensure crop is valid and large enough
                            if nx2 - nx1 > 50 and ny2 - ny1 > 50:
                                snapshot_img = frame[ny1:ny2, nx1:nx2]
                            else:
                                snapshot_img = frame # Fallback to full frame
                        
                        snapshot = await orchestrator.llm_agent.analyze_single_frame(snapshot_img)
                        
                        # Filter out internal engine fallbacks
                        clean_markers = [m for m in snapshot.get("markers", []) if "Technical Pulse" not in m]
                        session["markers"].extend(clean_markers)
                        
                        session["pet_breed"] = snapshot.get("breed", session["pet_breed"])
                        session["primary_state"] = snapshot.get("state", "Active")
                        
                        deep_insight = {
                            "markers": clean_markers,
                            "is_ready": len(session["markers"]) >= session["marker_threshold"]
                        }
                    except Exception as e:
                        logger.error(f"Snapshot Error: {e}")

                # Maintain state
                live_update["behavior"] = session["primary_state"]

                payload = {
                    "status": "active", 
                    "session_id": session_id,
                    "live_metrics": live_update, 
                    "heartbeat": deep_insight
                }
                await websocket.send_json(payload)
                
    except WebSocketDisconnect:
        logger.info(f"Session {session_id} disconnected.")
    except Exception as e:
        logger.error(f"WS Error: {e}")

@app.post("/api/live/synthesis")
async def perform_synthesis(request: LiveSynthesisRequest):
    """
    Final Synthesis of an observation session.
    """
    session = live_sessions.get(request.session_id)
    if not session or not session["markers"]:
        logger.warning(f"SYNTHESIS: No data for session {request.session_id}")
        raise HTTPException(status_code=404, detail="No session data found. The live feed must detect a pet first.")
    
    try:
        marker_count = len(session["markers"])
        logger.info(f"SYNTHESIS: Triggered for {session['pet_breed']} with {marker_count} markers.")
        
        # This will now use the parallel optimized synthesize method
        report = await orchestrator.llm_agent.generate_live_synthesis(
            animal_data={"breed": session["pet_breed"], "state": session["primary_state"]},
            markers=list(set(session["markers"])) # Unique markers
        )
        
        # --- Professional PDF Generation ---
        # Ensure the live synthesis juga gets a downloadable clinical audit
        try:
            from pdf_export import DrPetClinicalAudit
            pdf_engine = DrPetClinicalAudit()
            pdf_payload = {
                "timestamp": time.time(),
                "metrics": report.get("metrics", {}),
                "ai_insights": report.get("ai_insights", {}),
                "coaching_plan": {
                    "message": report.get("analysis", ""), 
                    "care_methods": report.get("recommendations", [])
                },
                "data_fidelity": "Live Session Intelligence"
            }
            await asyncio.to_thread(pdf_engine.generate_pdf, request.session_id, pdf_payload)
            report["clinical_audit_url"] = f"/download/report/{request.session_id}"
        except Exception as pdf_e:
            logger.error(f"SYNTHESIS: PDF Generation failed: {pdf_e}")

        logger.info(f"SYNTHESIS: Completed successfully for session {request.session_id}")
        # Cleanup
        if request.session_id in live_sessions:
            del live_sessions[request.session_id]
        return report
    except Exception as e:
        logger.error(f"SYNTHESIS: Fatal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/results/{file_id}")
async def get_results(file_id: str):
    result_path = os.path.join(RESULTS_DIR, f"{file_id}.json")
    if os.path.exists(result_path):
        with open(result_path, "r") as f:
            return json.load(f)
    return {"status": "processing", "message": "Pipeline in progress..."}


@app.get("/download/report/{file_id}")
async def download_report(file_id: str):
    """Download Clinical PDF Audit"""
    pdf_path = os.path.join(RESULTS_DIR, f"DR_PET_Audit_{file_id}.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, filename=f"DrPet_Audit_{file_id}.pdf")
    return {"error": "Report not found."}


@app.post("/feedback")
async def store_feedback(feedback: dict):
    logger.info(f"USER FEEDBACK RECORDED: {feedback}")
    return {"status": "success"}

# Serve Frontend
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    logger.warning(f"Frontend directory not found at {frontend_dir}")


if __name__ == "__main__":
    logger.info("Booting upgraded Dr. PET async backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
