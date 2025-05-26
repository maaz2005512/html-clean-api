from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from dateutil import parser as dparser
import html
import re
import traceback
import time
import gc

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({"message": "HTML Keyword Extractor API"})

@app.route('/clean', methods=['POST'])
def clean_html():
    try:
        data = request.get_json(force=True)
        html_content = data.get('html', '')
        keywords = data.get('keywords', [])
        min_keyword_count = int(data.get('min_count', 2))

        soup = BeautifulSoup(html_content, 'lxml')

        results = []
        articles = soup.find_all('article')

        for article in articles:
            text = article.get_text(separator=' ', strip=True)
            clean_text = html.unescape(text)
            clean_text = re.sub(r'\s+', ' ', clean_text)

            lower_text = clean_text.lower()
            matched = []
            for k in keywords:
                if k.lower() in lower_text:
                    count = lower_text.count(k.lower())
                    if count >= min_keyword_count:
                        matched.append({"keyword": k, "count": count})

            if matched:
                heading_tag = article.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                heading = heading_tag.get_text(strip=True) if heading_tag else None

                url_tag = article.find_parent('a', href=True)
                article_url = url_tag['href'] if url_tag else None

                # Try to parse date if present
                date_match = re.search(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},\s+\d{4}\b', text)
                date = None
                if date_match:
                    try:
                        date = str(dparser.parse(date_match.group()).date())
                    except:
                        pass

                results.append({
                    "heading": heading,
                    "article_url": article_url,
                    "date": date,
                    "article_context": clean_text[:500],
                    "matched_keywords": matched
                })

        return jsonify({
            "total_matched_articles": len(results),
            "results": results
        })

    except Exception as e:
        gc.collect()
        return jsonify({
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
