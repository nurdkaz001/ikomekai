import os
import json
import secrets
import requests
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from supabase import create_client, Client

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Настройки Supabase и DeepSeek ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print("Supabase init error:", e)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# --- Настройки защиты Админки ---
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ikomek2026")

security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def analyze_with_deepseek(description: str) -> dict:
    if not DEEPSEEK_API_KEY:
        return {
            "category": "Общее",
            "urgency": "Средний",
            "ai_summary": "DeepSeek API ключ не настроен"
        }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    Проанализируй жалобу жителя Астаны: "{description}".
    Верни ответ СТРОГО в формате валидного JSON без markdown оберток и лишнего текста:
    {{
      "category": "выбери строго одно из: (ЖКХ, Дороги, Благоустройство, Безопасность)",
      "urgency": "выбери строго одно из: (Высокий, Средний, Низкий)",
      "ai_summary": "краткое резюме проблемы для коммунальных служб (до 2 предложений)"
    }}
    """

    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }

    try:
        response = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=10)
        res_json = response.json()
        content = res_json['choices'][0]['message']['content'].strip()
        
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        return json.loads(content)
    except Exception as e:
        print("DeepSeek Error:", e)
        return {
            "category": "ЖКХ",
            "urgency": "Средний",
            "ai_summary": description
        }


# --- Публичные эндпоинты (для жителей) ---

@app.get("/")
async def read_root():
    return FileResponse("index.html")


@app.post("/api/report")
async def create_report(
    description: str = Form(...),
    user_id: str = Form("anonymous"),
    file: UploadFile = File(None)
):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client не инициализирован.")

    image_url = None

    if file and file.filename:
        try:
            file_bytes = await file.read()
            file_path = f"public/{file.filename}"
            supabase.storage.from_("incident-images").upload(
                file_path, 
                file_bytes, 
                file_options={"upsert": "true"}
            )
            image_url = supabase.storage.from_("incident-images").get_public_url(file_path)
        except Exception as e:
            print("Storage upload error:", e)

    parsed_ai = analyze_with_deepseek(description)

    data = {
        "description": description,
        "image_url": image_url,
        "category": parsed_ai.get("category", "Общее"),
        "urgency": parsed_ai.get("urgency", "Средний"),
        "ai_summary": parsed_ai.get("ai_summary", description),
        "status": "Новая",
        "user_id": user_id
    }

    try:
        db_response = supabase.table("incidents").insert(data).execute()
        return {"success": True, "data": db_response.data}
    except Exception as e:
        print("DB Insert Error:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports")
def get_reports(user_id: str = None):
    if not supabase:
        return []
    try:
        query = supabase.table("incidents").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        response = query.order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print("DB Fetch Error:", e)
        return []


# --- Защищенные эндпоинты (только для сотрудников Акимата) ---

@app.get("/admin", response_class=FileResponse)
async def admin_page(username: str = Depends(verify_admin)):
    return FileResponse("admin.html")


@app.get("/api/reports/all")
def get_all_reports(category: str = None, urgency: str = None, username: str = Depends(verify_admin)):
    if not supabase:
        return []
    try:
        query = supabase.table("incidents").select("*")
        if category:
            query = query.eq("category", category)
        if urgency:
            query = query.eq("urgency", urgency)
            
        response = query.order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print("Admin Fetch Error:", e)
        return []


@app.patch("/api/reports/{report_id}/status")
async def update_report_status(report_id: str, request: Request, username: str = Depends(verify_admin)):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase не инициализирован")
    
    body = await request.json()
    new_status = body.get("status")
    
    try:
        response = supabase.table("incidents").update({"status": new_status}).eq("id", report_id).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print("Status Update Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
