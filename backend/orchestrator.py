import os
import json
import time
import asyncio
from logger import get_logger
from vision_engine import DrPetVisionEngine
from acoustic_engine import DrPetAcousticEngine
from memory_engine import DrPetMemoryEngine
from llm_engine import DrPetLLMCoachingAgent
from pdf_export import DrPetClinicalAudit

logger = get_logger("Orchestrator")

class AnalysisOrchestrator:
    def __init__(self):
        # Initialize engines cleanly
        self.vision_engine = DrPetVisionEngine()
        self.acoustic_engine = DrPetAcousticEngine()
        self.memory_engine = DrPetMemoryEngine()
        self.llm_agent = DrPetLLMCoachingAgent()
        
        self.results_dir = "data/results"
        os.makedirs(self.results_dir, exist_ok=True)

    async def run_analysis_pipeline(self, file_path: str, file_id: str, pet_id: str = "Max"):
        """
        Orchestrates the modernized AWC-style multi-modal AI pipeline.
        Processes each detected animal individually after a global acoustic and AI sweep.
        """
        try:
            logger.info(f"Starting AWC-Style Pipeline for {file_id}")
            start_time = time.time()
            
            # --- STAGE 1 & 2: CONCURRENT MULTI-MODAL INFERENCE ---
            loop = asyncio.get_event_loop()
            
            # 1. Vision Hub (Multi-Pet detection + track initialization)
            vision_task = loop.run_in_executor(None, self.vision_engine.process_video, file_path, file_id)
            
            # 2. Acoustic Hub (Localizes vocal sentiment for the scene)
            acoustic_task = loop.run_in_executor(None, self.acoustic_engine.analyze_audio, file_path)
            
            # 3. LLM Vision (Global scene understanding / Narrative)
            ai_task = self.llm_agent.analyze_video_ai(file_path)
            
            vision_results, acoustic_results, ai_analysis = await asyncio.gather(
                vision_task, acoustic_task, ai_task
            )

            if "error" in vision_results:
                logger.error(f"Vision error in pipeline: {vision_results['error']}")
                return

            detected_pets = vision_results.get("pets", [])
            vocal_sentiment = acoustic_results.get("vocal_sentiment", "Stable")
            vocal_conf = acoustic_results.get("confidence", 0.0)

            # --- STAGE 3: INDIVIDUAL PET PROCESSING LOOP (Deterministic Fusion) ---
            pet_summaries = []
            
            # Fetch global insights
            global_ai_state = ai_analysis.get("emotional_state", "UNCERTAIN")
            global_ai_breed = ai_analysis.get("pet_type", "General Pet")
            
            for pet in detected_pets:
                pid = pet["pet_id"]
                yolo_type = pet["animal"]
                
                # --- SENSORY FUSION INPUTS ---
                v_state = pet.get("vision_state", "UNCERTAIN")
                v_vigor = pet["metrics"]["motion_vigor"]
                a_state = vocal_sentiment
                l_state = global_ai_state
                
                # --- SENSORY FUSION LOGIC (WEIGHTED CONSENSUS) ---
                # Weighting: LLM(0.4), Vision(0.3), Audio(0.3)
                final_state = "UNCERTAIN"
                
                # Rule 1: High-Confidence Dissonance Check
                # If audio is aggressive but vision/LLM is happy, we default to defensive for safety.
                if "Defensive" in a_state and ("Affiliative" in l_state or "Relaxed" in l_state):
                    final_state = "Potential DANGER / Stress Conflict"
                    logger.warning(f"FUSION DISSONANCE for {pid}: Audio reports aggression, LLM reports calm.")
                
                # Rule 2: Consensus Scoring
                score_map = {
                    "Relaxed / Equilibrium": 0,
                    "Affiliative / Playful": 0,
                    "Hyper-Aroused / Anxious": 0,
                    "Defensive / Reactive": 0,
                    "Suppressed / Pain State": 0
                }
                
                # Apply weights
                weights = {"LLM": 0.4, "Vision": 0.3, "Audio": 0.3}
                for component, state, weight in [("LLM", l_state, weights["LLM"]), ("Vision", v_state, weights["Vision"]), ("Audio", a_state, weights["Audio"])]:
                    clean_state = [k for k in score_map.keys() if k.split(" / ")[0] in state]
                    if clean_state:
                        score_map[clean_state[0]] += weight
                
                # Winner takes all
                if max(score_map.values()) > 0.35:
                    final_state = max(score_map, key=score_map.get)
                else:
                    # If no clear winner, use LLM or mark insecure
                    final_state = l_state if l_state != "UNCERTAIN" else "OBSERVE - LOW CONFIDENCE"

                # Debug Logging for Fusion
                print(f"DEBUG [FUSION]: {pid} Decision:")
                print(f"  -> Vision: {v_state}")
                print(f"  -> Audio: {a_state}")
                print(f"  -> LLM: {l_state}")
                print(f"  -> FINAL DECISION: {final_state}")

                # Enrichment via Memory & RAG
                rag_context = await asyncio.to_thread(self.memory_engine.get_rag_context, breed=global_ai_breed, behavior_state=final_state)
                
                behavior_snapshot = {
                    "pet_id": pid,
                    "animal": yolo_type,
                    "breed": global_ai_breed,
                    "metrics": {
                        "primary_behavior": final_state,
                        "confidence_score": pet["confidence"],
                        "vocal_context": vocal_sentiment,
                        "fusion_reasoning": f"Consensus score: {max(score_map.values()):.2f}",
                        "tail_wag": pet["metrics"]["tail_wag_frequency"]
                    },
                    "rag_insight": rag_context
                }

                # Generate Per-Pet Coaching Strategies
                coaching_plan = await self.llm_agent.generate_rag_report(behavior_snapshot, rag_context)
                
                pet_summaries.append({
                    "pet_data": behavior_snapshot,
                    "coaching_plan": coaching_plan
                })

            # --- STAGE 4: AGGREGATION & REPORT GENERATION ---
            primary_pet = pet_summaries[0] if pet_summaries else None
            
            final_output = {
                "file_id": file_id,
                "timestamp": time.time(),
                "scene_summary": ai_analysis.get("behavior_description", "Complete."),
                "vocal_data": acoustic_results,
                "individual_pets": pet_summaries,
                "breed_card": primary_pet["coaching_plan"].get("breed_card") if primary_pet else None,
                "total_animals_detected": len(pet_summaries),
                "data_fidelity": "Scientific (Detect-Crop-Classify)",
                "status": "completed",
                # Lift primary results to root for frontend JS compatibility
                "analysis": primary_pet["coaching_plan"]["message"] if primary_pet else "No subjects identified.",
                "recommendations": primary_pet["coaching_plan"]["care_methods"] if primary_pet else [],
                "temporal_intelligence": {"is_anomaly": False, "message": "Baseline lookup in progress.", "deviation_score": "0%"},
                "metrics": {
                    "happiness_score": ai_analysis.get("happiness_score", 65) if primary_pet else 0,
                    "tail_wag_frequency": primary_pet["pet_data"]["metrics"]["tail_wag"] if primary_pet else "0 Hz",
                    "acoustic_sentiment": vocal_sentiment,
                    "fft_peaks": acoustic_results.get("fft_peaks", [])
                },
                "ai_insights": {
                    "emotional_state": primary_pet["coaching_plan"]["state"] if primary_pet else "None",
                    "key_points": ai_analysis.get("clinical_evidence", []) if primary_pet else []
                }
            }

            # Generate consolidated Clinical Audit (PDF)
            pdf_engine = DrPetClinicalAudit()
            await asyncio.to_thread(pdf_engine.generate_pdf, file_id, final_output)
            final_output["clinical_audit_url"] = f"/download/report/{file_id}"

            # Persist results
            result_file = os.path.join(self.results_dir, f"{file_id}.json")
            with open(result_file, "w") as f:
                json.dump(final_output, f)

            logger.info(f"AWC Pipeline Completed for {file_id} with {len(pet_summaries)} subjects.")

            # Privacy cleanup
            try:
                os.remove(file_path)
            except: pass

        except Exception as e:
            logger.error(f"CRITICAL ORCHESTRATION FAILURE: {e}", exc_info=True)

