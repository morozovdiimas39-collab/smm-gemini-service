import json
import os
import urllib.request
import urllib.error

def handler(event: dict, context) -> dict:
    '''Проверяет текст на AI-паттерны и уникальность через Gemini API'''
    
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
        text = body.get('text', '')
        
        if not text:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Текст не предоставлен'}),
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
        
        # Промпт для анализа текста
        prompt = f"""Проанализируй следующий текст по двум критериям:

ТЕКСТ:
{text[:3000]}

ЗАДАЧИ:
1. AI-детекция: Оцени от 0 до 100, насколько текст похож на сгенерированный ИИ
   - Признаки AI: повторяющиеся фразы, шаблонность, искусственная структура, клише
   - Признаки человека: естественность, эмоции, неидеальность, личный стиль

2. Уникальность формулировок: Оцени от 0 до 100, насколько оригинальны формулировки
   - Низкая (0-40): Много общих/шаблонных фраз и конструкций
   - Средняя (40-70): Есть уникальные формулировки, но много стандартных
   - Высокая (70-100): Оригинальный стиль, свежие формулировки

ВЕРНИ СТРОГО JSON:
{{
  "ai_score": <число 0-100>,
  "uniqueness_score": <число 0-100>,
  "ai_indicators": ["признак 1", "признак 2"],
  "improvement_tips": ["совет 1", "совет 2"]
}}

ВАЖНО: Отвечай ТОЛЬКО JSON, без текста до и после!"""

        gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}'
        
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
            
            # Очистка от markdown форматирования
            if result_text.startswith('```'):
                lines = result_text.split('\n')
                result_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else result_text
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            analysis = json.loads(result_text)
            
            # Определяем, прошел ли текст проверку
            ai_score = analysis.get('ai_score', 50)
            uniqueness_score = analysis.get('uniqueness_score', 50)
            
            passed = ai_score < 50 and uniqueness_score > 70
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'ai_score': ai_score,
                    'uniqueness_score': uniqueness_score,
                    'passed': passed,
                    'ai_indicators': analysis.get('ai_indicators', []),
                    'improvement_tips': analysis.get('improvement_tips', [])
                }, ensure_ascii=False),
                'isBase64Encoded': False
            }
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Не удалось получить анализ текста'}),
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