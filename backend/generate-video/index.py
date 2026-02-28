"""
Генерация видео через Gemini API (Veo 3) — тот же GEMINI_API_KEY, что и для картинок.
Документация: https://ai.google.dev/gemini-api/docs/video
"""

import json
import os
import time
import urllib.request
import urllib.error

VEO_MODEL = 'veo-3.1-generate-preview'
POLL_INTERVAL = 10
MAX_POLL_MINUTES = 10


def handler(event: dict, context) -> dict:
    method = event.get('httpMethod', 'GET')

    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '86400',
            },
            'body': '',
        }

    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Method not allowed'}),
        }

    try:
        body_str = event.get('body', '{}')
        data = json.loads(body_str)
        prompt = data.get('prompt', '').strip()
        aspect_ratio = data.get('aspectRatio', '16:9')
        duration_sec = data.get('durationSec', 8)

        if not prompt:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Укажите описание видео (prompt)'}),
            }

        api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')

        if not api_key:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'GEMINI_API_KEY не настроен'}),
            }

        if proxy_url:
            proxy_handler = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)

        # Gemini API: generateVideos (асинхронная операция)
        base_url = f'https://generativelanguage.googleapis.com/v1beta/models/{VEO_MODEL}:generateVideos?key={api_key}'
        request_body = {
            'prompt': {'text': prompt},
            'aspectRatio': aspect_ratio,
            'numberOfVideos': 1,
        }
        if duration_sec in (5, 6, 8):
            request_body['durationSeconds'] = duration_sec

        req = urllib.request.Request(
            base_url,
            data=json.dumps(request_body).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                op_data = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else str(e)
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'Veo API: {e.code}', 'details': body[:500]}),
            }

        op_name = op_data.get('name')
        if not op_name:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Нет operation name в ответе', 'details': op_data}),
            }

        # Операции в Gemini API: полный URL для polling
        if op_name.startswith('operations/'):
            op_id = op_name
        else:
            op_id = op_name
        op_url = f'https://generativelanguage.googleapis.com/v1beta/{op_id}?key={api_key}'

        deadline = time.time() + MAX_POLL_MINUTES * 60
        while time.time() < deadline:
            time.sleep(POLL_INTERVAL)
            req_op = urllib.request.Request(op_url)
            with urllib.request.urlopen(req_op, timeout=30) as op_resp:
                op_status = json.loads(op_resp.read().decode('utf-8'))

            if op_status.get('done'):
                response = op_status.get('response', {})
                generated = response.get('generatedVideos') or response.get('generated_videos') or []
                if not generated:
                    return {
                        'statusCode': 500,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'error': 'В ответе нет видео', 'response': response}),
                    }
                video_ref = generated[0]
                video = video_ref.get('video') or video_ref.get('videoRef') or video_ref
                if isinstance(video, dict):
                    video_uri = video.get('uri') or video.get('fileData', {}).get('fileUri')
                else:
                    video_uri = None
                if not video_uri and isinstance(video, str):
                    video_uri = video
                if video_uri:
                    return {
                        'statusCode': 200,
                        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                        'body': json.dumps({'videoUrl': video_uri, 'prompt': prompt[:100]}),
                    }
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': 'Не удалось извлечь URL видео', 'generated': generated}),
                }

            if op_status.get('error'):
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': op_status['error'].get('message', 'Veo error')}),
                }

        return {
            'statusCode': 504,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Превышено время ожидания генерации видео'}),
        }

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e.code), 'details': body[:500]}),
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
        }
