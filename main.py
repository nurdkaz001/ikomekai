import os
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from supabase import create_client, Client

app = FastAPI()

# Разрешаем CORS для локальной разработки и деплоя
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к Supabase и DeepSeek из переменных окружения (на Render укажешь их в настройках)
SUPABASE_URL = os.getenv("SUPABASE_URL", " ТВОЙ_SUPABASE_URL ")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", " ТВОЙ_SUPABASE_KEY ")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", " ТВОЙ_DEEPSEEK_API_KEY ")

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions" # Проверь актуальный эндпоинт DeepSeek


def analyze_with_deepseek(description: str):
    """Отправляем текст проблемы в DeepSeek для классификации"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Проанализируй жалобу жителя Астаны: "{description}".
    Верни ответ строго в формате JSON без лишнего текста со следующими полями:
    - category: выбери одно из (ЖКХ, Дороги, Благоустройство, Безопасность)
    - urgency: выбери одно из (Высокий, Средний, Низкий)
    - ai_summary: краткое резюме проблемы для коммунальных служб на русском языке (до 1-2 предложений)
    """
    
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        response = requests.post(DEEPSEEK_URL, json=payload, headers=headers)
        res_json = response.json()
        content = res_json['choices'][0]['message']['content']
        # Здесь в реальном коде лучше распарсить JSON, для хакатона можно вернуть как есть или использовать json.loads
        return content
    except Exception as e:
        return '{"category": "Общее", "urgency": "Средний", "ai_summary": "Ошибка анализа ИИ"}'

@app.post("/api/report")
async def create_report(
    description: str = Form(...),
    file: UploadFile = File(None)
):
    image_url = None
    
    # 1. Загрузка фото в Supabase Storage (если передано)
    if file:
        file_bytes = await file.read()
        file_path = f"public/{file.filename}"
        storage_res = supabase.storage.from_("incident-images").upload(file_path, file_bytes, file_options={"upsert": "true"})
        image_url = supabase.storage.from_("incident-images").get_public_url(file_path)

    # 2. Анализ текста через DeepSeek
    ai_analysis = analyze_with_deepseek(description)
    
    # Парсим JSON ответа DeepSeek (упрощенно для примера)
    import json
    try:
        # Убираем markdown обертки если они есть
        clean_json = ai_analysis.replace("```json", "").replace("```", "").strip()
        parsed_ai = json.loads(clean_json)
    except:
        parsed_ai = {"category": "ЖКХ", "urgency": "Средний", "ai_summary": description}

    # 3. Сохранение в базу данных Supabase
    data = {
        "description": description,
        "image_url": image_url,
        "category": parsed_ai.get("category"),
        "urgency": parsed_ai.get("urgency"),
        "ai_summary": parsed_ai.get("ai_summary"),
        "status": "Новая"
    }
    
    db_response = supabase.table("incidents").insert(data).execute()
    
    return {"success": True, "data": db_response.data}

@app.get("/api/reports")
def get_reports():
    """Получить все заявки для дашборда"""
    response = supabase.table("incidents").select("*").order("created_at", desc=True).execute()
    return response.data
