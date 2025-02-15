import requests
import sqlite3
import csv
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Updated URL to fetch more articles
ARXIV_URL = "https://arxiv.org/list/math/recent?skip=0&show=2000"
CSV_FILENAME = "arxiv_articles.csv"

# Function to create the database
def create_db():
    conn = sqlite3.connect("arxiv.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arxiv_id TEXT UNIQUE,
            title TEXT,
            authors TEXT,
            subjects TEXT,
            pub_date TEXT,
            pdf_link TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Function to parse publication date into YYYY-MM-DD format
def parse_date(raw_date):
    """Extracts and converts a raw date string like 'Fri, 14 Feb 2025 (showing 191 of 191 entries )' to '2025-02-14'."""
    cleaned_date = re.sub(r"\s*\(.*\)", "", raw_date)  # Remove everything in parentheses
    try:
        parsed_date = datetime.strptime(cleaned_date, "%a, %d %b %Y")
        return parsed_date.strftime("%Y-%m-%d")  # Convert to YYYY-MM-DD format
    except ValueError:
        return "Unknown"  # Fallback if parsing fails

# Function to scrape the page
def scrape_arxiv():
    response = requests.get(ARXIV_URL)
    if response.status_code != 200:
        print("Error loading the page")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = []

    # Find the container with articles
    articles_container = soup.find("dl")
    if not articles_container:
        print("Article container not found")
        return []

    # Iterate through each publication date and corresponding articles
    current_pub_date = "Unknown"
    article_elements = articles_container.find_all(["h3", "dt", "dd"])

    for element in article_elements:
        if element.name == "h3":
            # If the element is <h3>, update the current publication date
            current_pub_date = parse_date(element.text.strip())  # Convert to YYYY-MM-DD
        elif element.name == "dt":
            dt = element
            dd = dt.find_next_sibling("dd")
            if not dd:
                continue

            # Find links inside <dt>
            links = dt.find_all("a")
            if len(links) < 2:
                continue  # Skip if the second <a> is missing

            arxiv_id = links[1].text.strip()  # Article ID
            pdf_link = "https://arxiv.org" + links[2]["href"] if len(links) > 2 else "No link"

            # Article title
            title_tag = dd.find("div", class_="list-title mathjax")
            title = title_tag.text.replace("Title:", "").strip() if title_tag else "No title"

            # Article authors
            authors_tag = dd.find("div", class_="list-authors")
            authors = authors_tag.text.replace("Authors:", "").strip() if authors_tag else "No authors"

            # Article subjects
            subjects_tag = dd.find("div", class_="list-subjects")
            subjects = " ".join(subjects_tag.text.replace("Subjects:", "").strip().split()) if subjects_tag else "No categories"

            # Save article data
            articles.append((arxiv_id, title, authors, subjects, current_pub_date, pdf_link))

    return articles

# Function to save data to SQLite
def save_to_db(articles):
    conn = sqlite3.connect("arxiv.db")
    cursor = conn.cursor()

    for article in articles:
        try:
            cursor.execute('''
                INSERT INTO articles (arxiv_id, title, authors, subjects, pub_date, pdf_link)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', article)
        except sqlite3.IntegrityError:
            print(f"Article {article[0]} is already in the database")

    conn.commit()
    conn.close()

# Function to save data to CSV
def save_to_csv(articles):
    with open(CSV_FILENAME, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["arXiv ID", "Title", "Authors", "Subjects", "Publication Date", "PDF Link"])  # Header
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
