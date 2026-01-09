import json
import os
import urllib.request
import urllib.error

def handler(event: dict, context) -> dict:
    '''Генерирует структуру или полный документ с помощью Gemini API'''
    
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
        
        if not subject:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указана тема документа'}),
                'isBase64Encoded': False
            }
        
        if mode == 'document' and (not topics or len(topics) == 0):
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не указана структура документа'}),
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
        else:
            topics_structure = '\n'.join([
                f"{i+1}. {topic['title']}\n   {topic['description']}"
                for i, topic in enumerate(topics)
            ])
            
            chars_per_page = 1800
            target_chars = pages * chars_per_page
            chars_per_section = target_chars // len(topics)
            
            prompt = f"""Напиши академический {doc_type} на тему: {subject}

СТРУКТУРА ДОКУМЕНТА:
{topics_structure}

ТРЕБОВАНИЯ:
- Общий объем: примерно {pages} страниц А4 (~{target_chars} символов)
- На каждый раздел: ~{chars_per_section} символов
- Академический стиль, научная терминология
- Логичное изложение с примерами
- Между разделами должна быть связь
- НЕ нужно оглавление, список литературы или титульный лист
- Начинай сразу с введения и основных разделов

{f'Дополнительные требования: {additional_info}' if additional_info else ''}

Формат ответа:
ВВЕДЕНИЕ
[текст введения]

1. [Название первого раздела]
[полный текст раздела]

2. [Название второго раздела]
[полный текст раздела]

...

ЗАКЛЮЧЕНИЕ
[текст заключения]

Пиши подробно, раскрывай каждую тему полностью. Используй абзацы для структуры."""

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
            
            if mode == 'topics':
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
            else:
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'document': result_text}, ensure_ascii=False),
                    'isBase64Encoded': False
                }
        else:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не удалось получить ответ от Gemini'}),
                'isBase64Encoded': False
            }
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else 'Unknown error'
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Gemini API error: {e.code}', 'details': error_body}),
            'isBase64Encoded': False
        }
    
    except json.JSONDecodeError as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Ошибка парсинга: {str(e)}'}),
            'isBase64Encoded': False
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Ошибка: {str(e)}'}),
            'isBase64Encoded': False
        }
