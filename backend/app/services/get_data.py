
import json

def get_json(gemini_path, convrted_path):

    with open(gemini_path, 'r', encoding='utf-8') as data:
        gemini_data = json.load(data)
    
    with open(gemini_path, 'r', encoding='utf-8') as data:
        converted_data = json.load(data)
        
    return gemini_data, converted_data