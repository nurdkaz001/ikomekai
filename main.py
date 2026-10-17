import os
import json
import requests
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from supabase import create_client, Client

app = FastAPI()

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print("Supabase init error:", e)

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


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Интерфейс Astana iKomek AI с надежными встроенными стилями и поддержкой RU/KZ"""
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Astana Smart City — iKomek AI Portal</title>
    <link href="[https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css](https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css)" rel="stylesheet">
    <link href="[https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap)" rel="stylesheet">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background-color: #F8FAFC; color: #1E293B; min-height: 100vh; display: flex; flex-direction: column; }
        
        /* Header */
        header { background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(10px); border-bottom: 1px solid #E2E8F0; position: sticky; top: 0; z-index: 50; }
        .header-container { max-width: 1200px; margin: 0 auto; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; }
        .logo-box { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 40px; height: 40px; background: #2563EB; color: white; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); }
        .logo-text h1 { font-size: 16px; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px; }
        .badge-ai { background: #EFF6FF; color: #2563EB; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 99px; border: 1px solid #BFDBFE; }
        .logo-text p { font-size: 11px; color: #64748B; }

        .header-right { display: flex; align-items: center; gap: 12px; }
        .lang-switch { display: flex; background: #F1F5F9; padding: 2px; border-radius: 10px; border: 1px solid #E2E8F0; }
        .lang-btn { background: none; border: none; padding: 6px 12px; font-size: 12px; font-weight: 600; cursor: pointer; border-radius: 8px; color: #475569; transition: all 0.2s; }
        .lang-btn.active { background: #2563EB; color: white; box-shadow: 0 2px 6px rgba(37, 99, 235, 0.2); }

        .status-badge { display: flex; align-items: center; gap: 8px; background: #F1F5F9; padding: 6px 14px; border-radius: 99px; border: 1px solid #E2E8F0; font-size: 12px; color: #475569; }
        .status-dot { width: 8px; height: 8px; background: #10B981; border-radius: 50%; box-shadow: 0 0 8px #10B981; }

        /* Layout */
        main { max-width: 1200px; width: 100%; margin: 0 auto; padding: 24px 20px; display: grid; grid-template-columns: 1fr 1.4fr; gap: 24px; flex: 1; }
        @media(max-width: 900px) { main { grid-template-columns: 1fr; } }

        /* Cards & Panels */
        .panel { background: white; border: 1px solid #E2E8F0; border-radius: 16px; padding: 24px; box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.04); }
        .panel-title { font-size: 15px; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
        .panel-desc { font-size: 12px; color: #64748B; margin-bottom: 20px; line-height: 1.4; }

        /* Form elements */
        .form-group { margin-bottom: 16px; }
        label { display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #475569; margin-bottom: 6px; letter-spacing: 0.5px; }
        textarea { width: 100%; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 12px; padding: 12px; font-size: 14px; color: #1E293B; resize: none; outline: none; transition: all 0.2s; }
        textarea:focus { border-color: #2563EB; background: white; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }

        .file-upload-box { border: 2px dashed #CBD5E1; border-radius: 12px; padding: 16px; text-align: center; cursor: pointer; background: #F8FAFC; transition: all 0.2s; }
        .file-upload-box:hover { border-color: #2563EB; background: #F0F6FF; }
        .file-upload-box i { font-size: 20px; color: #64748B; margin-bottom: 6px; }
        .file-upload-box span { display: block; font-size: 12px; font-weight: 500; color: #334155; }
        .file-upload-box small { font-size: 10px; color: #94A3B8; }
        
        .preview-container { margin-top: 10px; position: relative; border-radius: 10px; overflow: hidden; height: 120px; border: 1px solid #CBD5E1; display: none; }
        .preview-container img { width: 100%; height: 100%; object-fit: cover; }
        .remove-img { position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,0.7); color: white; border: none; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 12px; }

        .btn-submit { width: 100%; background: #2563EB; color: white; border: none; border-radius: 12px; padding: 14px; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.2s, transform 0.1s; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); display: flex; align-items: center; justify-content: center; gap: 8px; }
        .btn-submit:hover { background: #1D4ED8; }
        .btn-submit:active { transform: scale(0.99); }

        /* Feed section */
        .feed-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .btn-refresh { background: #F1F5F9; border: 1px solid #CBD5E1; padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; color: #475569; cursor: pointer; display: flex; align-items: center; gap: 6px; transition: background 0.2s; }
        .btn-refresh:hover { background: #E2E8F0; }

        .report-card { background: white; border: 1px solid #E2E8F0; border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.02); transition: transform 0.2s; }
        .report-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.04); }
        .card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .category-tag { background: #F1F5F9; border: 1px solid #CBD5E1; padding: 4px 10px; border-radius: 8px; font-size: 11px; font-weight: 600; color: #334155; display: flex; align-items: center; gap: 6px; }
        .urgency-tag { padding: 4px 10px; border-radius: 8px; font-size: 11px; font-weight: 600; border: 1px solid; }
        .urgency-high { background: #FEF2F2; color: #DC2626; border-color: #FECACA; }
        .urgency-mid { background: #FFFBEB; color: #D97706; border-color: #FDE68A; }
        .urgency-low { background: #ECFDF5; color: #059669; border-color: #A7F3D0; }

        .report-desc { font-size: 13px; color: #334155; line-height: 1.5; margin-bottom: 12px; }
        .report-img { border-radius: 10px; overflow: hidden; max-height: 200px; margin-bottom: 12px; border: 1px solid #E2E8F0; }
        .report-img img { width: 100%; height: 100%; object-fit: cover; }

        .ai-box { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px; margin-bottom: 12px; }
        .ai-title { font-size: 11px; font-weight: 700; color: #0D9488; display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
        .ai-text { font-size: 12px; color: #475569; line-height: 1.4; }

        .card-footer { display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #94A3B8; border-top: 1px solid #F1F5F9; padding-top: 10px; }
        
        footer { text-align: center; padding: 20px; font-size: 11px; color: #94A3B8; border-top: 1px solid #E2E8F0; background: white; }
    </style>
</head>
<body>

    <header>
        <div class="header-container">
            <div class="logo-box">
                <div class="logo-icon"><i class="fa-solid fa-city"></i></div>
                <div class="logo-text">
                    <h1>Astana Smart iKomek <span class="badge-ai">AI Powered</span></h1>
                    <p data-i18n="subtitle">Система интеллектуального реагирования</p>
                </div>
            </div>
            <div class="header-right">
                <div class="lang-switch">
                    <button onclick="setLang('ru')" id="lang-ru" class="lang-btn active">RU</button>
                    <button onclick="setLang('kz')" id="lang-kz" class="lang-btn">KZ</button>
                </div>
                <div class="status-badge hidden-mobile">
                    <span class="status-dot"></span>
                    <span>DeepSeek AI: <strong data-i18n="statusOnline">Активен</strong></span>
                </div>
            </div>
        </div>
    </header>

    <main>
        <!-- Форма -->
        <div>
            <div class="panel">
                <div class="panel-title">
                    <i class="fa-solid fa-paper-plane" style="color: #2563EB;"></i>
                    <span data-i18n="formTitle">Подать новое обращение</span>
                </div>
                <div class="panel-desc" data-i18n="formDesc">Опишите проблему, ИИ классифицирует и направит её нужным городским службам.</div>

                <form id="reportForm">
                    <div class="form-group">
                        <label data-i18n="labelDesc">Описание инцидента</label>
                        <textarea id="description" required rows="4" data-i18n-placeholder="placeholderDesc" placeholder="Например: Возле ТРЦ Хан Шатыр открыт люк на тротуаре..."></textarea>
                    </div>

                    <div class="form-group">
                        <label data-i18n="labelPhoto">Прикрепить фото</label>
                        <input type="file" id="fileInput" accept="image/*" style="display:none;" onchange="previewImage(event)">
                        <label for="fileInput" class="file-upload-box">
                            <i class="fa-solid fa-cloud-arrow-up"></i>
                            <span id="fileLabel" data-i18n="fileChoose">Выберите фотографию</span>
                            <small>PNG, JPG до 10MB</small>
                        </label>
                        <div id="imagePreviewContainer" class="preview-container">
                            <img id="imagePreview">
                            <button type="button" class="remove-img" onclick="removeImage()"><i class="fa-solid fa-xmark"></i></button>
                        </div>
                    </div>

                    <button type="submit" id="submitBtn" class="btn-submit">
                        <i class="fa-solid fa-wand-magic-sparkles"></i>
                        <span data-i18n="submitBtn">Отправить в Акимат</span>
                    </button>
                </form>
            </div>
        </div>

        <!-- Лента -->
        <div>
            <div class="panel" style="margin-bottom: 16px; padding: 16px 24px;">
                <div class="feed-header" style="margin-bottom: 0;">
                    <div>
                        <div class="panel-title" style="margin-bottom: 2px;"><i class="fa-solid fa-list-check" style="color: #0D9488;"></i> <span data-i18n="feedTitle">Мониторинг инцидентов</span></div>
                        <div style="font-size: 11px; color: #64748B;" data-i18n="feedSub">Живой поток обращений жителей</div>
                    </div>
                    <button onclick="loadReports()" class="btn-refresh">
                        <i class="fa-solid fa-rotate-right" id="refreshIcon"></i>
                        <span data-i18n="refreshBtn">Обновить</span>
                    </button>
                </div>
            </div>

            <div id="reportsList"></div>
        </div>
    </main>

    <footer>
        Astana IT University — Build with AI Hackathon 2026
    </footer>

    <script>
        const API_URL = "";

        const translations = {
            ru: {
                subtitle: "Система интеллектуального реагирования",
                statusOnline: "Активен",
                formTitle: "Подать новое обращение",
                formDesc: "Опишите проблему, ИИ классифицирует и направит её нужным городским службам.",
                labelDesc: "Описание инцидента",
                placeholderDesc: "Например: Возле ТРЦ Хан Шатыр открыт люк на тротуаре...",
                labelPhoto: "Прикрепить фото",
                fileChoose: "Выберите фотографию",
                submitBtn: "Отправить в Акимат",
                submitLoading: "Анализ ИИ...",
                feedTitle: "Мониторинг инцидентов",
                feedSub: "Живой поток обращений жителей",
                refreshBtn: "Обновить",
                emptyTitle: "Заявок пока нет",
                emptyDesc: "Отправьте первое обращение в Акимат.",
                aiAnalysis: "Анализ DeepSeek AI:",
                priority: "Приоритет:",
                status: "Статус:",
                errorLoad: "Ошибка загрузки данных. Проверьте подключение к серверу.",
                errorSubmit: "Ошибка при отправке!"
            },
            kz: {
                subtitle: "Зияткерлік ден қою жүйесі",
                statusOnline: "Белсенді",
                formTitle: "Жаңа өтінім беру",
                formDesc: "Мәселені сипаттаңыз, ЖИ оны жіктеп, қалалық қызметтерге жібереді.",
                labelDesc: "Оқиға сипаттамасы",
                placeholderDesc: "Мысалы: Хан Шатыр СОО жанында люк ашық тұр...",
                labelPhoto: "Сурет тіркеу",
                fileChoose: "Фотосуретті таңдаңыз",
                submitBtn: "Әкімдікке жіберу",
                submitLoading: "ЖИ талдауда...",
                feedTitle: "Оқиғалар мониторингі",
                feedSub: "Тұрғындардың өтініштері",
                refreshBtn: "Жаңарту",
                emptyTitle: "Әзірге өтінімдер жоқ",
                emptyDesc: "Әкімдікке бірінші болып өтінім жіберіңіз.",
                aiAnalysis: "DeepSeek AI талдауы:",
                priority: "Басымдық:",
                status: "Күйі:",
                errorLoad: "Деректерді жүктеу қатесі. Сервер байланысын тексеріңіз.",
                errorSubmit: "Жіберу кезінде қате орын алды!"
            }
        };

        let currentLang = localStorage.getItem('ikomek_lang') || 'ru';

        function setLang(lang) {
            currentLang = lang;
            localStorage.setItem('ikomek_lang', lang);
            
            document.getElementById('lang-ru').className = lang === 'ru' ? "lang-btn active" : "lang-btn";
            document.getElementById('lang-kz').className = lang === 'kz' ? "lang-btn active" : "lang-btn";

            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (translations[lang][key]) el.textContent = translations[lang][key];
            });

            document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
                const key = el.getAttribute('data-i18n-placeholder');
                if (translations[lang][key]) el.placeholder = translations[lang][key];
            });

            loadReports();
        }

        const categoryIcons = {
            'ЖКХ': 'fa-solid fa-house-chimney-crack',
            'Дороги': 'fa-solid fa-road',
            'Благоустройство': 'fa-solid fa-tree',
            'Безопасность': 'fa-solid fa-shield-halved',
            'Общее': 'fa-solid fa-circle-info'
        };

        function previewImage(event) {
            const input = event.target;
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('imagePreview').src = e.target.result;
                    document.getElementById('imagePreviewContainer').style.display = 'block';
                    document.getElementById('fileLabel').textContent = input.files[0].name;
                }
                reader.readAsDataURL(input.files[0]);
            }
        }

        function removeImage() {
            document.getElementById('fileInput').value = '';
            document.getElementById('imagePreviewContainer').style.display = 'none';
            document.getElementById('fileLabel').textContent = translations[currentLang].fileChoose;
        }

        async function loadReports() {
            const container = document.getElementById('reportsList');
            const refreshIcon = document.getElementById('refreshIcon');
            refreshIcon.style.animation = 'spin 1s linear infinite';

            try {
                const res = await fetch(`${API_URL}/api/reports`);
                const reports = await res.json();
                const t = translations[currentLang];
                
                if (!reports || reports.length === 0) {
                    container.innerHTML = `
                        <div class="panel" style="text-align: center; padding: 40px;">
                            <i class="fa-regular fa-folder-open" style="font-size: 28px; color: #94A3B8; margin-bottom: 8px;"></i>
                            <p style="font-size: 13px; font-weight: 600; color: #334155;">${t.emptyTitle}</p>
                            <p style="font-size: 11px; color: #94A3B8; margin-top: 4px;">${t.emptyDesc}</p>
                        </div>`;
                    return;
                }

                container.innerHTML = reports.map((r) => {
                    const iconClass = categoryIcons[r.category] || categoryIcons['Общее'];
                    let urgencyClass = 'urgency-mid';
                    if (r.urgency === 'Высокий') urgencyClass = 'urgency-high';
                    if (r.urgency === 'Низкий') urgencyClass = 'urgency-low';

                    return `
                        <div class="report-card">
                            <div class="card-top">
                                <div class="category-tag">
                                    <i class="${iconClass}"></i>
                                    <span>${r.category || 'Общее'}</span>
                                </div>
                                <span class="urgency-tag ${urgencyClass}">
                                    ${t.priority} ${r.urgency || 'Средний'}
                                </span>
                            </div>

                            <p class="report-desc">${r.description}</p>

                            ${r.image_url ? `
                                <div class="report-img">
                                    <img src="${r.image_url}">
                                </div>
                            ` : ''}

                            <div class="ai-box">
                                <div class="ai-title">
                                    <i class="fa-solid fa-microchip"></i>
                                    <span>${t.aiAnalysis}</span>
                                </div>
                                <div class="ai-text">${r.ai_summary}</div>
                            </div>

                            <div class="card-footer">
                                <span>${t.status} <strong>${r.status || 'Новая'}</strong></span>
                                <span>${r.created_at ? new Date(r.created_at).toLocaleString(currentLang === 'kz' ? 'kk-KZ' : 'ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}</span>
                            </div>
                        </div>
                    `;
                }).join('');

            } catch (err) {
                const t = translations[currentLang];
                container.innerHTML = `<div style="background:#FEF2F2; color:#DC2626; border:1px solid #FECACA; padding:12px; border-radius:10px; font-size:12px; text-align:center;">${t.errorLoad}</div>`;
            } finally {
                refreshIcon.style.animation = 'none';
            }
        }

        document.getElementById('reportForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('submitBtn');
            const t = translations[currentLang];
            const formData = new FormData();
            
            formData.append('description', document.getElementById('description').value);
            const fileInput = document.getElementById('fileInput').files[0];
            if (fileInput) formData.append('file', fileInput);

            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-spinner" style="animation: spin 1s linear infinite;"></i> <span>${t.submitLoading}</span>`;

            try {
                await fetch(`${API_URL}/api/report`, { method: 'POST', body: formData });
                document.getElementById('reportForm').reset();
                removeImage();
                await loadReports();
            } catch (err) {
                alert(t.errorSubmit);
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> <span>${t.submitBtn}</span>`;
            }
        });

        const styleSheet = document.createElement("style");
        styleSheet.type = "text/css";
        styleSheet.innerText = "@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }";
        document.head.appendChild(styleSheet);

        setLang(currentLang);
    </script>
</body>
</html>
"""


@app.post("/api/report")
async def create_report(
    description: str = Form(...),
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
        "status": "Новая"
    }

    try:
        db_response = supabase.table("incidents").insert(data).execute()
        return {"success": True, "data": db_response.data}
    except Exception as e:
        print("DB Insert Error:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports")
def get_reports():
    if not supabase:
        return []
    try:
        # Безопасный запрос без сортировки по дате, чтобы избежать ошибок структуры таблицы
        response = supabase.table("incidents").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print("DB Fetch Error:", e)
        return []
