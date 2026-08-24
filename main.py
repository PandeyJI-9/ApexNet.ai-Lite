import os
import urllib.parse
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# ==========================================
# 1. FASTAPI & CORS FIX (Failed to fetch ka ilaaj)
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
# 2. MONGODB SPECIAL CHARACTER FIX
# ==========================================
username = urllib.parse.quote_plus("APEXNETDATABASE")

# Render ke Environment Variables se tera rahasyamayi password aayega
raw_password = os.getenv("MONGO_PASS", "") 

# Python usko automatically theek karega (@, # sab fix ho jayega)
encoded_password = urllib.parse.quote_plus(raw_password)

# Final Secure Link
mongo_uri = f"mongodb+srv://{username}:{encoded_password}@cluster0.erkfyjv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

print("Connecting to MongoDB...")
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client.get_database("apexnet") # Apna DB name check kar lena
    print("✅ Database Connected Successfully!")
except Exception as e:
    print(f"❌ Database Error: {e}")
    db = None

# ==========================================
# 3. HEALTH CHECK (Render ko zinda rakhne ke liye)
# ==========================================
@app.get("/health")
def health_check():
    return {"status": "ApexNet Enterprise is Live and Running!"}


# 👇👇 YAHAN SE NEECHE TERA PURANA CODE AAYEGA 👇👇
# (Tere /auth/signup, /auth/login, /chats aur AI Model load karne wala code as it is rehne dena)
