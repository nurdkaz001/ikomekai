import os
import json
import secrets
import requests
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ikomek2026")


def check_auth(request: Request):
    session = request.cookies.get("admin_session")
    if session != "active":
        raise HTTPException(status_code=401, detail="Unauthorized")


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


# --- Публичные эндпоинты ---

@app.get("/")
async def read_root():
    return FileResponse("index.html")


@app.get("/admin", response_class=FileResponse)
async def admin_page():
    return FileResponse("admin.html")


@app.post("/api/admin/login")
async def admin_login(request: Request, response: Response):
    body = await request.json()
    u = body.get("username", "")
    p = body.get("password", "")

    if secrets.compare_digest(u, ADMIN_USERNAME) and secrets.compare_digest(p, ADMIN_PASSWORD):
        response.set_cookie(key="admin_session", value="active", httponly=True, max_age=3600*12)
        return {"success": True}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/api/admin/logout")
async def admin_logout(response: Response):
    response.delete_cookie("admin_session")
    return {"success": True}


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


@app.get("/api/notifications")
def get_notifications(user_id: str):
    if not supabase or not user_id:
        return []
    try:
        response = supabase.table("notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        print("Notifications Fetch Error:", e)
        return []


# --- Защищенные эндпоинты ---

@app.get("/api/reports/all", dependencies=[Depends(check_auth)])
def get_all_reports(category: str = None, urgency: str = None):
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


@app.patch("/api/reports/{report_id}/status", dependencies=[Depends(check_auth)])
async def update_report_status(report_id: str, request: Request):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase не инициализирован")
    
    body = await request.json()
    new_status = body.get("status")
    
    try:
        # 1. Если статус меняется на "Решено"
        if new_status == "Решено":
            # Находим инцидент, чтобы узнать user_id и описание
            report_res = supabase.table("incidents").select("*").eq("id", report_id).execute()
            if report_res.data:
                item = report_res.data[0]
                uid = item.get("user_id")
                desc = item.get("description", "Заявка")
                
                # Отправляем уведомление жителю
                if uid:
                    msg = f"Ваше обращение «{desc[:50]}...» успешно решено городскими службами Акимата!"
                    supabase.table("notifications").insert({"user_id": uid, "message": msg}).execute()
                
                # Удаляем проблему из таблицы incidents
                supabase.table("incidents").delete().eq("id", report_id).execute()
                return {"success": True, "deleted": True}
        
        # Для других статусов ("В работе", "Новая") просто обновляем
        response = supabase.table("incidents").update({"status": new_status}).eq("id", report_id).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        print("Status Update Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
