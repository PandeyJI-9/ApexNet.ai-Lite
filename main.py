import uuid
import os
import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# Imports for AI and Search
try:
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama
    from duckduckgo_search import DDGS
except ImportError:
    hf_hub_download = None
    Llama = None
    DDGS = None

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
# 3. HUGGING FACE MODEL LOAD (ULTRA LOW RAM)
# ==========================================
print("Fetching ApexNet from Hugging Face...")
try:
    if hf_hub_download and Llama:
        HF_REPO_ID = "PandeyJi9/ApexNet-Lite"  
        MODEL_FILENAME = "ApexNet_by_PandeyJi_0.5B.gguf"
        
        print(f"Downloading {MODEL_FILENAME} from {HF_REPO_ID}...")
        model_path = hf_hub_download(repo_id=HF_REPO_ID, filename=MODEL_FILENAME)
        
        print("✅ Downloaded! Forcing Disk Mapping...")
        llm = Llama(
            model_path=model_path,
            n_ctx=128,       # Thoda context badhaya hai Live Search ke liye
            n_threads=1,     
            n_batch=1,       
            use_mmap=True    
        )
        print("✅ ApexNet AI Engine Ready!")
    else:
        llm = None
        print("❌ Libraries missing!")
except Exception as e:
    print(f"❌ HF Load Error: {e}")
    llm = None

# ==========================================
# 4. REQUEST MODELS & AUTH ROUTES
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
# 5. ASLI AI + LIVE RESEARCH ENGINE 🌐
# ==========================================
@app.post("/chat")
def chat(req: ChatReq, request: Request):
    user = get_current_user(request)
    
    thinking = f"1. Prompt received: {req.prompt}\n2. Booting ApexNet-Lite Engine...\n"
    search_context = ""

    # Live DuckDuckGo Search Logic
    if DDGS:
        try:
            thinking += "3. Fetching live data from DuckDuckGo...\n"
            # Sirf 1 result lenge aur usko truncate karenge taaki RAM na fate
            results = DDGS().text(req.prompt, max_results=1)
            if results:
                search_context = results[0]['body'][:100]  # Max 100 characters
                thinking += "   ✅ Live Web Data injected!\n"
        except Exception as e:
            thinking += "   ⚠️ Search Engine blocked or timeout (Running offline mode).\n"
    
    if llm is None:
        answer = "Bhai, tera HF model load nahi ho paya (RAM issue ya file missing)."
        thinking += "❌ Model initialization failed.\n"
    else:
        try:
            thinking += "4. Generating ApexNet response...\n"
            
            # 🔥 PROMPT ENGINEERING: Search + Bhai Mode
            aaj_ki_tarik = datetime.datetime.now().strftime("%d %B %Y")
            custom_prompt = f"System: Tu 'ApexNet', ek smart AI hai. Aaj ki tarik {aaj_ki_tarik} hai. Tu hamesha 'Bhai' bol kar dosti wale Hinglish me baat karta hai.\n"
            
            if search_context:
                custom_prompt += f"Live Web Info: {search_context}\n"
                
            custom_prompt += f"User: {req.prompt}\nAI:"
            
            response = llm(
                custom_prompt, 
                max_tokens=60, # Tokens limit me rakhe hain taaki crash na ho
                stop=["User:", "\n\n", "System:"], 
                echo=False
            )
            answer = response["choices"][0]["text"].strip()
            
            if not answer:
                answer = "Bhai main thoda confuse ho gaya, ek baar phir se pooch! 😅"
                
            thinking += "5. AI output successful! 🚀\n"
        except Exception as e:
            answer = "Bhai tera prompt process karne me server ki saans phool gayi. 137 RAM error se bacha raha hu, wapas try kar!"
            thinking += f"❌ Generation Error: {e}\n"

    # Save to MongoDB
    chat_doc = chats_col.find_one({"chat_id": req.chat_id, "username": user["username"]})
    user_msg = {"role": "user", "content": req.prompt}
    bot_msg = {"role": "assistant", "content": answer, "thinking": thinking}
    
    if chat_doc:
        chats_col.update_one({"chat_id": req.chat_id}, {"$push": {"messages": {"$each": [user_msg, bot_msg]}}})
    else:
        chats_col.insert_one({"chat_id": req.chat_id, "username": user["username"], "title": req.prompt[:15] + "...", "messages": [user_msg, bot_msg]})

    return {"answer": answer, "thinking": thinking}
