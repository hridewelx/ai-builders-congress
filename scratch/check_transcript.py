import json

with open(r'C:\Users\Jitu\.gemini\antigravity\brain\843fb091-f952-4738-9ffc-9ef5996ee4f0\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        if obj.get('step_index') == 2831:
            print(obj.get('content'))
            break
