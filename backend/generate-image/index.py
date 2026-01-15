import json
import os
import urllib.request
import urllib.error
import base64
import uuid

def handler(event: dict, context) -> dict:
    '''API для генерации изображений через Gemini 2.5 Flash Image (Nano Banana)'''
    
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
        
        task = request_data.get('task', '')
        style = request_data.get('style', 'фотореализм')
        aspect_ratio = request_data.get('aspectRatio', 'квадрат')
        
        if not task:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Описание изображения не указано'})
            }
        
        style_prompts = {
            'фотореализм': 'Photorealistic, ultra-detailed, professional photography, high quality',
            'иллюстрация': 'Digital illustration, artistic style, vibrant colors, creative design',
            'мультяшный': 'Cartoon style, animated, colorful, fun character design',
            'минимализм': 'Minimalist design, clean lines, simple composition, elegant',
            'акварель': 'Watercolor painting style, soft colors, artistic brush strokes, gentle',
            '3d_render': '3D render, CGI, modern digital art, clean look, professional',
            'аниме': 'Anime style, manga art, Japanese animation aesthetic, detailed',
            'комикс': 'Comic book style, bold lines, pop art colors, dynamic',
            'винтаж': 'Vintage style, retro aesthetic, nostalgic feel, classic',
            'неон': 'Neon lights, cyberpunk aesthetic, vibrant glow effects, futuristic',
            'пастель': 'Pastel colors, soft tones, dreamy atmosphere, gentle light',
            'граффити': 'Graffiti art style, urban street art, bold spray paint, expressive'
        }
        
        aspect_ratio_map = {
            'квадрат': '1:1',
            'горизонтальный': '16:9',
            'вертикальный': '9:16',
            'горизонтальный_широкий': '3:2'
        }
        
        style_instruction = style_prompts.get(style, '')
        aspect_instruction = aspect_ratio_map.get(aspect_ratio, '1:1')
        
        prompt = f"{task}. Style: {style_instruction}. Aspect ratio: {aspect_instruction}. High quality, detailed."
        
        gemini_api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')
        
        if not gemini_api_key:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'GEMINI_API_KEY не настроен'})
            }
        
        gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={gemini_api_key}'
        
        gemini_request = {
            'contents': [{
                'parts': [{
                    'text': prompt
                }]
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
        
        with urllib.request.urlopen(req, timeout=60) as response:
            gemini_response = json.loads(response.read().decode('utf-8'))
        
        if 'candidates' in gemini_response and len(gemini_response['candidates']) > 0:
            parts = gemini_response['candidates'][0]['content']['parts']
            
            for part in parts:
                if 'inlineData' in part and 'data' in part['inlineData']:
                    image_data = part['inlineData']['data']
                    mime_type = part['inlineData'].get('mimeType', 'image/png')
                    
                    return {
                        'statusCode': 200,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({
                            'imageUrl': f'data:{mime_type};base64,{image_data}',
                            'prompt': prompt
                        })
                    }
            
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Нет изображения в ответе', 'response': gemini_response})
            }
        else:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не удалось получить ответ', 'response': gemini_response})
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