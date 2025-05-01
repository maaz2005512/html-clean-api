
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"message": "Welcome to HTML Cleaner API", 
                    "usage": "POST /clean with JSON body containing 'html' field"})

@app.route('/clean', methods=['POST'])
def clean_html():
    try:
        data = request.get_json()
        if not data or 'html' not in data:
            return jsonify({"error": "Missing 'html' field in request body"}), 400

        html = data['html']
        if not isinstance(html, str):
            return jsonify({"error": "'html' must be a string"}), 400

        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style tags
        for tag in soup(["script", "style"]):
            tag.extract()

        # Get clean text
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)

        return jsonify({"cleanText": clean_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
