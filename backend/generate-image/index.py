import json
import os
import urllib.request
import urllib.error
import base64

def handler(event: dict, context) -> dict:
    '''Генерация изображений через Gemini (gemini-2.5-flash-image)'''

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
        image_model = request_data.get('imageModel', 'flash')  # 'flash' | 'pro'

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

        style_instruction = style_prompts.get(style, '')
        prompt = f"{task}. Style: {style_instruction}. High quality, detailed."

        api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')

        if not api_key:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'GEMINI_API_KEY не настроен'})
            }

        # Модель: Flash (быстро, дёшево) или Pro / Nano Banana Pro (качество, дороже)
        model_id = 'gemini-3-pro-image-preview' if image_model == 'pro' else 'gemini-2.5-flash-image'
        gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}'

        gemini_request = {
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {
                'responseModalities': ['TEXT', 'IMAGE']
            }
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

        with urllib.request.urlopen(req, timeout=120) as response:
            gemini_response = json.loads(response.read().decode('utf-8'))

        # Достаём изображение из ответа (inlineData в parts)
        if 'candidates' not in gemini_response or not gemini_response['candidates']:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Gemini не вернул результат', 'details': gemini_response})
            }

        content = gemini_response['candidates'][0].get('content') or {}
        parts = content.get('parts') or []
        image_b64 = None
        mime_type = 'image/png'

        for part in parts:
            # REST может вернуть camelCase (inlineData) или snake_case (inline_data)
            inline = part.get('inlineData') or part.get('inline_data')
            if inline:
                image_b64 = inline.get('data')
                mime_type = inline.get('mimeType') or inline.get('mime_type') or 'image/png'
                if image_b64:
                    break

        if not image_b64:
            # Показать структуру ответа для отладки (без больших base64)
            def _peek(obj, depth=0):
                if depth > 4:
                    return '...'
                if isinstance(obj, dict):
                    return {k: _peek(v, depth + 1) if k != 'data' else '<base64>' for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_peek(x, depth + 1) for x in obj[:3]]
                return type(obj).__name__
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': 'В ответе Gemini нет изображения',
                    'details': _peek(gemini_response)
                })
            }

        # Фронт ожидает imageUrl — отдаём data URL
        image_url = f"data:{mime_type};base64,{image_b64}"

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'imageUrl': image_url,
                'prompt': prompt
            })
        }

    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
        except Exception:
            error_body = str(e)
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
