from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from flask_cors import CORS
import traceback
import logging
import gc
import time
import html
import re
from dateutil import parser as dparser

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return jsonify({"message": "HTML Keyword Extractor API"})

@app.route('/clean', methods=['POST'])
def clean_html():
    try:
        data = request.get_json(force=True)
        html_content = data.get('html', '')
        keywords = data.get('keywords', [])

        if not html_content or not isinstance(html_content, str):
            return jsonify({"error": "Invalid or missing 'html'"}), 400

        soup = BeautifulSoup(html_content, 'lxml')
        articles = soup.find_all('article')

        keyword_map = {k.lower(): [] for k in keywords}

        for article in articles:
            heading_tag = article.find(['h1', 'h2', 'h3'])
            heading = heading_tag.get_text(strip=True) if heading_tag else None
            article_text = article.get_text(separator=' ', strip=True)
            clean_text = html.unescape(article_text)
            clean_text = re.sub(r'\s+', ' ', clean_text)

            date_text = None
            date_match = re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b', clean_text)
            if date_match:
                try:
                    parsed_date = dparser.parse(date_match.group(), fuzzy=True)
                    date_text = parsed_date.strftime('%Y-%m-%d')
                except:
                    date_text = None

            url_tag = article.find_previous('a', href=True)
            article_url = url_tag['href'] if url_tag else None

            for keyword in keywords:
                k_lower = keyword.lower()
                count = clean_text.lower().count(k_lower)
                if count >= 2:
                    keyword_map[k_lower].append({
                        "heading": heading,
                        "url": article_url,
                        "date": date_text,
                        "match_count": count,
                        "article_context": ' '.join(clean_text.split()[:100])
                    })

        result = []
        for keyword, articles in keyword_map.items():
            if articles:
                result.append({
                    "keyword": keyword,
                    "total_matches": sum(a["match_count"] for a in articles),
                    "matched_articles": articles
                })

        return jsonify(result)

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

if __name__ == '__main__':
    app.run(debug=True)
