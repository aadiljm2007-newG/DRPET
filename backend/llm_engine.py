import os
import json
import asyncio
import traceback
from google import genai
from google.genai import types
from groq import AsyncGroq
from typing import Dict, List, Any
import cv2
import io
from PIL import Image
from logger import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger("LLMEngine")

# Import the new Professional Prompt Library
try:
    from prompts import (
        VIDEO_ANALYSIS_PROMPT, 
        LIVE_FRAME_PROMPT, 
        BREED_PROFILE_PROMPT, 
        LIVE_SYNTHESIS_PROMPT
    )
except ImportError:
    # If used without backend package structure (like in some debug scripts)
    from backend.prompts import (
        VIDEO_ANALYSIS_PROMPT, 
        LIVE_FRAME_PROMPT, 
        BREED_PROFILE_PROMPT, 
        LIVE_SYNTHESIS_PROMPT
    )

class DrPetLLMCoachingAgent:
    def __init__(self):
        # 1. Configure API Keys Securely
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_gen_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
        self.breed_cache = {} # Simple in-memory cache for speed
        
        # 2. Configure Gemini (Model 1: Native Video Analysis)
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
            self.gemini_model = "gemini-2.5-flash"
        else:
            self.gemini_client = None
            logger.warning("Gemini API key missing. Video analysis fallback will be used.")

        # 3. Configure Groq (Model 2: Fast RAG Report Generation)
        if self.groq_gen_key:
            self.groq_client = AsyncGroq(api_key=self.groq_gen_key)
            self.groq_model = "llama-3.3-70b-versatile"
        else:
            self.groq_client = None
            logger.warning("Groq API key missing. Heuristic text logic will be used.")
            
        self.personality = "Warm, intuitive, and data-driven"

    async def analyze_video_ai(self, video_path: str) -> Dict[str, Any]:
        """
        Model 1: Analyzes the RAW video using Gemini Flash fully asynchronously.
        """
        if not self.gemini_client:
            return {"error": "Gemini API Key missing", "status": "fallback"}

        try:
            logger.info(f"AI ENGINE (Gemini Video): Uploading raw video for analysis: {video_path}")
            
            # File I/O runs in thread
            video_file = await asyncio.to_thread(self.gemini_client.files.upload, file=video_path)
            
            # Async polling for processing state
            timeout_seconds = 120
            start_time = asyncio.get_event_loop().time()
            
            while True:
                video_file = await asyncio.to_thread(self.gemini_client.files.get, name=video_file.name)
                
                if video_file.state == "FAILED":
                    raise Exception("Video processing failed at Gemini server.")
                if video_file.state == "ACTIVE":
                    break
                if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                    raise Exception("Gemini video processing timed out.")
                    
                logger.info("AI ENGINE: Gemini is still processing the video file...")
                await asyncio.sleep(5)  # True async non-blocking sleep

            logger.info("AI ENGINE: Video analysis in progress (Determining true behavior)...")
            
            # Execute LLM call in a thread to keep async loop unblocked (since google-genai client is sync here)
            safety = [
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
            ]
            
            response = await asyncio.to_thread(
                self.gemini_client.models.generate_content,
                model=self.gemini_model,
                contents=[video_file, VIDEO_ANALYSIS_PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0, # STRICT MODE
                    safety_settings=safety
                )
            )
            
            if not response.text:
                raise ValueError("AI ENGINE: Empty response from Gemini (Safety Blocked)")
                
            raw_text = response.text.strip()
            print(f"DEBUG [LLM RAW]: {raw_text}")
            
            # Clean up potential markdown blocks from raw response if model includes them
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            
            analysis_data = json.loads(raw_text)
            
            # STRICT VALIDATION
            valid_states = ["Relaxed / Equilibrium", "Affiliative / Playful", "Hyper-Aroused / Anxious", "Defensive / Reactive", "Suppressed / Pain State"]
            if analysis_data.get("emotional_state") not in valid_states:
                logger.warning(f"AI ENGINE: Invalid state received: {analysis_data.get('emotional_state')}. Defaulting to UNCERTAIN.")
                analysis_data["emotional_state"] = "UNCERTAIN"

            # Cleanup
            await asyncio.to_thread(self.gemini_client.files.delete, name=video_file.name)
            
            logger.info(f"AI ENGINE: Analysis successful for {analysis_data.get('pet_type')}")
            return analysis_data

        except Exception as e:
            logger.error(f"Gemini Video Analysis Error: {traceback.format_exc()}")
            return {"error": str(e), "status": "failed", "emotional_state": "UNCERTAIN"}

    async def generate_rag_report(self, analysis_data: Dict[str, Any], rag_context: str) -> Dict[str, Any]:
        """
        Model 2: Generates a clinical report using Groq Llama-3.3 fully asynchronously.
        """
        if not self.groq_client:
            return self._heuristic_report(analysis_data, rag_context)

        try:
            logger.info(f"AI ENGINE (Groq Report): Generating synthesis via {self.groq_model}...")
            prompt = f"""
            You are Dr. PET, a professional behavior intelligence system.
            Ground your report in these behavioral key points and veterinary context.
            
            ANALYSIS POINTS: {json.dumps(analysis_data)}
            RAG CONTEXT: {rag_context}
            
            JSON ONLY Response:
            {{
                "state": "Emotional summary",
                "message": "Ground-breaking explanation of the 'Why' behind the behavior.",
                "action": "Immediate clinical recommendation.",
                "care_methods": ["Method 1", "Method 2", ...],
                "clinical_audit": {{
                    "analysis": "Internal consensus reasoning",
                    "rag_grounding": "Specific influence from RAG"
                }}
            }}
            """
            
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.groq_model,
                response_format={"type": "json_object"}
            )
            
            return json.loads(chat_completion.choices[0].message.content)

        except Exception as e:
            logger.error(f"Groq Report Error: {e}")
            return self._heuristic_report(analysis_data, rag_context)

    def _heuristic_report(self, behavior_snapshot, rag_context):
        """Fallback logic for when Groq is unavailable."""
        return {
            "state": "Processing/Heuristic",
            "message": f"AI Synthesis offline. Analyzing based on internal thresholds. {rag_context}",
            "action": "Observe for further behavioral shifts.",
            "care_methods": ["Maintain safe environment", "Reduce novel stimuli"],
            "clinical_audit": {"status": "Fallback Heuristics Applied"}
        }

    async def generate_breed_card(self, breed: str, emotional_state: str) -> Dict[str, Any]:
        """
        Fast Breed Lookup with Internet RAG + Caching.
        """
        if breed in self.breed_cache: 
            logger.info(f"BREED CACHE: Cache hit for {breed}")
            return self.breed_cache[breed]
            
        if not self.groq_client or not breed:
            return {"breed": breed, "summary": "Breed data unavailable.", "traits": [], "situation_advice": ""}

        # Step 1: Internet RAG lookup with strict timeout (Single Focused Query)
        def _fetch_duckduckgo():
            raw_docs = []
            try:
                from duckduckgo_search import DDGS
                query = f"{breed} dog temperament and {emotional_state} behavioral advice"
                
                with DDGS(timeout=5) as ddgs:
                    try:
                        results = list(ddgs.text(query, max_results=3))
                        for r in results:
                            raw_docs.append(r.get("body", ""))
                    except: pass
                return raw_docs
            except Exception as e:
                logger.error(f"BREED RAG: lookup failed: {e}")
                return []
                
        raw_docs = await asyncio.to_thread(_fetch_duckduckgo)
        context_block = "\n\n".join(raw_docs[:3]) if raw_docs else f"General knowledge about {breed} dogs."

        # Step 2: Groq Synthesis
        # Step 2: Groq Synthesis
        prompt = BREED_PROFILE_PROMPT.format(
            breed=breed, 
            emotional_state=emotional_state, 
            context=context_block[:1500]
        )
        try:
            resp = await self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.groq_model,
                response_format={"type": "json_object"}
            )
            card = json.loads(resp.choices[0].message.content)
            card["source_quality"] = "Live Web RAG" if raw_docs else "Local Knowledge"
            logger.info(f"BREED CARD: Successfully generated card for {breed}")
            self.breed_cache[breed] = card
            return card
        except Exception as e:
            logger.error(f"BREED CARD: Groq synthesis failed: {e}")
            return {
                "breed": breed,
                "origin": "Unknown",
                "size": "Unknown",
                "temperament_traits": [],
                "energy_level": "Unknown",
                "known_for": f"{breed} is a recognized breed.",
                "current_situation": f"The breed is currently exhibiting {emotional_state} behavior.",
                "owner_advice": "Consult a veterinary professional.",
                "source_quality": "Fallback"
            }
    async def analyze_single_frame(self, frame: Any) -> Dict[str, Any]:
        """
        [UPGRADED] High-speed single-frame behavioral analysis.
        Extracts clinical markers for session synthesis.
        """
        if not self.gemini_client:
            return {"state": "Observing", "confidence": 0.5, "markers": []}

        try:
            # 1. Resize for light payload and faster inference
            h, w = frame.shape[:2]
            scale = min(512/w, 512/h, 1.0)
            if scale < 1.0:
                frame = cv2.resize(frame, (int(w*scale), int(h*scale)))

            success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if not success: return {"state": "Error", "confidence": 0.0, "markers": []}
            
            image_part = types.Part.from_bytes(data=buffer.tobytes(), mime_type="image/jpeg")
            
            # Use the high-fidelity professional frame prompt
            prompt = LIVE_FRAME_PROMPT
            
            # Use safety settings to prevent false 'dangerous content' rejection on animal behavior
            safety = [
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
            ]

            response = await asyncio.to_thread(
                self.gemini_client.models.generate_content,
                model=self.gemini_model,
                contents=[image_part, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                    safety_settings=safety
                )
            )
            
            if not response.text:
                raise ValueError("Empty AI response")
                
            analysis_data = json.loads(response.text)
            
            # Merge breed into markers for better live keyword visibility
            breed = analysis_data.get("breed", "Unknown")
            state = analysis_data.get("state", "Unknown")
            markers = analysis_data.get("markers", [])
            
            # Prepend breed & species if detected
            if breed != "Unknown" and f"Breed: {breed}" not in markers:
                markers.insert(0, f"Breed: {breed}")
            
            # Add general pet species from common knowledge if possible or just the breed
            analysis_data["markers"] = markers
            return analysis_data
        except Exception as e:
            logger.error(f"AI ENGINE: Snapshot error: {traceback.format_exc()}")
            return {"state": "Observing", "confidence": 0.5, "markers": ["Technical Pulse Active"]}

    async def generate_live_synthesis(self, animal_data: Dict[str, Any], markers: List[str]) -> Dict[str, Any]:
        """
        Synthesizes collected markers into a formal Behavioral Report.
        Uses parallel processing for speed.
        """
        if not self.groq_client: 
            return {
                "analysis": "AI Synthesis Offline.", 
                "recommendations": ["Manual observation required."],
                "temporal_intelligence": {"is_anomaly": False, "message": "Offline"},
                "metrics": {"happiness_score": 50, "acoustic_sentiment": "Offline"},
                "ai_insights": {"emotional_state": "Offline", "key_points": markers}
            }

        try:
            breed = animal_data.get("breed", "Unknown")
            state = animal_data.get("state", "Unknown")
            
            logger.info(f"AI ENGINE: Parallel synthesis triggered for {breed}")
            
            # Step 1: Synthesis Prompt
            prompt = LIVE_SYNTHESIS_PROMPT.format(
                breed=breed, 
                markers=", ".join(markers)
            )
            
            # Step 2: Execute both expensive LLM calls in parallel
            synthesis_task = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.groq_model,
                response_format={"type": "json_object"}
            )
            breed_task = self.generate_breed_card(breed, state)
            
            # Use gather for true concurrency
            resp, breed_card = await asyncio.gather(synthesis_task, breed_task)
            
            raw_result = json.loads(resp.choices[0].message.content)
            
            # HARMONIZE SCHEMA FOR FRONTEND (app.js)
            # This ensures displayResults() doesn't crash on missing 'temporal_intelligence'
            # and correctly populates the AI Insight panel.
            final_report = {
                "analysis": raw_result.get("analysis", ""),
                "recommendations": raw_result.get("recommendations", []),
                "breed_card": breed_card,
                "status": "completed",
                "temporal_intelligence": {
                    "is_anomaly": False, 
                    "message": "Live session monitoring complete.", 
                    "deviation_score": "0%"
                },
                "metrics": {
                    "happiness_score": raw_result.get("happiness_score", 50),
                    "acoustic_sentiment": raw_result.get("emotional_state", "Stable"),
                    "fft_peaks": [] 
                },
                "ai_insights": {
                    "emotional_state": raw_result.get("emotional_state", "Stable"),
                    "key_points": raw_result.get("key_points", [])
                }
            }
            
            return final_report
            
        except Exception as e:
            logger.error(f"AI ENGINE: Synthesis error: {e}")
            return {
                "analysis": f"Synthesis failure: {e}", 
                "recommendations": [],
                "temporal_intelligence": {"is_anomaly": False, "message": "Error during synthesis."},
                "metrics": {"happiness_score": 0, "acoustic_sentiment": "Error"},
                "ai_insights": {"emotional_state": "Error", "key_points": markers}
            }
