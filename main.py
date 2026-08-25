import uuid
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# HF aur Llama-cpp imports
try:
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama
except ImportError:
    hf_hub_download = None
    Llama = None

# ==========================================
# 1. APP SETUP & CORS 
# ==========================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ==========================================
# 2. MONGODB CONNECTION
# ==========================================
MONGO_URI = "mongodb+srv://gamerinpubg1229_db_user:5cywj4SrBooKSN65@cluster0.0eit7bi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("apexnet")
    users_col = db.get_collection("users")
    chats_col = db.get_collection("chats")
except Exception as e:
    db = None

# ==========================================
# 3. HUGGING FACE SE MODEL LOAD KARNA 🔥
# ==========================================
print("Fetching ApexNet from Hugging Face...")
try:
    if hf_hub_download and Llama:
        # 👇👇 TERA ASLI HUGGING FACE REPO 👇👇
        HF_REPO_ID = "PandeyJi9/ApexNet-Lite"  
        
        # 🚨 DHYAN DE: Agar HF par teri file ka naam alag hai, toh yahan change kar lena!
        MODEL_FILENAME = "ApexNet_by_PandeyJi_0.5B.gguf"
        
        print(f"Downloading {MODEL_FILENAME} from {HF_REPO_ID}...")
        
        # Ye Render ke server pe model download karega
        model_path = hf_hub_download(repo_id=HF_REPO_ID, filename=MODEL_FILENAME)
        
        print("✅ Downloaded! Loading into RAM...")
        llm = Llama(
            model_path=model_path,
            n_ctx=256,       # Low RAM Limit
            n_threads=2,     
            use_mmap=False   
        )
        print("✅ ApexNet AI Engine Ready!")
    else:
        llm = None
        print("❌ Libraries missing!")
except Exception as e:
    print(f"❌ HF Load Error: {e}")
    llm = None

# ==========================================
# 4. REQUEST MODELS & API ROUTES
# ==========================================
class SignupReq(BaseModel):
    username: str
    password: str
    key: str

class LoginReq(BaseModel):
    username: str
    password: str

class ChatReq(BaseModel):
    chat_id: str
    prompt: str

@app.get("/health")
def health_check():
    return {"status": "ApexNet AI System is Live!"}

@app.post("/auth/signup")
def signup(req: SignupReq):
    if db is None: raise HTTPException(status_code=500, detail="Database Offline")
    role = "Admin" if req.key == "Apex-Owner-999" else "User"
    if req.key not in ["Apex-Owner-999", "Apex-Lite-0001"]: raise HTTPException(status_code=400, detail="Invalid Key!")
    if users_col.find_one({"username": req.username}): raise HTTPException(status_code=400, detail="Username taken!")
    
    token = "token_" + str(uuid.uuid4())
    users_col.insert_one({"username": req.username, "password": req.password, "role": role, "token": token})
    return {"token": token, "role": role}

@app.post("/auth/login")
def login(req: LoginReq):
    if db is None: raise HTTPException(status_code=500, detail="Database Offline")
    user = users_col.find_one({"username": req.username, "password": req.password})
    if not user: raise HTTPException(status_code=401, detail="Invalid Credentials!")
    return {"token": user["token"], "role": user.get("role", "User")}

def get_current_user(request: Request):
    if db is None: raise HTTPException(status_code=500, detail="Database Offline")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "): raise HTTPException(status_code=401, detail="Unauthorized")
    user = users_col.find_one({"token": auth_header.split(" ")[1]})
    if not user: raise HTTPException(status_code=401, detail="Unauthorized")
    return user

@app.get("/chats")
def get_chats(request: Request):
    user = get_current_user(request)
    return {"chats": list(chats_col.find({"username": user["username"]}, {"_id": 0}))}

# ==========================================
# 5. ASLI MODEL INFERENCE (Chat)
# ==========================================
@app.post("/chat")
def chat(req: ChatReq, request: Request):
    user = get_current_user(request)
    
    thinking = f"1. Prompt received: {req.prompt}\n2. Booting up ApexNet-Lite from Hugging Face...\n"
    
    if llm is None:
        answer = "Bhai, tera HF model load nahi ho paya. Ek baar repo aur file ka naam check kar!"
        thinking += "❌ Model initialization failed.\n"
    else:
        try:
            thinking += "3. Generating response via local GGUF model...\n"
            response = llm(
                f"Question: {req.prompt}\nAnswer:", 
                max_tokens=150, 
                stop=["Question:", "\n"], 
                echo=False
            )
            answer = response["choices"][0]["text"].strip()
            thinking += "4. AI output successful! 🚀\n"
        except Exception as e:
            answer = "Model ne generate karne me error de diya bhai."
            thinking += f"❌ Error: {e}\n"

    # Save to MongoDB
    chat_doc = chats_col.find_one({"chat_id": req.chat_id, "username": user["username"]})
    user_msg = {"role": "user", "content": req.prompt}
    bot_msg = {"role": "assistant", "content": answer, "thinking": thinking}
    
    if chat_doc:
        chats_col.update_one({"chat_id": req.chat_id}, {"$push": {"messages": {"$each": [user_msg, bot_msg]}}})
    else:
        chats_col.insert_one({"chat_id": req.chat_id, "username": user["username"], "title": req.prompt[:15] + "...", "messages": [user_msg, bot_msg]})

    return {"answer": answer, "thinking": thinking}
