from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from flask_cors import CORS
from dateutil import parser as dparser
import traceback
import logging
import gc
import time
import html
import re
from datetime import datetime

# Configure logging
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
        data = request.get_json(force=True)
        html_content = data.get('html', '')
        keywords = data.get('keywords', [])

        if not html_content or not isinstance(html_content, str):
            return jsonify({"error": "Invalid or missing 'html' field"}), 400
        if not isinstance(keywords, list):
            return jsonify({"error": "'keywords' must be a list of strings"}), 400

        soup = BeautifulSoup(html_content, 'lxml')
        for tag in soup(['script', 'style', 'iframe', 'canvas', 'svg']):
            tag.decompose()

        articles = soup.find_all('article')
        results = []
        keyword_total_count = {}

        for keyword in keywords:
            keyword_total_count[keyword.lower()] = 0

        for article in articles:
            heading_tag = article.find(['h1', 'h2', 'h3'])
            heading = heading_tag.get_text(strip=True) if heading_tag else None
            article_text = article.get_text(separator=' ', strip=True)
            article_text_clean = html.unescape(article_text)
            article_text_clean = re.sub(r'[\r\n\t]+', ' ', article_text_clean)
            article_text_clean = re.sub(r' +', ' ', article_text_clean)

            matched = []
            matched_count = 0
            keyword_count = {}

            for keyword in keywords:
                count = article_text_clean.lower().count(keyword.lower())
                if count >= 2:
                    matched.append({"keyword": keyword, "count": count})
                    keyword_total_count[keyword.lower()] += count
                    matched_count += count

            if matched:
                date_text = article_text_clean[:300]  # limit scope for faster match
                date_match = re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b', date_text)
                date = None
                if date_match:
                    try:
                        date = str(dparser.parse(date_match.group(), fuzzy=True).date())
                    except:
                        date = None

                a_tag = article.find_parent('a') or article.find('a')
                article_url = a_tag['href'] if a_tag and a_tag.has_attr('href') else None

                results.append({
                    "heading": heading,
                    "article_context": article_text_clean[:1000],
                    "article_url": article_url,
                    "date": date,
                    "matched_keywords": matched
                })

        total_keywords_matched = sum(keyword_total_count.values())

        processing_time = time.time() - start_time
        response = {
            "total_matched_articles": len(results),
            "total_keywords_matched": total_keywords_matched,
            "matches": results,
            "processing_time_seconds": round(processing_time, 2)
        }
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing HTML: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Processing Error",
            "details": str(e),
            "type": type(e).__name__
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
