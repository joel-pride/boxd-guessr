import random
import re
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow your frontend to talk to this backend locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/quiz/{username}")
def get_random_review(username: str):
    rss_url = f"https://letterboxd.com/{username}/rss/"
    response = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})

    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="User not found or feed unavailable")

    soup = BeautifulSoup(response.content, "xml")
    items = soup.find_all("item")

    # Filter out entries that are just ratings or lists (look for reviews with descriptions)
    valid_reviews = []
    for item in items:
        title_text = item.title.text if item.title else ""
        description_html = item.description.text if item.description else ""

        # Letterboxd titles in RSS look like: "Movie Title, Year - ★★★"
        # We extract the movie title by splitting at the last comma before the year
        match = re.match(r"^(.*?),\s\d{4}", title_text)
        if match and description_html:
            movie_title = match.group(1).strip()

            # Extract plain text from the HTML description block
            desc_soup = BeautifulSoup(description_html, "html.parser")

            # Remove the default paragraph Letterboxd adds ("Watched on...")
            for p in desc_soup.find_all("p"):
                if "Watched on" in p.text:
                    p.decompose()

            review_text = desc_soup.get_text().strip()

            # Only count it if they actually wrote a review, not just a star rating
            if review_text and len(review_text) > 10:
                valid_reviews.append({
                    "title": movie_title,
                    "review": review_text,
                    "link": item.link.text if item.link else ""
                })

    if not valid_reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this user.")

    # Pick a random one
    selected = random.choice(valid_reviews)

    # Mask the title inside the review text to prevent instant spoilers
    safe_title = re.escape(selected["title"])
    masked_review = re.sub(safe_title, "[MOVIE TITLE REDACTED]", selected["review"], flags=re.IGNORECASE)

    return {
        "review": masked_review,
        "correct_answer": selected["title"]
    }