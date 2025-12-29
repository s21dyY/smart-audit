import re
import json
from urllib import request
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel # define request body
from fastapi.middleware.cors import CORSMiddleware  
from dotenv import load_dotenv
import asyncio
from starlette.responses import StreamingResponse

# load env 
load_dotenv()

# ADK imports
from google.adk.sessions import Session # session object
from google.adk.runners import Runner # main orchestrator runner
from google.adk.sessions import InMemorySessionService # in memrory session service
from google.genai import types # defines message types

# My agent 
from agents.agent import root_agent

app = FastAPI(title="Smart Audit")
session_service = InMemorySessionService()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    user_id: str = "default_user"
    session_id: str = "session_1"

# --- Utility to resolve/get Runner ---
active_sessions = {}
async def get_or_create_runner(session_id: str, user_id: str):
    # Persistence: check if session exists in DB service
    try:
        session = await session_service.get_session(session_id=session_id)
    except:
        session = None
    
    if not session:
        await session_service.create_session(
            app_name="SmartAudit",
            user_id=user_id,
            session_id=session_id
        )
    
    # Session Persistence: Check if Runner is in memory
    if session_id not in active_sessions:
        active_sessions[session_id] = Runner(
            agent=root_agent, 
            session_service=session_service, 
            app_name="SmartAudit"
        )
    return active_sessions[session_id]

# --- 1. Non-Streaming Endpoint (Not used in this) ---
@app.post("/chat")
async def chat(request: ChatRequest):
    runner = await get_or_create_runner(request.session_id, request.user_id)

    # format message
    user_message = types.Content(role="user", 
                                 parts=[types.Part.from_text(text=request.query)])

    # output vars
    response_text = "n/a"
    async for event in runner.run_async(new_message=user_message,
                                        user_id=request.user_id,      
                                        session_id=request.session_id):
        if event.is_final_response() and event.content:
            response_text = "".join([p.text for p in event.content.parts if p.text])
            
    return {"agent_response": response_text}

# --- 2. Streaming Endpoint ---
@app.post("/chat_stream")
async def chat_stream(request: ChatRequest):
    runner = await get_or_create_runner(request.session_id, request.user_id)
    user_message = types.Content(role="user", 
                                 parts=[types.Part.from_text(text=request.query)])
    async def event_generator():
        trace_data = {"memory_context": "N/A", "domain": "N/A", "score": 0.0}
        
        try:
            async for event in runner.run_async(new_message=user_message,
                                                user_id=request.user_id,      
                                                session_id=request.session_id):
                # Capture the "Thinking" for the Logic Trace
                agent_name = event.author or "Orchestrator"
                display_content = ""
                
                # Logic to extract sidebar trace data mid-stream
                if event.content and hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            call = part.function_call
                            display_content = f"EXEC_OP: {call.name} -> TARGET_INTENT: '{call.args.get('request', 'Internal')[:60]}...'"
                        
                        elif hasattr(part, 'function_response') and part.function_response:
                            res = part.function_response
                            display_content = f"DATA_RETURN: {res.name} -> Status: SUCCESS_VALIDATED"

                            # Capture MemoryAgent context
                            if "MemoryAgent" in res.name:
                                trace_data["memory_context"] = res.response.get("result", "Analyzing current intent...")
                            
                            # Capture MatchingAgent audit data
                            if "MatchingAgent" in res.name:
                                raw_content = res.response.get("result", "")
                                # Clean and Parse JSON safely
                                try:
                                    clean_json = raw_content.replace("```json", "").replace("```", "").strip()
                                    audit = json.loads(clean_json).get("financial_audit", {})
                                    trace_data.update({
                                        "domain": audit.get("primary_metric", "General"),
                                        "score": float(audit.get("confidence", 0.0) or 0.0),
                                        "actual_value": audit.get("value", 0.0)
                                    })
                                except: pass
                # Skip noisy packets (like raw thought signatures)
                if not display_content and not event.is_final_response():
                    continue

                # Determine event type for Frontend handling
                is_final = event.is_final_response()           
                payload = {
                    "agent": agent_name,
                    "content": "".join([p.text for p in event.content.parts if p.text]) if is_final else display_content,
                    "type": "final" if is_final else "trace",
                    "trace_data": trace_data
                }
                
                yield f"data: {json.dumps(payload)}\n\n"
                await asyncio.sleep(0.08) # UX: Smooth the scrolling
        
        except Exception as e:
            error_payload = {
                "agent": "System",
                "content": f"Error: {str(e)}",
                "type": "error",
                "trace_data": trace_data
            }
            yield f"data: {json.dumps(error_payload)}\n\n"
            await asyncio.sleep(0.08) # UX: Smooth the scrolling

    return StreamingResponse(event_generator(), media_type="text/event-stream")



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)