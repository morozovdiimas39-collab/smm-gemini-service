import json
import os
import urllib.request
import urllib.error

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
    '''Создает улучшенный промпт для перегенерации с учетом уровня качества'''
    
    base_improvements = {
        'standard': [
            "Перепиши текст более естественно, избегая шаблонных фраз.",
            "Добавь разнообразия в конструкции предложений.",
            "Используй более живой язык."
        ],
        'high': [
            "Перепиши текст значительно более естественно, избегая любых AI-паттернов. Добавь конкретные примеры.",
            "Сделай текст более человечным: используй разнообразные конструкции, избегай повторов, добавь индивидуальности.",
            "Полностью переформулируй с оригинальными выражениями. Пиши как эксперт в теме.",
            "Используй неожиданные сравнения и метафоры. Добавь больше деталей и нюансов.",
            "Пиши максимально естественно, как будто это пишет увлеченный темой человек."
        ],
        'max': [
            "КРИТИЧНО: Текст должен быть полностью оригинальным и естественным. Избегай ЛЮБЫХ шаблонов AI. Пиши уникально!",
            "Переосмысли тему полностью. Используй неожиданные подходы, свежие аргументы, оригинальные примеры.",
            "Пиши как настоящий эксперт с личным опытом. Добавь неформальности, живости, индивидуального стиля.",
            "Максимальная оригинальность: избегай клише, используй редкие обороты, придумай свои формулировки.",
            "Финальная версия: абсолютная естественность, как будто текст писал человек несколько часов."
        ]
    }
    
    improvements = base_improvements.get(quality_level, base_improvements['high'])
    improvement_text = improvements[min(iteration - 1, len(improvements) - 1)]
    
    return f"{original_prompt}\n\nКРИТИЧНО ВАЖНО: {improvement_text}"

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
        with urllib.request.urlopen(req, timeout=20) as response:
            gemini_response = json.loads(response.read().decode('utf-8'))
    except Exception:
        raise Exception('Слишком большой документ. Уменьшите количество страниц до 10-15')
    
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
        
        # Настройки по уровню качества
        quality_settings = {
            'standard': {'max_attempts': 3, 'ai_threshold': 70, 'uniqueness_threshold': 40},
            'high': {'max_attempts': 4, 'ai_threshold': 50, 'uniqueness_threshold': 70},
            'max': {'max_attempts': 5, 'ai_threshold': 30, 'uniqueness_threshold': 80}
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
            
            # Улучшенный базовый промпт с инструкциями для естественности
            base_prompt = f"""Напиши раздел для академического документа ({doc_type}) на тему: {subject}

РАЗДЕЛ: {section_title}
ОПИСАНИЕ: {section_description}

КРИТИЧНЫЕ ТРЕБОВАНИЯ К СОДЕРЖАНИЮ:
- Объем: СТРОГО {target_words} слов (это обязательно!)
- Академический стиль, научная терминология
- Логичное изложение с примерами и деталями
- Раскрывай тему МАКСИМАЛЬНО подробно
- Используй абзацы для структуры
- Приводи конкретные примеры и факты
- Пиши развернуто, не сокращай

КРИТИЧНЫЕ ТРЕБОВАНИЯ К СТИЛЮ (для прохождения AI-детекции):
- ИЗБЕГАЙ шаблонных фраз типа "в современном мире", "в настоящее время", "важно отметить"
- Используй РАЗНООБРАЗНЫЕ конструкции предложений (не только сложноподчиненные)
- Добавляй КОНКРЕТИКУ: цифры, даты, имена, реальные примеры
- Пиши ЕСТЕСТВЕННО, как пишет увлеченный темой человек
- НЕ повторяй одинаковые речевые обороты
- Используй неожиданные сравнения и метафоры где уместно
- Варьируй длину предложений (короткие и длинные)
- Добавь индивидуальности: личные наблюдения, интересные детали

{f'Дополнительные требования: {additional_info}' if additional_info else ''}

ВАЖНО: Текст должен быть РОВНО {target_words} слов! Не меньше!
Напиши ТОЛЬКО текст раздела, без заголовка раздела."""

            # Генерация с автопроверкой
            max_attempts = settings['max_attempts']
            best_text = None
            best_scores = {'ai_score': 100, 'uniqueness_score': 0}
            
            for attempt in range(1, max_attempts + 1):
                prompt = improve_text_prompt(base_prompt, attempt, quality_level) if attempt > 1 else base_prompt
                result_text = generate_with_gemini(prompt, api_key, proxy_url)
                
                # Проверяем качество
                try:
                    scores = check_content_quality(result_text, api_key, proxy_url)
                    ai_score = scores.get('ai_score', 50)
                    uniqueness_score = scores.get('uniqueness_score', 50)
                    
                    # Сохраняем лучший результат
                    if ai_score < best_scores['ai_score'] or uniqueness_score > best_scores['uniqueness_score']:
                        best_text = result_text
                        best_scores = {'ai_score': ai_score, 'uniqueness_score': uniqueness_score}
                    
                    # Проверяем по порогам уровня качества
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
            
            # Возвращаем лучший результат
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
            
            chars_per_page = 1800
            target_chars = pages * chars_per_page
            chars_per_section = target_chars // len(topics)
            
            words_per_page = 300
            target_words = pages * words_per_page
            words_per_section = target_words // len(topics)
            
            words_limit = min(target_words, 2000)
            
            prompt = f"""Напиши академический {doc_type} на тему: {subject}

СТРУКТУРА ДОКУМЕНТА:
{topics_structure}

ТРЕБОВАНИЯ:
- Объем: МАКСИМУМ {words_limit} слов (это критично!)
- Академический стиль, научная терминология
- Логичное изложение с ключевыми моментами
- НЕ нужно оглавление, список литературы или титульный лист
- Начинай сразу с введения

{f'Дополнительные требования: {additional_info}' if additional_info else ''}

Формат ответа:
ВВЕДЕНИЕ
[2 абзаца]

1. [Название первого раздела]
[основной текст]

2. [Название второго раздела]
[основной текст]

...

ЗАКЛЮЧЕНИЕ
[2 абзаца]

КРИТИЧНО: Уложись в {words_limit} слов! Пиши только главное."""

            result_text = generate_with_gemini(prompt, api_key, proxy_url)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'document': result_text}, ensure_ascii=False),
                'isBase64Encoded': False
            }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Некорректный JSON'}),
            'isBase64Encoded': False
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
