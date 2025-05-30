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
            return jsonify({"error": "Unsupported Content-Type"}), 400

        html_content = data.get('html', '')
        keywords = data.get('keywords', [])

        if not html_content or not isinstance(html_content, str):
            return jsonify({"error": "Missing or invalid 'html' field"}), 400
        if not isinstance(keywords, list):
            return jsonify({"error": "'keywords' must be a list"}), 400

        soup = BeautifulSoup(html_content, 'lxml')
        articles = soup.find_all('article')

        keyword_map = {k.lower(): [] for k in keywords if k}
        total_articles = 0
        total_keywords_matched = 0

        for article in articles:
            article_text = article.get_text(separator=' ', strip=True)
            clean_text = html.unescape(article_text)
            clean_text = re.sub(r'\s+', ' ', clean_text)
            clean_text_lower = clean_text.lower()

            matched = []
            for keyword in keyword_map:
                count = clean_text_lower.count(keyword)
                if count >= 2:
                    matched.append((keyword, count))

            if matched:
                total_articles += 1
                h2 = article.find('h2')
                heading = h2.get_text(strip=True) if h2 else None

                # Try to extract URL from surrounding anchor tag
                parent_a = article.find_parent('a', href=True)
                article_url = parent_a['href'] if parent_a else ''

                # Try to parse date near heading
                date_text = ""
                if h2 and h2.next_sibling:
                    try:
                        date_match = re.search(
                            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b',
                            h2.next_sibling.get_text(strip=True) if hasattr(h2.next_sibling, 'get_text') else str(h2.next_sibling)
                        )
                        if date_match:
                            parsed_date = dparser.parse(date_match.group(0), fuzzy=True)
                            date_text = parsed_date.strftime('%Y-%m-%d')
                    except:
                        pass

                for keyword, count in matched:
                    keyword_map[keyword].append({
                        "heading": heading,
                        "url": article_url,
                        "date": date_text,
                        "count": count,
                        "article_context": clean_text[:500]
                    })
                    total_keywords_matched += 1

        result = {
            "total_matched_keywords": total_keywords_matched,
            "total_matched_articles": total_articles,
            "results": []
        }

        for keyword, articles in keyword_map.items():
            if articles:
                result["results"].append({
                    "keyword": keyword,
                    "total_matches": sum(a["count"] for a in articles),
                    "articles": articles
                })

        result["processing_time_seconds"] = round(time.time() - start_time, 2)
        return jsonify(result)

    except Exception as e:
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
