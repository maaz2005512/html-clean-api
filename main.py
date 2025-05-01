from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        "message": "Welcome to HTML Cleaner & Multi-Keyword Extractor API",
        "usage": "POST /clean with JSON body: { 'html': '<html>', 'keywords': ['keyword1', 'keyword2'] }"
    })

@app.route('/clean', methods=['POST'])
def clean_html():
    try:
        data = request.get_json()
        html = data.get('html', '')
        keywords = data.get('keywords', [])

        if not html or not isinstance(keywords, list) or len(keywords) == 0:
            return jsonify({"error": "Provide 'html' and a list of 'keywords'"}), 400

        # Normalize keywords
        keywords = [kw.lower() for kw in keywords]

        soup = BeautifulSoup(html, 'html.parser')

        for tag in soup(["script", "style", "noscript", "footer", "header"]):
            tag.extract()

        full_text = soup.get_text(separator='\n')
        lines = [line.strip() for line in full_text.splitlines()]
        clean_text = '\n'.join(line for line in lines if line)

        sections = []

        for heading in soup.find_all(re.compile('^h[1-6]$')):
            section_text = ""
            next_tag = heading.find_next_sibling()
            paragraph_limit = 0

            while next_tag and paragraph_limit < 5:
                if next_tag.name == 'p':
                    section_text += next_tag.get_text(separator=' ', strip=True) + " "
                    paragraph_limit += 1
                next_tag = next_tag.find_next_sibling()

            combined_text = heading.get_text().lower() + " " + section_text.lower()

            for keyword in keywords:
                if keyword in combined_text:
                    count = combined_text.count(keyword)

                    # URL detection
                    url = None
                    parent_link = heading.find_parent('a', href=True)
                    if parent_link and parent_link.get('href'):
                        url = parent_link.get('href')
                    elif heading.find('a', href=True):
                        url = heading.find('a').get('href')
                    else:
                        link_tag = heading.find_next('a', href=True)
                        if link_tag:
                            url = link_tag.get('href')

                    # If relative URL, patch it manually later
                    if url and url.startswith('/'):
                        url = "https://example.com" + url  # Replace with the base domain

                    sections.append({
                        "keyword": keyword,
                        "heading": heading.get_text(strip=True),
                        "context": section_text.strip(),
                        "score": count,
                        "url": url
                    })

        best_match = max(sections, key=lambda x: x["score"], default=None)

        if best_match:
            return jsonify({
                "matchedKeyword": best_match["keyword"],
                "heading": best_match["heading"],
                "articlePreview": best_match["context"][:500] + "...",
                "url": best_match["url"],
                "cleanText": clean_text
            })
        else:
            return jsonify({
                "message": "No keyword match found in any heading or content.",
                "cleanText": clean_text
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
