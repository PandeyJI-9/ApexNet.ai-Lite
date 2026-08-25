import uuid
import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from duckduckgo_search import DDGS

# ==========================================
# 1. APP SETUP & CORS 
# ==========================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. MONGODB CONNECTION
# ==========================================
MONGO_URI = "mongodb+srv://gamerinpubg1229_db_user:5cywj4SrBooKSN65@cluster0.0eit7bi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

print("Connecting to MongoDB Atlas...")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("apexnet")
    users_col = db.get_collection("users")
    chats_col = db.get_collection("chats")
    client.admin.command('ping')
    print("✅ Database Connected & Verified Successfully!")
except Exception as e:
    print(f"❌ Database Error: {e}")
    db = None

# ==========================================
# 3. REQUEST MODELS
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

# ==========================================
# 4. API ROUTES (Auth)
# ==========================================
@app.get("/health")
def health_check():
    return {"status": "ApexNet System is Live!"}

@app.post("/auth/signup")
def signup(req: SignupReq):
    if db is None:
        raise HTTPException(status_code=500, detail="Database Offline")
    role = "Admin" if req.key == "Apex-Owner-999" else "User"
    if req.key not in ["Apex-Owner-999", "Apex-Lite-0001"]:
        raise HTTPException(status_code=400, detail="Invalid Activation Key!")
    if users_col.find_one({"username": req.username}):
        raise HTTPException(status_code=400, detail="Username already exists!")
    
    token = "token_" + str(uuid.uuid4())
    users_col.insert_one({"username": req.username, "password": req.password, "role": role, "token": token})
    return {"token": token, "role": role}

@app.post("/auth/login")
def login(req: LoginReq):
    if db is None:
        raise HTTPException(status_code=500, detail="Database Offline")
    user = users_col.find_one({"username": req.username, "password": req.password})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Username or Password!")
    return {"token": user["token"], "role": user.get("role", "User")}

def get_current_user(request: Request):
    if db is None:
        raise HTTPException(status_code=500, detail="Database Offline")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    token = auth_header.split(" ")[1]
    user = users_col.find_one({"token": token})
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user

@app.get("/chats")
def get_chats(request: Request):
    user = get_current_user(request)
    user_chats = list(chats_col.find({"username": user["username"]}, {"_id": 0}))
    return {"chats": user_chats}

# ==========================================
# 5. ASLI AI CHAT LOGIC (Dimag Is Back!)
# ==========================================
@app.post("/chat")
def chat(req: ChatReq, request: Request):
    user = get_current_user(request)
    prompt_lower = req.prompt.lower()
    
    thinking = f"1. Processing prompt from {user['username']}...\n2. Analyzing context...\n"
    
    # 🧠 AI KA LOGIC
    if "tarik" in prompt_lower or "date" in prompt_lower:
        aaj_ki_tarik = datetime.datetime.now().strftime("%d %B %Y")
        answer = f"Bhai, aaj ki tarik **{aaj_ki_tarik}** hai. Aur bata kya madad karu?"
        thinking += "3. Extracted current system date.\n"
        
    elif "naam" in prompt_lower:
        answer = f"Mera naam **ApexNet AI** hai! Aur tu mera admin hai. 😎"
        thinking += "3. Identity matrix loaded.\n"
        
    else:
        try:
            # DuckDuckGo Live Search Engine
            thinking += "3. Searching live web for the answer...\n"
            results = DDGS().text(req.prompt, max_results=1)
            search_context = results[0]['body'] if results else "Mujhe samajh nahi aaya bhai, thoda aur detail me bata."
            answer = f"**Result:**\n{search_context}"
            thinking += "4. Fetched real-time data from DuckDuckGo.\n"
        except Exception as e:
            answer = "Bhai server abhi thoda busy hai, par mera connection MongoDB se 100% done hai! 🔥"
            thinking += "3. Search bypassed due to high load.\n"

    # Save to MongoDB
    chat_doc = chats_col.find_one({"chat_id": req.chat_id, "username": user["username"]})
    user_msg = {"role": "user", "content": req.prompt}
    bot_msg = {"role": "assistant", "content": answer, "thinking": thinking}
    
    if chat_doc:
        chats_col.update_one(
            {"chat_id": req.chat_id},
            {"$push": {"messages": {"$each": [user_msg, bot_msg]}}}
        )
    else:
        chats_col.insert_one({
            "chat_id": req.chat_id,
            "username": user["username"],
            "title": req.prompt[:15] + "...",
            "messages": [user_msg, bot_msg]
        })

    return {"answer": answer, "thinking": thinking}
