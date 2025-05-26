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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    start_time = time.time()
    try:
        content_type = request.headers.get('Content-Type', '')

        if 'application/json' in content_type.lower():
            data = request.get_json(force=True)
        else:
            return jsonify({"error": "Only application/json supported"}), 400

        html_content = data.get('html', '')
        keywords = data.get('keywords', [])

        if not html_content:
            return jsonify({"error": "Missing 'html' field"}), 400
        if not isinstance(html_content, str):
            return jsonify({"error": "'html' must be a string"}), 400
        if not isinstance(keywords, list):
            return jsonify({"error": "'keywords' must be a list of strings"}), 400

        soup = BeautifulSoup(html_content, 'lxml')
        for tag in soup(["script", "style", "iframe", "canvas", "svg"]):
            tag.decompose()

        articles = soup.find_all('article')
        matches = []

        for article in articles:
            heading_tag = article.find(['h1', 'h2', 'h3'])
            heading = heading_tag.get_text(strip=True) if heading_tag else None
            text = article.get_text(separator=' ', strip=True)
            clean_text = html.unescape(text)
            clean_text = re.sub(r'\s+', ' ', clean_text)

            keyword_matches = []
            lower_text = clean_text.lower()
            for keyword in keywords:
                count = lower_text.count(keyword.lower())
                if count > 0:
                    keyword_matches.append({"keyword": keyword, "count": count})

            if keyword_matches:
                link_tag = article.find_parent('a') or article.find('a')
                article_url = link_tag['href'] if link_tag and link_tag.has_attr('href') else None
                matches.append({
                    "heading": heading,
                    "article_context": clean_text[:400],
                    "article_url": article_url,
                    "matched_keywords": keyword_matches
                })

        total_matched_articles = len(matches)
        total_keywords_matched = sum(
            sum(kw['count'] for kw in article['matched_keywords']) for article in matches
        )

        return jsonify({
            "total_matched_articles": total_matched_articles,
            "total_keywords_matched": total_keywords_matched,
            "matches": matches,
            "processing_time_seconds": round(time.time() - start_time, 2)
        })

    except Exception as e:
        logger.error("Error: %s", str(e))
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Server error",
            "details": str(e),
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
