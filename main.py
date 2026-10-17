import os
import json
import requests
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

app = FastAPI()

# CORS настройки (чтобы фронтенд мог отправлять запросы без блокировок)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к Supabase из переменных окружения Render
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Ключ DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def analyze_with_deepseek(description: str) -> dict:
    """Анализ проблемы с помощью DeepSeek AI"""
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
        
        # Очистка от возможной markdown разметки ```json ... ```
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        parsed = json.loads(content)
        return parsed
    except Exception as e:
        print("DeepSeek Error:", e)
        return {
            "category": "ЖКХ",
            "urgency": "Средний",
            "ai_summary": description
        }


@app.get("/")
def read_root():
    """Проверочный маршрут для Render"""
    return {
        "status": "online",
        "project": "Astana Smart City AI Manager",
        "message": "API работает корректно!"
    }


@app.post("/api/report")
async def create_report(
    description: str = Form(...),
    file: UploadFile = File(None)
):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client не инициализирован. Проверь переменные окружения.")

    image_url = None

    # 1. Загрузка фото в Supabase Storage
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

    # 2. Обработка через DeepSeek AI
    parsed_ai = analyze_with_deepseek(description)

    # 3. Сохранение в Supabase DB
    data = {
        "description": description,
        "image_url": image_url,
        "category": parsed_ai.get("category", "Общее"),
        "urgency": parsed_ai.get("urgency", "Средний"),
        "ai_summary": parsed_ai.get("ai_summary", description),
        "status": "Новая"
    }

    db_response = supabase.table("incidents").insert(data).execute()
    return {"success": True, "data": db_response.data}


@app.get("/api/reports")
def get_reports():
    """Получить все заявки для дашборда"""
    if not supabase:
        return []
    response = supabase.table("incidents").select("*").order("created_at", desc=True).execute()
    return response.data
