import os
import json
import requests
from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Красивый фронтенд с поддержкой RU/KZ и Light Glassmorphism стилем"""
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Astana Smart City — iKomek AI Portal</title>
    <!-- Tailwind CSS -->
    <script src="[https://cdn.tailwindcss.com](https://cdn.tailwindcss.com)"></script>
    <!-- FontAwesome Icons -->
    <link href="[https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css](https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css)" rel="stylesheet">
    <!-- Google Fonts -->
    <link href="[https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap](https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap)" rel="stylesheet">

    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Inter', 'sans-serif'] },
                    colors: {
                        brand: {
                            50: '#F0F6FF',
                            100: '#E0EDFE',
                            500: '#3B82F6',
                            600: '#2563EB',
                            900: '#1E3A8A',
                        }
                    }
                }
            }
        }
    </script>

    <style>
        body {
            background-color: #F8FAFC;
            background-image: 
                radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.05) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(13, 148, 136, 0.05) 0px, transparent 50%);
        }
        .card-shadow {
            box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.02);
        }
        .card-shadow:hover {
            box-shadow: 0 10px 25px -3px rgba(37, 99, 235, 0.08), 0 4px 10px -2px rgba(15, 23, 42, 0.03);
            transform: translateY(-2px);
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .animate-fade {
            animation: fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #F8FAFC; }
        ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 9999px; }
        ::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
    </style>
</head>
<body class="text-slate-800 font-sans antialiased min-h-screen flex flex-col selection:bg-brand-500 selection:text-white">

    <!-- Header -->
    <header class="bg-white/85 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-brand-600 text-white flex items-center justify-center shadow-md shadow-brand-500/20">
                    <i class="fa-solid fa-city text-lg"></i>
                </div>
                <div>
                    <h1 class="font-bold text-base text-slate-900 tracking-tight flex items-center gap-2">
                        Astana Smart iKomek
                        <span class="bg-brand-50 text-brand-600 text-[11px] font-semibold px-2.5 py-0.5 rounded-full border border-brand-100">AI Powered</span>
                    </h1>
                    <p class="text-[11px] text-slate-500" data-i18n="subtitle">Система интеллектуального реагирования</p>
                </div>
            </div>

            <div class="flex items-center gap-3">
                <!-- Переключатель языка -->
                <div class="flex bg-slate-100 p-1 rounded-xl border border-slate-200 text-xs font-semibold">
                    <button onclick="setLang('ru')" id="lang-ru" class="px-3 py-1 rounded-lg transition bg-brand-600 text-white shadow-sm">RU</button>
                    <button onclick="setLang('kz')" id="lang-kz" class="px-3 py-1 rounded-lg transition text-slate-600 hover:text-slate-900">KZ</button>
                </div>

                <div class="hidden sm:flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-600">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>DeepSeek AI: <strong class="text-slate-900 font-medium" data-i18n="statusOnline">Активен</strong></span>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">

        <!-- Левая колонка: Форма подачи (5 колонок) -->
        <div class="lg:col-span-5">
            <div class="bg-white p-6 rounded-2xl border border-slate-200/80 card-shadow sticky top-24 space-y-5">
                <div>
                    <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
                        <i class="fa-solid fa-paper-plane text-brand-600 text-sm"></i>
                        <span data-i18n="formTitle">Подать новое обращение</span>
                    </h2>
                    <p class="text-xs text-slate-500 mt-1" data-i18n="formDesc">Опишите проблему, ИИ классифицирует и направит её нужным городским службам.</p>
                </div>

                <form id="reportForm" class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5" data-i18n="labelDesc">Описание инцидента</label>
                        <textarea id="description" required rows="4" 
                            class="w-full bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:bg-white focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 transition resize-none"
                            data-i18n-placeholder="placeholderDesc" placeholder="Например: Возле ТРЦ Хан Шатыр открыт люк на тротуаре..."></textarea>
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5" data-i18n="labelPhoto">Прикрепить фото</label>
                        <input type="file" id="fileInput" accept="image/*" class="hidden" onchange="previewImage(event)">
                        <label for="fileInput" 
                            class="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-200 hover:border-brand-500/50 rounded-xl cursor-pointer bg-slate-50/50 hover:bg-slate-50 transition text-center group">
                            <i class="fa-solid fa-cloud-arrow-up text-xl text-slate-400 group-hover:text-brand-600 transition-colors mb-1"></i>
                            <span class="text-xs text-slate-600 font-medium group-hover:text-slate-900" id="fileLabel" data-i18n="fileChoose">Выберите фотографию</span>
                            <span class="text-[10px] text-slate-400 mt-0.5">PNG, JPG до 10MB</span>
                        </label>
                        <div id="imagePreviewContainer" class="hidden mt-3 relative rounded-xl overflow-hidden border border-slate-200 h-32">
                            <img id="imagePreview" class="w-full h-full object-cover">
                            <button type="button" onclick="removeImage()" class="absolute top-2 right-2 bg-slate-900/70 hover:bg-rose-600 text-white p-1 rounded-full text-xs transition">
                                <i class="fa-solid fa-xmark w-4 h-4 flex items-center justify-center"></i>
                            </button>
                        </div>
                    </div>

                    <button type="submit" id="submitBtn" 
                        class="w-full bg-brand-600 hover:bg-brand-900 text-white font-semibold py-3 px-4 rounded-xl transition shadow-md shadow-brand-500/20 active:scale-[0.99] flex items-center justify-center gap-2 text-sm">
                        <i class="fa-solid fa-wand-magic-sparkles text-xs"></i>
                        <span data-i18n="submitBtn">Отправить в Акимат</span>
                    </button>
                </form>
            </div>
        </div>

        <!-- Правая колонка: Лента инцидентов (7 колонок) -->
        <div class="lg:col-span-7 space-y-5">
            <div class="flex items-center justify-between bg-white p-4 rounded-2xl border border-slate-200/80 card-shadow">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-teal-50 text-teal-600 border border-teal-100 flex items-center justify-center text-xs">
                        <i class="fa-solid fa-list-check"></i>
                    </div>
                    <div>
                        <h2 class="text-sm font-bold text-slate-900" data-i18n="feedTitle">Мониторинг инцидентов</h2>
                        <p class="text-xs text-slate-500" data-i18n="feedSub">Живой поток обращений жителей</p>
                    </div>
                </div>
                <button onclick="loadReports()" class="px-3 py-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-600 text-xs font-medium transition flex items-center gap-2 border border-slate-200">
                    <i class="fa-solid fa-rotate-right text-[10px]" id="refreshIcon"></i>
                    <span data-i18n="refreshBtn">Обновить</span>
                </button>
            </div>

            <div id="reportsList" class="space-y-4"></div>
        </div>

    </main>

    <!-- Footer -->
    <footer class="mt-auto bg-white border-t border-slate-200/80 py-5 text-center text-xs text-slate-500">
        Astana IT University — Build with AI Hackathon 2026
    </footer>

    <!-- Скрипты -->
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
            
            document.getElementById('lang-ru').className = lang === 'ru' 
                ? "px-3 py-1 rounded-lg transition bg-brand-600 text-white shadow-sm" 
                : "px-3 py-1 rounded-lg transition text-slate-600 hover:text-slate-900";
            
            document.getElementById('lang-kz').className = lang === 'kz' 
                ? "px-3 py-1 rounded-lg transition bg-brand-600 text-white shadow-sm" 
                : "px-3 py-1 rounded-lg transition text-slate-600 hover:text-slate-900";

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
            'ЖКХ': 'fa-solid fa-house-chimney-crack text-amber-500',
            'Дороги': 'fa-solid fa-road text-brand-600',
            'Благоустройство': 'fa-solid fa-tree text-teal-600',
            'Безопасность': 'fa-solid fa-shield-halved text-rose-500',
            'Общее': 'fa-solid fa-circle-info text-slate-500'
        };

        const urgencyStyles = {
            'Высокий': 'bg-rose-50 text-rose-600 border-rose-200',
            'Средний': 'bg-amber-50 text-amber-600 border-amber-200',
            'Низкий': 'bg-emerald-50 text-emerald-600 border-emerald-200'
        };

        function previewImage(event) {
            const input = event.target;
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('imagePreview').src = e.target.result;
                    document.getElementById('imagePreviewContainer').classList.remove('hidden');
                    document.getElementById('fileLabel').textContent = input.files[0].name;
                }
                reader.readAsDataURL(input.files[0]);
            }
        }

        function removeImage() {
            document.getElementById('fileInput').value = '';
            document.getElementById('imagePreviewContainer').classList.add('hidden');
            document.getElementById('fileLabel').textContent = translations[currentLang].fileChoose;
        }

        async function loadReports() {
            const container = document.getElementById('reportsList');
            const refreshIcon = document.getElementById('refreshIcon');
            refreshIcon.classList.add('fa-spin');

            try {
                const res = await fetch(`${API_URL}/api/reports`);
                const reports = await res.json();
                const t = translations[currentLang];
                
                if (!reports || reports.length === 0) {
                    container.innerHTML = `
                        <div class="bg-white p-10 rounded-2xl text-center space-y-2 border border-slate-200/80 card-shadow">
                            <i class="fa-regular fa-folder-open text-2xl text-slate-400"></i>
                            <p class="text-sm font-medium text-slate-700">${t.emptyTitle}</p>
                            <p class="text-xs text-slate-400">${t.emptyDesc}</p>
                        </div>`;
                    return;
                }

                container.innerHTML = reports.map((r) => {
                    const iconClass = categoryIcons[r.category] || categoryIcons['Общее'];
                    const urgencyClass = urgencyStyles[r.urgency] || urgencyStyles['Средний'];

                    return `
                        <div class="bg-white p-5 rounded-2xl border border-slate-200/80 card-shadow animate-fade space-y-3 transition-all duration-200">
                            <div class="flex items-center justify-between gap-3">
                                <div class="flex items-center gap-2 bg-slate-50 border border-slate-200/80 px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-700">
                                    <i class="${iconClass}"></i>
                                    <span>${r.category || 'Общее'}</span>
                                </div>
                                <span class="text-xs px-2.5 py-1 rounded-lg border font-semibold ${urgencyClass}">
                                    ${t.priority} ${r.urgency || 'Средний'}
                                </span>
                            </div>

                            <p class="text-sm text-slate-700 leading-relaxed">${r.description}</p>

                            ${r.image_url ? `
                                <div class="rounded-xl overflow-hidden border border-slate-200 max-h-60">
                                    <img src="${r.image_url}" class="w-full h-full object-cover">
                                </div>
                            ` : ''}

                            <div class="bg-slate-50 border border-slate-200/80 p-3.5 rounded-xl space-y-1">
                                <div class="flex items-center gap-1.5 text-xs font-semibold text-teal-700">
                                    <i class="fa-solid fa-microchip"></i>
                                    <span>${t.aiAnalysis}</span>
                                </div>
                                <p class="text-xs text-slate-600 leading-relaxed">${r.ai_summary}</p>
                            </div>

                            <div class="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-100">
                                <span>${t.status} <strong class="text-slate-600">${r.status || 'Новая'}</strong></span>
                                <span>${new Date(r.created_at).toLocaleString(currentLang === 'kz' ? 'kk-KZ' : 'ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
                            </div>
                        </div>
                    `;
                }).join('');

            } catch (err) {
                const t = translations[currentLang];
                container.innerHTML = `
                    <div class="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 text-xs text-center">
                        ${t.errorLoad}
                    </div>`;
            } finally {
                refreshIcon.classList.remove('fa-spin');
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
            btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin text-xs"></i> <span>${t.submitLoading}</span>`;

            try {
                await fetch(`${API_URL}/api/report`, { method: 'POST', body: formData });
                document.getElementById('reportForm').reset();
                removeImage();
                await loadReports();
            } catch (err) {
                alert(t.errorSubmit);
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-xs"></i> <span>${t.submitBtn}</span>`;
            }
        });

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
