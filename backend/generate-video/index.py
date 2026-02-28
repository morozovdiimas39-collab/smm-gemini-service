"""
Генерация видео через Gemini API (Veo 3). Синхронный режим: POST ждёт окончания (2–5 мин) и возвращает videoUrl.
GET ?jobId=xxx — polling для обратной совместимости (если вернётся jobId).
"""

import base64
import json
import os
import time
import urllib.request

VEO_MODEL = 'veo-3.1-generate-preview'
POLL_INTERVAL = 10
MAX_POLL_MINUTES = 10


def _get_s3():
    bucket = os.environ.get('S3_BUCKET')
    key_id = os.environ.get('S3_ACCESS_KEY')
    secret = os.environ.get('S3_SECRET_KEY')
    if not (bucket and key_id and secret):
        return None, None
    import boto3
    s3 = boto3.client(
        's3',
        endpoint_url='https://storage.yandexcloud.net',
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
    )
    return s3, bucket


def _write_status(job_id: str, status: str, video_url: str = None, error: str = None):
    s3, bucket = _get_s3()
    if not s3:
        return
    data = {'status': status}
    if video_url:
        data['videoUrl'] = video_url
    if error:
        data['error'] = error
    s3.put_object(
        Bucket=bucket,
        Key=f'veo/jobs/{job_id}/status.json',
        Body=json.dumps(data).encode(),
        ContentType='application/json',
    )


def _do_generate(job_id: str, prompt: str, aspect_ratio: str, duration_sec: int, reference_image: dict = None):
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')
        if not api_key:
            _write_status(job_id, 'error', error='GEMINI_API_KEY не настроен')
            return

        from google import genai
        from google.genai import types

        http_options = None
        if proxy_url:
            import httpx
            http_options = types.HttpOptions(
                httpx_client=httpx.Client(proxy=proxy_url, follow_redirects=True)
            )
        client = genai.Client(api_key=api_key, http_options=http_options)

        config_kw = {'aspect_ratio': aspect_ratio, 'number_of_videos': 1}
        # С эталонным изображением Veo поддерживает только 8 сек
        if reference_image:
            duration_sec = 8
        if duration_sec in (4, 6, 8):
            config_kw['duration_seconds'] = duration_sec
        elif duration_sec == 5:
            config_kw['duration_seconds'] = 6
        config = types.GenerateVideosConfig(**config_kw)

        image_param = None
        if reference_image:
            ref_b64 = reference_image.get('data') or reference_image.get('dataBase64')
            ref_mime = reference_image.get('mimeType') or reference_image.get('mime_type') or 'image/png'
            if isinstance(ref_b64, str) and ref_b64:
                try:
                    image_bytes = base64.b64decode(ref_b64)
                    from io import BytesIO
                    # Veo принимает image через URI; загружаем в Files API
                    f = client.files.upload(file=BytesIO(image_bytes), config={'mime_type': ref_mime})
                    uri = getattr(f, 'uri', None) or getattr(f, 'name', None)
                    if uri and hasattr(types, 'Image'):
                        image_param = types.Image(file_uri=uri, mime_type=ref_mime)
                    elif uri and hasattr(types, 'VideoGenerationReferenceImage'):
                        image_param = types.VideoGenerationReferenceImage(file_uri=uri, mime_type=ref_mime)
                except Exception as e:
                    _write_status(job_id, 'error', error=f'Неверный формат изображения: {e}')
                    return

        if image_param is not None:
            operation = client.models.generate_videos(
                model=VEO_MODEL, prompt=prompt, config=config, image=image_param
            )
        else:
            operation = client.models.generate_videos(model=VEO_MODEL, prompt=prompt, config=config)
        deadline = time.time() + MAX_POLL_MINUTES * 60

        while time.time() < deadline:
            time.sleep(POLL_INTERVAL)
            operation = client.operations.get(operation)
            if not operation.done:
                continue
            if operation.error:
                _write_status(job_id, 'error', error=str(operation.error))
                return
            resp = operation.response
            if not resp or not getattr(resp, 'generated_videos', None):
                _write_status(job_id, 'error', error='В ответе нет видео')
                return
            video_ref = resp.generated_videos[0]
            video_file = getattr(video_ref, 'video', None) or getattr(video_ref, 'video_ref', None)
            if not video_file:
                _write_status(job_id, 'error', error='Не удалось извлечь видео')
                return

            download_url = getattr(video_file, 'uri', None) or getattr(video_file, 'name', None)
            if download_url:
                download_url = str(download_url)
                if not download_url.startswith('http'):
                    download_url = f'https://generativelanguage.googleapis.com/v1beta/{download_url}'
                sep = '&' if '?' in download_url else '?'
                actual_url = f'{download_url}{sep}key={api_key}'
                if proxy_url:
                    ph = urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url})
                    opener = urllib.request.build_opener(ph)
                    urllib.request.install_opener(opener)
                with urllib.request.urlopen(actual_url, timeout=120) as r:
                    data = r.read()
            else:
                blob = client.files.download(file=video_file)
                data = blob.data if hasattr(blob, 'data') else (blob if isinstance(blob, bytes) else None)

            if not data:
                _write_status(job_id, 'error', error='Не удалось получить видео')
                return

            s3, bucket = _get_s3()
            if s3:
                import uuid
                key = f'veo/{uuid.uuid4().hex}.mp4'
                s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType='video/mp4')
                url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=86400)
                _write_status(job_id, 'done', video_url=url)
            else:
                _write_status(job_id, 'error', error='Настройте S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY')
            return

        _write_status(job_id, 'error', error='Превышено время ожидания')
    except Exception as e:
        _write_status(job_id, 'error', error=str(e))


def handler(event: dict, context) -> dict:
    method = event.get('httpMethod', 'GET')
    headers = {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}

    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '86400',
            },
            'body': '',
        }

    if method == 'GET':
        # Polling: ?jobId=xxx
        params = event.get('queryStringParameters') or {}
        job_id = params.get('jobId')
        if not job_id:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Укажите jobId'})}
        s3, bucket = _get_s3()
        if not s3:
            return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': 'S3 не настроен'})}
        try:
            r = s3.get_object(Bucket=bucket, Key=f'veo/jobs/{job_id}/status.json')
            data = json.loads(r['Body'].read().decode())
            return {'statusCode': 200, 'headers': headers, 'body': json.dumps(data)}
        except Exception as e:
            err_str = str(e).lower()
            if 'nosuchkey' in err_str or '404' in err_str or 'not found' in err_str:
                return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'status': 'processing'})}
            return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

    if method != 'POST':
        return {'statusCode': 405, 'headers': headers, 'body': json.dumps({'error': 'Method not allowed'})}

    try:
        body_str = event.get('body', '{}')
        data = json.loads(body_str)

        prompt = data.get('prompt', '').strip()
        aspect_ratio = data.get('aspectRatio', '16:9')
        duration_sec = int(data.get('durationSec', 8))
        reference_image = data.get('referenceImage')  # optional: { mimeType, data } (base64)

        if not prompt:
            return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Укажите описание видео (prompt)'})}

        s3, bucket = _get_s3()
        if not s3:
            return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': 'Настройте S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY'})}

        import uuid
        job_id = uuid.uuid4().hex
        ref_for_generate = None
        if reference_image and isinstance(reference_image, dict) and (reference_image.get('data') or reference_image.get('dataBase64')):
            ref_b64 = reference_image.get('data') or reference_image.get('dataBase64')
            ref_mime = reference_image.get('mimeType') or reference_image.get('mime_type') or 'image/png'
            ref_for_generate = {'data': ref_b64, 'mimeType': ref_mime}

        _do_generate(job_id, prompt, aspect_ratio, duration_sec, reference_image=ref_for_generate)

        try:
            r = s3.get_object(Bucket=bucket, Key=f'veo/jobs/{job_id}/status.json')
            status_data = json.loads(r['Body'].read().decode())
            if status_data.get('status') == 'done' and status_data.get('videoUrl'):
                return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'videoUrl': status_data['videoUrl']})}
            return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': status_data.get('error', 'Не удалось создать видео')})}
        except Exception as e:
            return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}

    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}
