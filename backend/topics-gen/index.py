import json
import os
import google.generativeai as genai

def handler(event: dict, context) -> dict:
    '''Генерирует темы для документов'''
    
    method = event.get('httpMethod', 'POST')
    
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            },
            'body': '',
            'isBase64Encoded': False
        }
    
    try:
        body = json.loads(event.get('body', '{}'))
        subject = body.get('subject', '')
        pages = body.get('pages', 10)
        
        if not subject:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Subject required'}),
                'isBase64Encoded': False
            }
        
        api_key = os.environ.get('GEMINI_API_KEY')
        proxy_url = os.environ.get('PROXY_URL')
        
        if proxy_url:
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        sections = max(3, pages // 3)
        prompt = f'''Create structure for document about: {subject}
Return only JSON array with {sections} objects: [{{"title": "...", "description": "..."}}]
No extra text, only JSON!'''
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith('```'):
            text = '\n'.join(text.split('\n')[1:-1]).replace('```json', '').replace('```', '').strip()
        
        topics = json.loads(text)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'topics': topics}, ensure_ascii=False),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)}),
            'isBase64Encoded': False
        }
