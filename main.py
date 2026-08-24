import os
import urllib.parse
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from duckduckgo_search import DDGS

# ==========================================
# 1. APP SETUP & CORS FIX (No More 'Failed to fetch')
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
# 2. DATABASE SETUP (Secured & URL Encoded)
# ==========================================
username = urllib.parse.quote_plus("APEXNETDATABASE")
# Render dashboard se tera asli password uthayega
raw_password = os.getenv("MONGO_PASS", "") 
# Special characters ko khud theek karega
encoded_password = urllib.parse.quote_plus(raw_password)

mongo_uri = f"mongodb+srv://{username}:{encoded_password}@cluster0.erkfyjv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

print("Connecting to MongoDB...")
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client.get_database("apexnet")
    users_col = db.get_collection("users")
    chats_col = db.get_collection("chats")
    print("✅ Database Connected Successfully!")
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
# 4. API ROUTES (Login & Signup)
# ==========================================
@app.get("/health")
def health_check():
    return {"status": "ApexNet Enterprise is Live!"}

@app.post("/auth/signup")
def signup(req: SignupReq):
    if db is None:
        raise HTTPException(status_code=500, detail="Database Offline")
    
    role = "User"
    if req.key == "Apex-Owner-999":
        role = "Admin"
    elif req.key != "Apex-Lite-0001":
        raise HTTPException(status_code=400, detail="Invalid Activation Key!")

    if users_col.find_one({"username": req.username}):
        raise HTTPException(status_code=400, detail="Username already taken!")
    
    token = "token_" + str(uuid.uuid4())
    new_user = {"username": req.username, "password": req.password, "role": role, "token": token}
    users_col.insert_one(new_user)
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
# 5. AI & CHAT LOGIC (Lightweight + Web Search)
# ==========================================
@app.post("/chat")
def chat(req: ChatReq, request: Request):
    user = get_current_user(request)
    
    thinking = "1. Processing user prompt...\n2. Initializing ApexNet Lightweight Engine...\n"
    
    try:
        # Live Web Search
        thinking += "3. Fetching real-time context via DuckDuckGo...\n"
        results = DDGS().text(req.prompt, max_results=1)
        search_context = results[0]['body'] if results else "No recent data found."
        thinking += "4. Context acquired. Generating response..."
        
        answer = f"**System Response:**\n{search_context}\n\n*ApexNet Database Sync Active. Query processed for {user['username']}*"
    except Exception as e:
        thinking += f"\nSearch bypassed due to connection.\n"
        answer = f"Hello **{user['username']}**! ApexNet received your prompt: *'{req.prompt}'*"

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
