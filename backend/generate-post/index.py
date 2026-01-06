import json
import os
import urllib.request
import urllib.error

def handler(event: dict, context) -> dict:
    '''API для генерации постов через Gemini 2.5 Flash с использованием прокси'''
    
    method = event.get('httpMethod', 'GET')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '86400'
            },
            'body': ''
        }
    
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        body_str = event.get('body', '{}')
        request_data = json.loads(body_str)
        
        platform = request_data.get('platform', 'социальная сеть')
        task = request_data.get('task', '')
        tone = request_data.get('tone', 'дружелюбный')
        goal = request_data.get('goal', 'вовлечение')
        length = request_data.get('length', 'средний')
        emojis = request_data.get('emojis', 'баланс')
        
        if not task:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Задача поста не указана'})
            }
        
        platform_names = {
            'telegram': 'Telegram',
            'vk': 'ВКонтакте',
            'instagram': 'Instagram',
            'facebook': 'Facebook'
        }
        
        length_desc = {
            'короткий': 'до 200 символов',
            'средний': '200-500 символов',
            'длинный': 'более 500 символов'
        }
        
        emoji_desc = {
            'нет': 'не использовать эмодзи',
            'мало': 'использовать 1-2 эмодзи',
            'баланс': 'использовать 3-5 эмодзи',
            'много': 'использовать много эмодзи (8-12)'
        }
        
        prompt = f"""Создай пост для {platform_names.get(platform, 'социальной сети')}.

Задача: {task}

Требования:
- Тон: {tone}
- Цель поста: {goal}
- Длина: {length_desc.get(length, '200-500 символов')}
- Эмодзи: {emoji_desc.get(emojis, 'использовать 3-5 эмодзи')}

Напиши готовый пост для {platform_names.get(platform, '')} канала/группы AnyaGPT. Только текст поста, без пояснений."""
        
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')
        
        if not gemini_api_key:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'GEMINI_API_KEY не настроен'})
            }
        
        gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={gemini_api_key}'
        
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
            generated_text = gemini_response['candidates'][0]['content']['parts'][0]['text']
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'post': generated_text})
            }
        else:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не удалось получить ответ от Gemini'})
            }
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else 'Unknown error'
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Gemini API error: {e.code}', 'details': error_body})
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
