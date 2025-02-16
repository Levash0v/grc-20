import requests
import sqlite3
import csv
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# Constants
ARXIV_URL = "https://arxiv.org/list/math/recent?skip=0&show=2000"
CSV_FILENAME = "arxiv_articles.csv"
DB_FILENAME = "arxiv.db"
IMAGE_DIR = "images"
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"  # Update for your OS
IMAGE_SIZE = (2384, 640)

# Ensure image directory exists
os.makedirs(IMAGE_DIR, exist_ok=True)

def create_db():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arxiv_id TEXT UNIQUE,
            title TEXT,
            authors TEXT,
            subjects TEXT,
            pub_date TEXT,
            pdf_link TEXT,
            image_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def parse_date(raw_date):
    cleaned_date = re.sub(r"\s*\(.*\)", "", raw_date)
    try:
        parsed_date = datetime.strptime(cleaned_date, "%a, %d %b %Y")
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        return "Unknown"

def get_background_color(category):
    r = sum(ord(c) for c in category) % 256
    g = sum(ord(c) * 3 for c in category) % 256
    b = sum(ord(c) * 7 for c in category) % 256
    return (r, g, b)

def generate_image(title, authors, categories, arxiv_id):
    main_category = categories.split(";")[0].strip().split("(")[-1][:-1]
    bg_color = get_background_color(main_category)
    image = Image.new("RGB", IMAGE_SIZE, bg_color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_PATH, 50)
    text = f"{title}\n{authors}\n{categories}\n{arxiv_id}"
    draw.text((50, 50), text, fill="black", font=font)
    image_path = os.path.join(IMAGE_DIR, f"{arxiv_id.replace(':', '_')}.png")
    image.save(image_path)
    return image_path

def scrape_arxiv():
    response = requests.get(ARXIV_URL)
    if response.status_code != 200:
        print("Error loading the page")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    articles = []
    articles_container = soup.find("dl")
    if not articles_container:
        print("Article container not found")
        return []
    
    current_pub_date = "Unknown"
    article_elements = articles_container.find_all(["h3", "dt", "dd"])
    for element in article_elements:
        if element.name == "h3":
            current_pub_date = parse_date(element.text.strip())
        elif element.name == "dt":
            dt = element
            dd = dt.find_next_sibling("dd")
            if not dd:
                continue
            links = dt.find_all("a")
            if len(links) < 2:
                continue
            arxiv_id = links[1].text.strip()
            pdf_link = "https://arxiv.org" + links[2]["href"] if len(links) > 2 else "No link"
            title_tag = dd.find("div", class_="list-title mathjax")
            title = title_tag.text.replace("Title:", "").strip() if title_tag else "No title"
            authors_tag = dd.find("div", class_="list-authors")
            authors = authors_tag.text.replace("Authors:", "").strip() if authors_tag else "No authors"
            subjects_tag = dd.find("div", class_="list-subjects")
            subjects = " ".join(subjects_tag.text.replace("Subjects:", "").strip().split()) if subjects_tag else "No categories"
            image_path = generate_image(title, authors, subjects, arxiv_id)
            articles.append((arxiv_id, title, authors, subjects, current_pub_date, pdf_link, image_path))
    return articles

def save_to_db(articles):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    for article in articles:
        try:
            cursor.execute('''
                INSERT INTO articles (arxiv_id, title, authors, subjects, pub_date, pdf_link, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', article)
        except sqlite3.IntegrityError:
            print(f"Article {article[0]} is already in the database")
    conn.commit()
    conn.close()

def save_to_csv(articles):
    with open(CSV_FILENAME, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["arXiv ID", "Title", "Authors", "Subjects", "Publication Date", "PDF Link", "Image Path"])
        writer.writerows(articles)
    print(f"Saved {len(articles)} articles to {CSV_FILENAME}")

if __name__ == "__main__":
    create_db()
    articles = scrape_arxiv()
    if articles:
        save_to_db(articles)
        save_to_csv(articles)
        print(f"Saved {len(articles)} articles to the database and CSV file.")
    else:
        print("Failed to retrieve articles.")
