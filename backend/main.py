import asyncio
import json
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ollama

# MCP Client imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sessions = {}
MODEL = "llama3.2"

# MCP Server config - points to your mcp_server.py file
MCP_PARAMS = StdioServerParameters(
    command="python",
    args=["mcp_server.py"], # Make sure you run uvicorn from the backend/ folder!
)

# Helper: Call an MCP tool and return the text result
async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    async with stdio_client(MCP_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            # MCP returns a list of content blocks; we grab the first text block
            text_result = result.content[0].text
            return json.loads(text_result) if text_result.startswith("{") else text_result


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    authenticated: bool


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):   # <--- MUST be async now!
    sid = req.session_id or str(uuid.uuid4())
    session = sessions.setdefault(sid, {"history": [], "authenticated": False, "user": None})

    # ---------- AUTH FLOW via MCP ----------
    if not session["authenticated"]:
        text = req.message.strip().lower()
        if "@" in text and "." in text:
            email = next((tok for tok in text.split() if "@" in tok), None)
            if email:
                email = email.strip(".,!?")
                # 🔥 Call the MCP tool instead of direct DB call!
                result = await call_mcp_tool("authenticate_user", {"email": email})
                
                if result.get("authenticated"):
                    session["authenticated"] = True
                    session["user"] = result["user"]
                    reply = f"✅ Verified! Welcome, {result['user']['name']}. How can I help you today?"
                else:
                    reply = f"❌ {result['message']}"
                
                session["history"].append({"role": "assistant", "content": reply})
                return ChatResponse(session_id=sid, reply=reply, authenticated=session["authenticated"])
        
        reply = "👋 Hi! Please share your email ID to continue."
        session["history"].append({"role": "assistant", "content": reply})
        return ChatResponse(session_id=sid, reply=reply, authenticated=False)

    # ---------- CHAT FLOW (Authenticated) ----------
    session["history"].append({"role": "user", "content": req.message})
    user_name = session["user"]["name"]

    # Check if user is asking about weather -> call MCP weather tool
    tool_context = ""
    if "weather" in req.message.lower():
        # Extract city (very naive, for learning)
        city = "India" if "india" in req.message.lower() else req.message
        weather_data = await call_mcp_tool("get_weather", {"city": city})
        tool_context = f"\n[SYSTEM NOTE: Real weather data is: {weather_data}. Use this to answer!]"

    messages = [
        {"role": "system", "content": f"You are a helpful assistant. User is {user_name}.{tool_context}"}
    ] + session["history"][-10:]

    try:
        response = ollama.chat(model=MODEL, messages=messages)
        reply = response["message"]["content"]
    except Exception as e:
        raise HTTPException(500, f"Ollama error: {e}")

    session["history"].append({"role": "assistant", "content": reply})
    return ChatResponse(session_id=sid, reply=reply, authenticated=True)


@app.post("/logout")
def logout(session_id: str):
    sessions.pop(session_id, None)
    return {"ok": True}