import json
import os
import urllib.request
import urllib.error
import re

def humanize_text(text: str) -> str:
    '''Пост-процессинг: заменяет AI-фразы на человечные'''
    
    ai_phrases = {
        r'\bв современном мире\b': 'сейчас',
        r'\bв настоящее время\b': 'сегодня',
        r'\bважно отметить,? что\b': '',
        r'\bследует отметить,? что\b': '',
        r'\bнеобходимо подчеркнуть\b': 'стоит сказать',
        r'\bнемаловажно отметить\b': 'также',
        r'\bданный\b': 'этот',
        r'\bданная\b': 'эта',
        r'\bданное\b': 'это',
        r'\bданные\b': 'эти',
        r'\bявляется\b': 'есть',
        r'\bпредставляет собой\b': 'это',
        r'\bосуществляется\b': 'происходит',
        r'\bпозволяет\b': 'дает возможность',
        r'\bв заключение\b': 'подводя итог',
        r'\bтаким образом,?\b': 'итак,',
        r'\bследовательно,?\b': 'значит,',
        r'\bкак показывает практика\b': 'на практике',
        r'\bв рамках\b': 'в',
    }
    
    result = text
    for pattern, replacement in ai_phrases.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'\s+([.,;:!?])', r'\1', result)
    
    return result.strip()

def check_content_quality(text: str, api_key: str, proxy_url: str = None) -> dict:
    '''Проверяет качество текста через Gemini'''
    prompt = f"""Проанализируй текст по двум критериям:

ТЕКСТ:
{text[:3000]}

ЗАДАЧИ:
1. AI-детекция: Оцени от 0 до 100, насколько текст похож на сгенерированный ИИ
2. Уникальность формулировок: Оцени от 0 до 100, насколько оригинальны формулировки

ВЕРНИ СТРОГО JSON:
{{
  "ai_score": <число 0-100>,
  "uniqueness_score": <число 0-100>
}}

ВАЖНО: Отвечай ТОЛЬКО JSON!"""

    gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}'
    
    gemini_request = {
        'contents': [{
            'parts': [{'text': prompt}]
        }]
    }
    
    req = urllib.request.Request(
        gemini_url,
        data=json.dumps(gemini_request).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    if proxy_url:
        proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)
    
    with urllib.request.urlopen(req, timeout=30) as response:
        gemini_response = json.loads(response.read().decode('utf-8'))
    
    if 'candidates' in gemini_response and gemini_response['candidates']:
        result_text = gemini_response['candidates'][0]['content']['parts'][0]['text'].strip()
        
        if result_text.startswith('```'):
            lines = result_text.split('\n')
            result_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else result_text
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        return json.loads(result_text)
    
    return {'ai_score': 50, 'uniqueness_score': 50}

def improve_text_prompt(original_prompt: str, iteration: int, quality_level: str) -> str:
    '''Радикально меняет промпт для каждой итерации'''
    
    if iteration == 1:
        return original_prompt
    
    strategies = [
        """
НОВЫЙ ПОДХОД: Забудь про академичность. Пиши как студент, который реально разбирается в теме.

- Используй простые слова вместо сложных терминов где можно
- Объясняй сложное через простое
- Добавь примеры из жизни
- Пиши короткими и длинными предложениями вперемешку
- Используй "это", "есть", "делает" вместо "представляет собой", "является", "осуществляет"
- НЕ используй: "в современном мире", "важно отметить", "следует подчеркнуть"
""",
        """
КРИТИЧНО: ПОЛНОСТЬЮ переосмысли тему. НЕ копируй предыдущий текст!

- Начни с другой мысли
- Используй ДРУГИЕ аргументы и примеры
- Другая структура изложения
- Пиши как будто объясняешь другу, который в теме
- Добавь неожиданные сравнения
- Используй активный залог: "AI помогает", а не "с помощью AI осуществляется помощь"
""",
        """
МАКСИМАЛЬНАЯ ЕСТЕСТВЕННОСТЬ:

- Пиши живым языком, добавь эмоции
- Используй разговорные обороты (но не сленг)
- Вставь риторические вопросы
- Делай паузы в тексте (короткие предложения)
- Пиши так, как будто ты автор, который лично исследовал тему
- Добавь личные наблюдения: "интересно, что...", "на практике видно..."
""",
        """
ФИНАЛЬНАЯ ПОПЫТКА - АБСОЛЮТНАЯ УНИКАЛЬНОСТЬ:

- Придумай СВОИ формулировки для всех идей
- Используй метафоры и образы
- Пиши нелинейно: начни с неожиданного факта
- Добавь конкретные цифры и даты (можешь условные)
- Используй прямую речь или цитаты
- Пиши так, чтобы никто не догадался, что это AI
- Будь смелее в формулировках
"""
    ]
    
    strategy_text = strategies[min(iteration - 2, len(strategies) - 1)]
    
    return f"{original_prompt}\n\n{'='*50}\n{strategy_text}\n{'='*50}\n\nТеперь напиши текст полностью по-новому с этим подходом!"

def generate_with_gemini(prompt: str, api_key: str, proxy_url: str = None) -> str:
    '''Генерирует текст через Gemini API'''
    gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}'
    
    gemini_request = {
        'contents': [{
            'parts': [{'text': prompt}]
        }]
    }
    
    req = urllib.request.Request(
        gemini_url,
        data=json.dumps(gemini_request).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    if proxy_url:
        proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
        opener = urllib.request.build_opener(proxy_handler)
        urllib.request.install_opener(opener)
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            gemini_response = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        raise Exception(f'Ошибка API: {str(e)}')
    
    if 'candidates' in gemini_response and gemini_response['candidates']:
        return gemini_response['candidates'][0]['content']['parts'][0]['text'].strip()
    
    raise Exception('Не удалось сгенерировать текст')

def handler(event: dict, context) -> dict:
    '''Генерирует структуру или полный документ с автопроверкой качества через Gemini API'''
    
    method = event.get('httpMethod', 'POST')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '86400'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'}),
            'isBase64Encoded': False
        }
    
    try:
        body = json.loads(event.get('body', '{}'))
        mode = body.get('mode', 'document')
        doc_type = body.get('docType', 'реферат')
        subject = body.get('subject', '')
        pages = body.get('pages', 10)
        topics = body.get('topics', [])
        additional_info = body.get('additionalInfo', '')
        section_title = body.get('sectionTitle', '')
        section_description = body.get('sectionDescription', '')
        quality_level = body.get('qualityLevel', 'high')
        
        if not subject:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указана тема документа'}),
                'isBase64Encoded': False
            }
        
        if mode == 'section' and not section_title:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указан раздел'}),
                'isBase64Encoded': False
            }
        
        api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')
        
        if not api_key:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'API ключ не настроен'}),
                'isBase64Encoded': False
            }
        
        quality_settings = {
            'standard': {'max_attempts': 3, 'ai_threshold': 70, 'uniqueness_threshold': 40},
            'high': {'max_attempts': 4, 'ai_threshold': 50, 'uniqueness_threshold': 70},
            'max': {'max_attempts': 5, 'ai_threshold': 40, 'uniqueness_threshold': 75}
        }
        
        settings = quality_settings.get(quality_level, quality_settings['high'])
        
        if mode == 'topics':
            sections_count = max(3, pages // 3)
            prompt = f"""Создай структуру для документа типа "{doc_type}" на тему: {subject}

Документ должен быть объемом примерно {pages} страниц А4.

{f'Дополнительные требования: {additional_info}' if additional_info else ''}

Верни ТОЛЬКО валидный JSON массив из {sections_count} объектов:
[
  {{
    "title": "Название раздела",
    "description": "Краткое описание содержания раздела"
  }}
]

Без введения/заключения - только основные разделы.
Названия лаконичные и конкретные. Описания информативные (2-3 предложения).

ВАЖНО: Верни ТОЛЬКО JSON, без дополнительного текста, markdown или комментариев!"""

            result_text = generate_with_gemini(prompt, api_key, proxy_url)
            
            if result_text.startswith('```'):
                lines = result_text.split('\n')
                result_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else result_text
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            topics_result = json.loads(result_text)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'topics': topics_result}, ensure_ascii=False),
                'isBase64Encoded': False
            }
            
        elif mode == 'section':
            words_per_page = 300
            total_words_needed = pages * words_per_page
            sections_count = len(topics) if topics else 5
            words_for_intro_conclusion = 400
            words_for_sections = total_words_needed - words_for_intro_conclusion
            words_per_section = words_for_sections // sections_count if sections_count > 0 else 500
            
            target_words = words_per_section
            if 'введение' in section_title.lower() or 'заключение' in section_title.lower():
                target_words = 200
            
            base_prompt = f"""Ты студент, который пишет {doc_type} на тему: {subject}

РАЗДЕЛ: {section_title}
О ЧЕМ ПИСАТЬ: {section_description}

ТРЕБОВАНИЯ К ОБЪЕМУ:
- Ровно {target_words} слов (не меньше!)

КАК ПИСАТЬ (КРИТИЧНО ВАЖНО):
1. Пиши ПРОСТЫМ языком, как объясняешь другу
2. КОРОТКИЕ и ДЛИННЫЕ предложения вперемешку
3. Используй АКТИВНЫЙ залог: "AI помогает", а не "помощь осуществляется"
4. Приводи КОНКРЕТНЫЕ примеры, цифры, факты
5. НЕ используй штампы:
   ❌ "в современном мире"
   ❌ "важно отметить"
   ❌ "следует подчеркнуть"
   ❌ "представляет собой"
   ❌ "осуществляется"
   ✅ Вместо них: "сейчас", "интересно", "это", "происходит"

6. Начни с КОНКРЕТНОГО факта или примера, а не с общих слов
7. Добавь ЛИЧНЫЕ наблюдения: "на практике видно...", "интересно, что..."
8. Используй риторические вопросы иногда
9. Пиши так, чтобы было интересно читать

{f'ДОПОЛНИТЕЛЬНО: {additional_info}' if additional_info else ''}

ВАЖНО: 
- Текст должен звучать как написал человек, а не робот
- {target_words} слов - строго!
- Напиши ТОЛЬКО текст раздела без заголовка"""

            max_attempts = settings['max_attempts']
            best_text = None
            best_scores = {'ai_score': 100, 'uniqueness_score': 0}
            
            for attempt in range(1, max_attempts + 1):
                prompt = improve_text_prompt(base_prompt, attempt, quality_level)
                result_text = generate_with_gemini(prompt, api_key, proxy_url)
                result_text = humanize_text(result_text)
                
                try:
                    scores = check_content_quality(result_text, api_key, proxy_url)
                    ai_score = scores.get('ai_score', 50)
                    uniqueness_score = scores.get('uniqueness_score', 50)
                    
                    if ai_score < best_scores['ai_score'] or uniqueness_score > best_scores['uniqueness_score']:
                        best_text = result_text
                        best_scores = {'ai_score': ai_score, 'uniqueness_score': uniqueness_score}
                    
                    if ai_score < settings['ai_threshold'] and uniqueness_score > settings['uniqueness_threshold']:
                        return {
                            'statusCode': 200,
                            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                            'body': json.dumps({
                                'text': result_text,
                                'quality': {
                                    'ai_score': ai_score,
                                    'uniqueness_score': uniqueness_score,
                                    'attempts': attempt,
                                    'passed': True
                                }
                            }, ensure_ascii=False),
                            'isBase64Encoded': False
                        }
                except Exception:
                    if best_text is None:
                        best_text = result_text
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'text': best_text,
                    'quality': {
                        'ai_score': best_scores['ai_score'],
                        'uniqueness_score': best_scores['uniqueness_score'],
                        'attempts': max_attempts,
                        'passed': False
                    }
                }, ensure_ascii=False),
                'isBase64Encoded': False
            }
            
        else:
            topics_structure = '\n'.join([
                f"{i+1}. {topic['title']}\n   {topic['description']}"
                for i, topic in enumerate(topics)
            ])
            
            words_per_page = 300
            target_words = pages * words_per_page
            
            prompt = f"""Напиши {doc_type} на тему: {subject}

СТРУКТУРА ({len(topics)} разделов):
{topics_structure}

ОБЪЕМ: {target_words} слов (~{pages} страниц A4)
Это примерно {target_words // len(topics)} слов на каждый раздел.

СТИЛЬ:
- Пиши как хороший студент, который ПОНИМАЕТ тему
- Объясняй простым языком, как другу
- Используй примеры, факты, цифры
- Чередуй короткие и длинные предложения
- Пиши активным залогом: "AI помогает", а не "помощь осуществляется"

ЗАПРЕЩЕНО использовать:
❌ "в современном мире" ❌ "важно отметить" ❌ "представляет собой"
❌ "осуществляется" ❌ "в настоящее время" ❌ "данный"
❌ "является" ❌ "позволяет" ❌ "необходимо подчеркнуть"

ВМЕСТО ЭТОГО:
✅ Конкретика: "в 2024 году", "по данным исследований"
✅ Живые фразы: "интересно, что...", "на практике...", "важный момент:"
✅ Короткие слова: "этот", "есть", "дает", "сегодня"

{f'Дополнительно: {additional_info}' if additional_info else ''}

ФОРМАТ:

ВВЕДЕНИЕ
[2-3 абзаца, ~{target_words // len(topics) // 2} слов]

1. [Название раздела]
[Подробный текст, ~{target_words // len(topics)} слов]

2. [Название раздела]
[Подробный текст, ~{target_words // len(topics)} слов]

...

ЗАКЛЮЧЕНИЕ
[2-3 абзаца, ~{target_words // len(topics) // 2} слов]

⚠️ КРИТИЧНО: Пиши ПОЛНЫЙ объем {target_words} слов! Не сокращай!"""

            result_text = generate_with_gemini(prompt, api_key, proxy_url)
            result_text = humanize_text(result_text)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'document': result_text}, ensure_ascii=False),
                'isBase64Encoded': False
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
