import json
import os
import urllib.request
import urllib.error
import base64

def handler(event: dict, context) -> dict:
    '''API для генерации изображений через Flux (Black Forest Labs)'''
    
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
        
        style_instruction = style_prompts.get(style, '')
        prompt = f"{task}. Style: {style_instruction}. High quality, detailed."
        
        flux_api_key = os.environ.get('BFL_API_KEY')
        
        if not flux_api_key:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'BFL_API_KEY не настроен'})
            }
        
        flux_url = 'https://api.bfl.ml/v1/flux-pro-1.1'
        
        flux_request = {
            'prompt': prompt,
            'width': 1024,
            'height': 1024
        }
        
        req = urllib.request.Request(
            flux_url,
            data=json.dumps(flux_request).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'X-Key': flux_api_key
            }
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            flux_response = json.loads(response.read().decode('utf-8'))
        
        if 'id' in flux_response:
            task_id = flux_response['id']
            
            import time
            max_attempts = 30
            for attempt in range(max_attempts):
                time.sleep(2)
                
                result_req = urllib.request.Request(
                    f'https://api.bfl.ml/v1/get_result?id={task_id}',
                    headers={'X-Key': flux_api_key}
                )
                
                with urllib.request.urlopen(result_req, timeout=30) as result_response:
                    result_data = json.loads(result_response.read().decode('utf-8'))
                
                if result_data.get('status') == 'Ready':
                    image_url = result_data.get('result', {}).get('sample')
                    if image_url:
                        return {
                            'statusCode': 200,
                            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                            'body': json.dumps({
                                'imageUrl': image_url,
                                'prompt': prompt
                            })
                        }
                elif result_data.get('status') == 'Error':
                    return {
                        'statusCode': 500,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': 'Ошибка генерации изображения', 'details': result_data})
                    }
            
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Превышено время ожидания генерации'})
            }
        else:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Не удалось запустить генерацию', 'response': flux_response})
            }
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else 'Unknown error'
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': f'Flux API error: {e.code}', 'details': error_body})
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }