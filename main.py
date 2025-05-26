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
    return jsonify({"message": "Welcome to HTML Cleaner API"})

@app.route('/clean', methods=['POST'])
def clean_html():
    start_time = time.time()
    try:
        data = request.get_json()
        html_content = data.get('html', '')
        keywords = data.get('keywords', [])

        if not html_content or not isinstance(html_content, str):
            return jsonify({"error": "Invalid or missing 'html' content"}), 400
        if not isinstance(keywords, list):
            return jsonify({"error": "'keywords' must be a list"}), 400

        soup = BeautifulSoup(html_content, 'lxml')
        articles = soup.find_all('article')
        matches = []
        total_keyword_hits = 0

        for article in articles:
            text = article.get_text(separator=' ', strip=True)
            clean_text = html.unescape(text)
            clean_text = re.sub(r'[\r\n\t]+', ' ', clean_text)
            clean_text = re.sub(r'[ ]{2,}', ' ', clean_text)
            lower_text = clean_text.lower()

            keyword_hits = []
            for keyword in keywords:
                if keyword.lower() in lower_text:
                    count = lower_text.count(keyword.lower())
                    total_keyword_hits += count
                    keyword_hits.append({"keyword": keyword, "count": count})

            if keyword_hits:
                heading = article.find(['h1', 'h2', 'h3'])
                heading_text = heading.get_text(strip=True) if heading else None

                # Extract date near heading
                date_text = None
                if heading:
                    next_siblings_text = ''
                    for sib in heading.find_all_next(string=True, limit=5):
                        next_siblings_text += sib + ' '
                    date_match = re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b', next_siblings_text)
                    if date_match:
                        date_text = date_match.group(0)

                link_tag = article.find_previous('a', class_='story-link')
                article_url = link_tag['href'] if link_tag and link_tag.has_attr('href') else None

                matches.append({
                    "heading": heading_text,
                    "article_context": clean_text[:500],
                    "article_url": article_url,
                    "date": date_text,
                    "matched_keywords": keyword_hits
                })

        processing_time = time.time() - start_time

        return jsonify({
            "total_matched_articles": len(matches),
            "total_keywords_matched": total_keyword_hits,
            "matches": matches,
            "processing_time_seconds": round(processing_time, 2)
        })

    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
