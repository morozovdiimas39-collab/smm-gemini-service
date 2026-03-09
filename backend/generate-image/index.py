import json
import os
import time
import urllib.request
import urllib.error
import base64

MAX_RETRIES = 3
RETRY_DELAY_SEC = 4
RETRY_CODES = (503, 429, 500)

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

    t0 = time.time()

    try:
        body_str = event.get('body', '{}')
        request_data = json.loads(body_str)

        # Режим отладки таймаута: запрос с testTimeout=65 ждёт 65 сек и возвращает OK. Нужно понять, на какой секунде рвётся соединение.
        test_timeout = request_data.get('testTimeout')
        if isinstance(test_timeout, (int, float)) and 10 <= test_timeout <= 180:
            print(f'[generate_image] testTimeout={test_timeout}s sleeping...')
            time.sleep(test_timeout)
            print(f'[generate_image] testTimeout done, returning after {time.time() - t0:.1f}s')
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'ok': True, 'slept_sec': test_timeout, 'total_sec': round(time.time() - t0, 1)})
            }

        task = request_data.get('task', '')
        style = request_data.get('style', 'фотореализм')
        aspect_ratio = request_data.get('aspectRatio', 'квадрат')
        image_model = request_data.get('imageModel', 'flash')  # 'flash' | 'pro'
        image_provider = request_data.get('imageProvider', request_data.get('provider', 'gemini'))  # 'gemini' | 'yandex'
        reference_image = request_data.get('referenceImage')  # optional: base64 string or { "mimeType": "...", "data": "..." }

        if not task:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Описание изображения не указано'})
            }

        style_prompts = {
            'как_на_картинке': '',  # используется только при has_reference; стиль берётся с образца
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

        use_reference_style = (style == 'как_на_картинке')
        style_instruction = style_prompts.get(style, '') if not use_reference_style else ''
        has_reference = False
        ref_mime = 'image/png'
        ref_b64 = None
        if reference_image and image_provider != 'yandex':
            if isinstance(reference_image, dict):
                ref_b64 = reference_image.get('data') or reference_image.get('dataBase64')
                ref_mime = reference_image.get('mimeType') or reference_image.get('mime_type') or 'image/png'
            elif isinstance(reference_image, str):
                ref_b64 = reference_image
            if ref_b64:
                has_reference = True
        if has_reference:
            if use_reference_style:
                prompt = (
                    "Using the attached reference image as the basis and as the ONLY style reference: "
                    "preserve the exact same artistic style, lighting, color palette, mood, and visual look of the reference. "
                    f"Create: {task}. The result must look like it was made in the same style as the reference. High quality, detailed."
                )
            else:
                prompt = f"Using the attached reference image as the basis, create: {task}. Style: {style_instruction}. Keep the composition/subject from the reference but apply the new description and style. High quality, detailed."
        else:
            if use_reference_style:
                style_instruction = style_prompts.get('фотореализм', '')
            prompt = f"{task}. Style: {style_instruction}. High quality, detailed."

        # Соответствие формата фронта и Gemini (1:1, 16:9, 9:16, 3:2, 4:3, 3:4, 21:9, 4:5, 5:4)
        aspect_to_gemini = {
            'квадрат': '1:1',
            'горизонтальный': '16:9',
            'вертикальный': '9:16',
            'горизонтальный_широкий': '3:2',
            '4_3': '4:3',
            '3_4': '3:4',
            '21_9': '21:9',
            '4_5': '4:5',
            '5_4': '5:4',
        }
        # Yandex ART: widthRatio, heightRatio — строки (например "1","1", "16","9")
        aspect_to_yandex = {
            'квадрат': ('1', '1'),
            'горизонтальный': ('16', '9'),
            'вертикальный': ('9', '16'),
            'горизонтальный_широкий': ('3', '2'),
            '4_3': ('4', '3'),
            '3_4': ('3', '4'),
            '21_9': ('21', '9'),
            '4_5': ('4', '5'),
            '5_4': ('5', '4'),
        }
        gemini_aspect = aspect_to_gemini.get(aspect_ratio, '1:1')
        yandex_w, yandex_h = aspect_to_yandex.get(aspect_ratio, ('1', '1'))

        if image_provider == 'yandex':
            yandex_api_key = os.environ.get('YANDEX_API_KEY')
            yandex_folder_id = os.environ.get('YANDEX_FOLDER_ID')
            proxy_url = os.environ.get('PROXY_URL')
            if not yandex_api_key or not yandex_folder_id:
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'YANDEX_API_KEY или YANDEX_FOLDER_ID не настроены'})
                }
            model_uri = f'art://{yandex_folder_id}/yandex-art/latest'
            art_body = {
                'modelUri': model_uri,
                'messages': [{'text': prompt}],
                'generationOptions': {
                    'seed': str((hash(prompt) % 10**9) + 10**9),
                    'aspectRatio': {'widthRatio': yandex_w, 'heightRatio': yandex_h}
                }
            }
            art_url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync'
            req = urllib.request.Request(
                art_url,
                data=json.dumps(art_body).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Api-Key {yandex_api_key}'
                }
            )
            if proxy_url:
                proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
                opener = urllib.request.build_opener(proxy_handler)
                urllib.request.install_opener(opener)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    op_data = json.loads(resp.read().decode('utf-8'))
            except urllib.error.HTTPError as e:
                err_b = e.read().decode('utf-8') if e.fp else ''
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': f'Yandex ART: {e.code}', 'details': err_b[:400]})
                }
            op_id = op_data.get('id')
            if not op_id:
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Yandex ART не вернул id операции', 'details': str(op_data)[:300]})
                }
            op_url = f'https://operation.api.cloud.yandex.net/operations/{op_id}'
            op_req_headers = {'Authorization': f'Api-Key {yandex_api_key}'}
            if proxy_url:
                proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
                opener = urllib.request.build_opener(proxy_handler)
                urllib.request.install_opener(opener)
            max_poll_sec = 180
            poll_interval = 5
            t_art_start = time.time()
            while (time.time() - t_art_start) < max_poll_sec:
                op_req = urllib.request.Request(op_url, headers=op_req_headers)
                try:
                    with urllib.request.urlopen(op_req, timeout=30) as op_resp:
                        op_result = json.loads(op_resp.read().decode('utf-8'))
                except urllib.error.HTTPError as e:
                    return {
                        'statusCode': 500,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': f'Yandex операция: {e.code}'})
                    }
                if op_result.get('done'):
                    response_data = op_result.get('response') or {}
                    image_b64_art = response_data.get('image')
                    if image_b64_art:
                        image_url_art = f"data:image/png;base64,{image_b64_art}"
                        total_art = round(time.time() - t0, 1)
                        return {
                            'statusCode': 200,
                            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                            'body': json.dumps({
                                'imageUrl': image_url_art,
                                'prompt': prompt,
                                'debug': {'total_sec': total_art, 'provider': 'yandex'}
                            })
                        }
                    return {
                        'statusCode': 500,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': 'В ответе Yandex ART нет изображения'})
                    }
                time.sleep(poll_interval)
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Yandex ART: генерация заняла слишком много времени. Попробуйте позже.'})
            }

        api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')

        if not api_key:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'GEMINI_API_KEY не настроен'})
            }

        # Flash — gemini-2.5-flash-image; Nano Banana Pro — gemini-3-pro-image-preview
        model_id = 'gemini-3-pro-image-preview' if image_model == 'pro' else 'gemini-2.5-flash-image'
        print(f'[generate_image] started model={model_id}')

        gemini_url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}'

        # Формат по доке: https://ai.google.dev/gemini-api/docs/image-generation
        # responseModalities TEXT+IMAGE; imageConfig.aspectRatio — для Nano Banana / Gemini image
        generation_config = {
            'responseModalities': ['TEXT', 'IMAGE'],
        }
        # aspectRatio по доке: 1:1, 16:9, 9:16, 3:2, 4:3, 3:4, 4:5, 5:4, 21:9
        generation_config['imageConfig'] = {'aspectRatio': gemini_aspect}

        parts = []
        if has_reference and ref_b64:
            parts.append({'inlineData': {'mimeType': ref_mime, 'data': ref_b64}})
        parts.append({'text': prompt})
        gemini_request = {
            'contents': [{'parts': parts}],
            'generationConfig': generation_config,
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

        last_error = None
        t_gemini_start = time.time()
        for attempt in range(MAX_RETRIES):
            try:
                print(f'[generate_image] calling_gemini attempt={attempt + 1}')
                with urllib.request.urlopen(req, timeout=120) as response:
                    gemini_response = json.loads(response.read().decode('utf-8'))
                break
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code in RETRY_CODES and attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SEC * (attempt + 1))
                    continue
                raise

        gemini_elapsed = round(time.time() - t_gemini_start, 1)
        print(f'[generate_image] gemini_elapsed_sec={gemini_elapsed}')

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
        total_elapsed = round(time.time() - t0, 1)
        print(f'[generate_image] returning_response total_sec={total_elapsed} gemini_sec={gemini_elapsed}')

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'imageUrl': image_url,
                'prompt': prompt,
                'debug': {'total_sec': total_elapsed, 'gemini_sec': gemini_elapsed}
            })
        }

    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
        except Exception:
            error_body = str(e)
        user_message = None
        if error_body:
            try:
                err = json.loads(error_body)
                if err.get('error', {}).get('status') == 'UNAVAILABLE' or err.get('error', {}).get('code') == 503:
                    user_message = 'Модель перегружена. Обычно это ненадолго — попробуйте через минуту.'
                elif err.get('error', {}).get('message'):
                    user_message = err['error']['message'][:200]
            except Exception:
                pass
        if not user_message:
            if e.code == 503:
                user_message = 'Сервис Gemini временно недоступен. Попробуйте через минуту.'
            elif e.code == 429:
                user_message = 'Слишком много запросов. Подождите немного и попробуйте снова.'
            else:
                user_message = f'Gemini API error: {e.code}'
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': user_message})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
