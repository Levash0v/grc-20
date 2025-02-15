import requests
import sqlite3
from bs4 import BeautifulSoup

# URL of the page with the latest mathematics articles
ARXIV_URL = "https://arxiv.org/list/math/recent"

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
            pdf_link TEXT
        )
    ''')
    conn.commit()
    conn.close()

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

    # Process all articles
    for dt, dd in zip(articles_container.find_all("dt"), articles_container.find_all("dd")):
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
        if subjects_tag:
            subjects = subjects_tag.text.replace("Subjects:", "").strip()
            subjects = " ".join(subjects.split())  # Remove extra spaces and line breaks
        else:
            subjects = "No categories"

        articles.append((arxiv_id, title, authors, subjects, pdf_link))

    return articles

# Function to save data to SQLite
def save_to_db(articles):
    conn = sqlite3.connect("arxiv.db")
    cursor = conn.cursor()

    for article in articles:
        try:
            cursor.execute('''
                INSERT INTO articles (arxiv_id, title, authors, subjects, pdf_link)
                VALUES (?, ?, ?, ?, ?)
            ''', article)
        except sqlite3.IntegrityError:
            print(f"Article {article[0]} is already in the database")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_db()
    articles = scrape_arxiv()
    if articles:
        save_to_db(articles)
        print(f"Saved {len(articles)} articles to the database.")
    else:
        print("Failed to retrieve articles.")
