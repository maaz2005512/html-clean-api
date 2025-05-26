from flask import Flask, request, jsonify from bs4 import BeautifulSoup from flask_cors import CORS import traceback import logging import gc import time import html import re from dateutil import parser as dparser

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

app = Flask(name) CORS(app)

@app.route('/') def home(): return jsonify({ "message": "Welcome to HTML Cleaner API", "usage": "POST /clean with 'html' and optional 'keywords' fields" })

@app.route('/clean', methods=['POST']) def clean_html(): start_time = time.time() try: content_type = request.headers.get('Content-Type', '') if 'application/json' in content_type.lower(): data = request.get_json(force=True) else: return jsonify({"error": "Unsupported Content-Type"}), 400

html_content = data.get('html', '')
    keywords = data.get('keywords', [])

    if not html_content:
        return jsonify({"error": "Missing 'html' field"}), 400
    if not isinstance(keywords, list):
        return jsonify({"error": "'keywords' must be a list"}), 400

    soup = BeautifulSoup(html_content, 'lxml')
    for tag in soup(["script", "style", "iframe", "canvas", "svg"]):
        tag.decompose()

    articles = soup.find_all('article')
    matches = []
    total_keywords_matched = 0

    for article in articles:
        heading_tag = article.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        heading = heading_tag.get_text(strip=True) if heading_tag else None
        article_text = article.get_text(" ", strip=True)
        link_tag = article.find('a', href=True)
        article_url = link_tag['href'] if link_tag else None

        keyword_hits = []
        lower_text = article_text.lower()
        for keyword in keywords:
            count = lower_text.count(keyword.lower())
            if count > 0:
                keyword_hits.append({"keyword": keyword, "count": count})
                total_keywords_matched += 1

        if keyword_hits:
            matches.append({
                "heading": heading,
                "article_context": article_text[:500],
                "article_url": article_url,
                "matched_keywords": keyword_hits
            })

    processing_time = time.time() - start_time
    return jsonify({
        "total_matched_articles": len(matches),
        "total_keywords_matched": total_keywords_matched,
        "matches": matches,
        "processing_time_seconds": round(processing_time, 2)
    })

except Exception as e:
    logger.error(f"Error: {str(e)}")
    return jsonify({
        "error": "Internal Server Error",
        "details": str(e),
        "traceback": traceback.format_exc()
    }), 500

if name == 'main': import os port = int(os.environ.get('PORT', 5000)) app.run(host='0.0.0.0', port=port)

