import os
import re
import time
import hashlib
import jwt
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from huggingface_hub import hf_hub_download
from llama_cpp import Llama
from duckduckgo_search import DDGS
from pymongo import MongoClient

# --- CONFIG ---
HF_REPO_ID = os.getenv("HF_REPO_ID", "PandeyJi9/ApexNet-Lite")
HF_FILENAME = os.getenv("HF_FILENAME", "ApexNet_by_PandeyJi_0.5B.gguf")
MONGO_URI = os.getenv("MONGO_URI", "")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-apex-key-999") # Security Key

# --- MODEL INIT (Render 512MB RAM Optimized) ---
print(f"Loading Model: {HF_FILENAME} from {HF_REPO_ID}...")
model_path = hf_hub_download(repo_id=HF_REPO_ID, filename=HF_FILENAME, local_dir="model_cache")
llm = Llama(
    model_path=model_path, 
    n_ctx=1024, 
    n_batch=64, 
    n_threads=1, 
    n_gpu_layers=0, 
    use_mmap=True, 
    verbose=False
)

# --- DATABASE CONNECTION (Enterprise Mode) ---
db = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=4000)
        db = client["ApexNetEnterprise"]
        users_db = db["users"]
        chats_db = db["chat_histories"]
        print("Database Connected: Enterprise Mode Active.")
    except Exception as e:
        print(f"Database warning: {e}")

# --- FASTAPI APP ---
app = FastAPI(title="ApexNet Enterprise API")

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# --- SECURITY FUNCTIONS ---
def hash_password(password: str, salt: bytes = None):
    if salt is None:
        salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return pwd_hash, salt

def create_jwt(username: str, role: str):
    payload = {"sub": username, "role": role, "exp": int(time.time()) + (86400 * 7)} # 7 Days valid
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized Access!")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Token Expired or Invalid!")

# --- HEALTH CHECK (Fixes Render 404 Error) ---
@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ApexNet Enterprise is Live and Running!"}

# --- AUTH ENDPOINTS ---
class AuthModel(BaseModel):
    username: str
    password: str
    key: str = None

@app.post("/auth/signup")
def signup(data: AuthModel):
    if not db: raise HTTPException(status_code=500, detail="Database Offline")
    if users_db.find_one({"username": data.username}):
        raise HTTPException(status_code=400, detail="Username already exists!")
    
    # Key System
    if data.key == "Apex-Owner-999": role = "Super Admin"
    elif data.key and data.key.startswith("Apex-Lite-"): role = "User"
    else: raise HTTPException(status_code=400, detail="Invalid Activation Key!")

    pwd_hash, salt = hash_password(data.password)
    users_db.insert_one({"username": data.username, "hash": pwd_hash, "salt": salt, "role": role})
    return {"token": create_jwt(data.username, role), "role": role}

@app.post("/auth/login")
def login(data: AuthModel):
    if not db: raise HTTPException(status_code=500, detail="Database Offline")
    user = users_db.find_one({"username": data.username})
    if not user: raise HTTPException(status_code=400, detail="User not found!")
    
    pwd_hash, _ = hash_password(data.password, user["salt"])
    if pwd_hash != user["hash"]: raise HTTPException(status_code=400, detail="Wrong Password!")
    
    return {"token": create_jwt(data.username, user["role"]), "role": user["role"]}

# --- CHAT & HISTORY ENDPOINTS ---
class ChatPayload(BaseModel):
    chat_id: str
    prompt: str

@app.get("/chats")
def get_chats(user: dict = Depends(verify_token)):
    if not db: return {"chats": []}
    user_chats = list(chats_db.find({"username": user["sub"]}, {"_id": 0}))
    return {"chats": user_chats}

@app.post("/chat")
def chat_engine(payload: ChatPayload, background_tasks: BackgroundTasks, user: dict = Depends(verify_token)):
    try:
        # 1. Deep Research
        clean_query = re.sub(r'[^\w\s]', '', payload.prompt).strip()
        research_context = ""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(" ".join(clean_query.split()[:8]), max_results=2))
                research_context = "\n".join([f"[{r['title']}]: {r['body'][:200]}" for r in results])
        except: pass

        # 2. Prompt Formulation
        sys_prompt = f"You are ApexNet, developed by PandeyJi. Current user role: {user['role']}.\nResearch: {research_context}\nReason inside <think> tags before answering."
        full_prompt = f"<|im_start|>system\n{sys_prompt}<|im_end|>\n<|im_start|>user\n{payload.prompt}<|im_end|>\n<|im_start|>assistant\n<think>\n"

        # 3. Model Inference
        output = llm(
            prompt=full_prompt, 
            max_tokens=350, 
            temperature=0.6, 
            stop=["<|im_end|>"]
        )
        text = "<think>\n" + output["choices"][0]["text"].strip()

        # 4. Parse response
        thinking_match = re.search(r'<think>(.*?)</think>', text, flags=re.DOTALL)
        thinking = thinking_match.group(1).strip() if thinking_match else ""
        answer = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

        # Ensure balanced tags just in case
        if not answer:
            answer = text

        # 5. Save to Cloud DB
        def save_db():
            if not db: return
            chat_doc = chats_db.find_one({"chat_id": payload.chat_id})
            new_msg = [
                {"role": "user", "content": payload.prompt}, 
                {"role": "assistant", "content": answer, "thinking": thinking}
            ]
            if chat_doc:
                chats_db.update_one({"chat_id": payload.chat_id}, {"$push": {"messages": {"$each": new_msg}}})
            else:
                chats_db.insert_one({
                    "username": user["sub"], 
                    "chat_id": payload.chat_id, 
                    "title": payload.prompt[:30]+"...", 
                    "messages": new_msg
                })
        
        background_tasks.add_task(save_db)
        
        return {"answer": answer, "thinking": thinking}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
