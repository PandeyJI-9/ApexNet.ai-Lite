import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# ==========================================
# 1. APP SETUP & CORS (Fixes 'Failed to fetch')
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
# 2. THE PERFECT MONGODB CONNECTION
# ==========================================
# Tera exact naya link, directly embedded!
MONGO_URI = "mongodb+srv://gamerinpubg1229_db_user:5cywj4SrBooKSN65@cluster0.0eit7bi.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

print("Connecting to MongoDB Atlas...")
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("apexnet")
    users_col = db.get_collection("users")
    chats_col = db.get_collection("chats")
    
    # Ek ping test confirm karne ke liye ki andar access mil gaya
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
# 4. API ROUTES (Complete Auth System)
# ==========================================
@app.get("/health")
def health_check():
    return {"status": "ApexNet Database is Live and Secure! 🚀"}

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
# 5. CHAT LOGIC (Saving strictly to Database)
# ==========================================
@app.post("/chat")
def chat(req: ChatReq, request: Request):
    user = get_current_user(request)
    
    thinking = "1. Processing prompt...\n2. Routing through Secure MongoDB Atlas...\n3. ApexNet System Active!\n"
    answer = f"Hello **{user['username']}**! Your prompt: *'{req.prompt}'* has been fully processed and saved to the new database! 💯"

    # Save to MongoDB Database (Permanent Save)
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
