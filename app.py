from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import json
import time
import traceback
import re

app = Flask(__name__)
CORS(app)

# 🔐 Replace with your actual Gemini API key
genai.configure(api_key="AIzaSyBPVIXo-nz2ogDlNGKEsnVLtgkZ3J-69n0")

model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')

def extract_json_from_response(text):
    try:
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        else:
            return json.loads(text.strip())  # fallback if response is already JSON
    except Exception as e:
        print("JSON extraction failed:", e)
        raise e

def generate_quiz_with_retries(prompt, retries=5, backoff_factor=1):
    for i in range(retries):
        try:
            response = model.generate_content(prompt)
            print("DEBUG: Gemini raw response:", response.text)
            if response.text:
                return extract_json_from_response(response.text)
        except Exception as e:
            app.logger.error(f"Attempt {i + 1} failed: {e}")
            traceback.print_exc()
            if i < retries - 1:
                time.sleep(backoff_factor * (2 ** i))
            else:
                raise e
    return None

@app.route('/', methods=['GET'])
def index():
    return "Flask backend is running!"

@app.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.json
        topic = data.get('topic')
        if not topic:
            return jsonify({"error": "Topic is required"}), 400

        prompt = f"""
        You are a quiz generator. Return a JSON object only.
        Generate a multiple-choice quiz with exactly 5 questions on: "{topic}".
        Each question must have:
        - A 'question' string
        - An 'options' list with 4 choices
        - A 'correct_answer' string that exactly matches one of the options.
        Return only a JSON like:
        {{
          "topic": "{topic}",
          "questions": [
            {{
              "question": "...",
              "options": ["A", "B", "C", "D"],
              "correct_answer": "..."
            }},
            ...
          ]
        }}
        No explanations. Only valid JSON.
        """

        quiz_data = generate_quiz_with_retries(prompt)
        if quiz_data:
            return jsonify(quiz_data)
        else:
            return jsonify({"error": "Could not generate quiz. Please try again."}), 500

    except Exception as e:
        app.logger.error("An error occurred while generating the quiz.")
        traceback.print_exc()
        return jsonify({"error": "An error occurred while generating the quiz."}), 500

if __name__ == '__main__':
    app.run(debug=True)
