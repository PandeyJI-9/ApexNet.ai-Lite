import os
import re
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from duckduckgo_search import DDGS
from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Configuration (PandeyJi9 / ApexNet-Lite)
# ---------------------------------------------------------------------------
HF_REPO_ID = os.getenv("HF_REPO_ID", "PandeyJi9/ApexNet-Lite")
HF_FILENAME = os.getenv("HF_FILENAME", "ApexNet_by_PandeyJi_0.5B.gguf")
HF_TOKEN = os.getenv("HF_TOKEN", None)
MONGO_URI = os.getenv("MONGO_URI", "")

# ---------------------------------------------------------------------------
# 1. Download & Initialize 0.5B Model (Render 512MB RAM Optimized)
# ---------------------------------------------------------------------------
print(f"Downloading/Verifying: {HF_FILENAME} from https://huggingface.co/{HF_REPO_ID}...")
model_path = hf_hub_download(
    repo_id=HF_REPO_ID,
    filename=HF_FILENAME,
    token=HF_TOKEN,
    local_dir="model_cache"
)

llm = Llama(
    model_path=model_path,
    n_ctx=1024,           # Safe context for thinking & web snippets
    n_batch=64,           # Prevents RAM spikes on 512MB tier
    n_threads=1,          # Match free-tier single thread allocation
    n_gpu_layers=0,       # Pure CPU mode
    use_mmap=True,        # Memory mapping enabled
    use_mlock=False,
    verbose=False
)
print("ApexNet-Lite 0.5B Engine Ready.")

# ---------------------------------------------------------------------------
# 2. Collective Memory Layer (MongoDB Atlas)
# ---------------------------------------------------------------------------
db_collection = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
        db = client["ApexNetCore"]
        db_collection = db["user_experiences"]
        print("Connected to Collective Memory Database.")
    except Exception as e:
        print(f"Database warning: {e}")

# ---------------------------------------------------------------------------
# 3. Agent Intelligence Tools (Deep Research & Memory Retrieval)
# ---------------------------------------------------------------------------
def execute_deep_research(user_prompt: str) -> str:
    """Extracts search terms and fetches live web context."""
    clean_query = re.sub(r'[^\w\s]', '', user_prompt).strip()
    search_query = " ".join(clean_query.split()[:8])
    
    try:
        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(search_query, max_results=3))
            for r in search_results:
                title = r.get("title", "Reference")
                body = r.get("body", "")
                if body:
                    results.append(f"• [{title}]: {body[:250]}")
        
        if not results:
            return "No real-time web results found."
        return "\n".join(results)
    except Exception as e:
        return f"Research lookup bypassed: {str(e)}"

def query_collective_memory(user_prompt: str) -> str:
    """Retrieves previous user mistakes, warnings, and solutions."""
    if db_collection is None:
        return "No collective memory logs connected."
    
    try:
        keywords = [w.lower() for w in user_prompt.split() if len(w) > 3]
        if not keywords:
            recent_logs = list(db_collection.find().sort("_id", -1).limit(2))
        else:
            filter_query = {"$or": [{"issue": {"$regex": k, "$options": "i"}} for k in keywords[:3]]}
            recent_logs = list(db_collection.find(filter_query).limit(2))
            if not recent_logs:
                recent_logs = list(db_collection.find().sort("_id", -1).limit(2))

        if not recent_logs:
            return "Fresh query. No previous community failure records."

        formatted_logs = []
        for doc in recent_logs:
            warn = doc.get("warning", "")
            sol = doc.get("solution", "")
            formatted_logs.append(f"• Community Record: {warn} -> Solution: {sol}")
        return "\n".join(formatted_logs)
    except Exception:
        return "Memory query bypassed."

def save_experience_to_memory(prompt: str, response: str):
    """Background worker to save lessons for future users."""
    if db_collection is None:
        return
    try:
        clean_ans = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
        clean_ans = clean_ans.replace("\n", " ")[:200]
        
        db_collection.insert_one({
            "issue": prompt[:150],
            "warning": f"Topic: {prompt[:60]}",
            "solution": clean_ans
        })
    except Exception as e:
        print(f"Memory logging error: {e}")

# ---------------------------------------------------------------------------
# 4. FastAPI App & Routes
# ---------------------------------------------------------------------------
app = FastAPI(title="ApexNet-Lite AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class ChatPayload(BaseModel):
    prompt: str
    deep_research: bool = True
    deep_thinking: bool = True
    max_tokens: int = Field(default=350, ge=50, le=450)

@app.get("/health")
def health_check():
    return {
        "status": "ApexNet-Lite Online",
        "engine": "0.5B Quantized + Scaffolding",
        "model": HF_FILENAME,
        "database": "Connected" if db_collection is not None else "Disconnected"
    }

@app.post("/chat")
def chat_handler(payload: ChatPayload, background_tasks: BackgroundTasks):
    try:
        # Step 1: Deep Research
        research_context = "Deep research disabled."
        if payload.deep_research:
            research_context = execute_deep_research(payload.prompt)

        # Step 2: Collective User Memory Retrieval
        memory_context = query_collective_memory(payload.prompt)

        # Step 3: Scaffold Instruction Prompt
        system_rules = (
            "You are ApexNet-Lite, a fast reasoning assistant created by PandeyJi.\n"
            "Use the provided Live Web Research and Collective User Memory to formulate your response.\n\n"
            f"[LIVE RESEARCH DATA]\n{research_context}\n\n"
            f"[COLLECTIVE USER MEMORY / PAST ISSUES]\n{memory_context}\n\n"
            "RESPONSE RULES:\n"
            "1. First, reason step-by-step inside <think> ... </think> tags.\n"
            "2. If Collective Memory has a past mistake on this topic, warn the user explicitly: 'Bhai ye galti mat karna...' or similar.\n"
            "3. Provide the clean, direct final solution immediately after </think>."
        )

        model_prompt = (
            f"<|im_start|>system\n{system_rules}<|im_end|>\n"
            f"<|im_start|>user\n{payload.prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        if payload.deep_thinking:
            model_prompt += "<think>\n"

        # Step 4: Run Inference
        output = llm(
            prompt=model_prompt,
            max_tokens=payload.max_tokens,
            temperature=0.65,
            top_p=0.85,
            stop=["<|im_end|>", "User:"]
        )
        generated_text = output["choices"][0]["text"].strip()

        if payload.deep_thinking and not generated_text.startswith("<think>"):
            generated_text = "<think>\n" + generated_text
        if "<think>" in generated_text and "</think>" not in generated_text:
            generated_text += "\n</think>\n"

        # Step 5: Background Memory Storage
        background_tasks.add_task(save_experience_to_memory, payload.prompt, generated_text)

        # Parse Thinking vs Final Answer for clean frontend parsing
        thinking_match = re.search(r'<think>(.*?)</think>', generated_text, flags=re.DOTALL)
        thinking_content = thinking_match.group(1).strip() if thinking_match else ""
        final_answer = re.sub(r'<think>.*?</think>', '', generated_text, flags=re.DOTALL).strip()

        return {
            "thinking": thinking_content,
            "answer": final_answer if final_answer else generated_text,
            "raw_response": generated_text,
            "research_used": payload.deep_research,
            "memory_attached": bool(db_collection is not None)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
