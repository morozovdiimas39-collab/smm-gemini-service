import json
import os
import urllib.request
import urllib.error
import urllib.parse

def handler(event: dict, context) -> dict:
    '''API для генерации изображений через Pollinations.ai (бесплатный FLUX)'''
    
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
            'квадрат': {'width': 1024, 'height': 1024},
            'горизонтальный': {'width': 1920, 'height': 1080},
            'вертикальный': {'width': 1080, 'height': 1920},
            'горизонтальный_широкий': {'width': 1200, 'height': 628}
        }
        
        style_instruction = style_prompts.get(style, '')
        size_config = aspect_ratio_map.get(aspect_ratio, {'width': 1024, 'height': 1024})
        
        full_prompt = f"{task}. {style_instruction}. High quality, professional, detailed."
        encoded_prompt = urllib.parse.quote(full_prompt)
        
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={size_config['width']}&height={size_config['height']}&nologo=true&model=flux"
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'imageUrl': image_url,
                'prompt': full_prompt
            })
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
