from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to HTML Cleaner API",
        "usage": "POST /clean with 'html' and optional 'keywords' fields"
    })

@app.route('/clean', methods=['POST'])
def clean_html():
    try:
        data = request.get_json()
        html = data.get('html')
        keywords = data.get('keywords', [])

        if not html:
            return jsonify({"error": "Missing 'html' field"}), 400
        if not isinstance(html, str):
            return jsonify({"error": "'html' must be a string"}), 400
        if not isinstance(keywords, list):
            return jsonify({"error": "'keywords' must be a list of strings"}), 400

        soup = BeautifulSoup(html, 'html.parser')

        # Remove scripts and styles
        for tag in soup(["script", "style"]):
            tag.extract()

        # Try extracting URL from meta or base tags
        url = ""
        base = soup.find('base', href=True)
        if base:
            url = base['href']
        else:
            meta = soup.find('meta', attrs={"property": "og:url"})
            if meta:
                url = meta.get('content', '')

        # Find all article sections
        articles = soup.find_all(['article', 'section', 'div'])

        best_match = {
            "url": url,
            "heading": None,
            "article": None,
            "keywords": [],
            "match_count": 0
        }

        for block in articles:
            text = block.get_text(separator=' ', strip=True).lower()
            count = sum(text.count(k.lower()) for k in keywords)
            if count > best_match["match_count"]:
                heading = block.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                snippet = ' '.join(text.split()[:100])  # first 100 words
                best_match.update({
                    "match_count": count,
                    "heading": heading.get_text(strip=True) if heading else None,
                    "article": snippet,
                    "keywords": keywords
                })

        # Clean full HTML text
        full_text = soup.get_text(separator=' ', strip=True)

        return jsonify({
            "url": best_match['url'],
            "heading": best_match['heading'],
            "article_context": best_match['article'],
            "matched_keywords": best_match['keywords'],
            "cleanText": full_text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
