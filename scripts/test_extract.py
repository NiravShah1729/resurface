"""Test script to evaluate LLM extraction on 4 sample inputs."""

import json
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.llm import extract_save

SAMPLES = [
    {
        "category": "Book Reel Caption",
        "text": """
Instagram
Log in to like or comment.
Liked by reader_jen and 4,120 others
CAPTION:
If you loved The Martian, you NEED to read 'Project Hail Mary' by Andy Weir right now!
Ryland Grace wakes up alone on a spaceship with total amnesia and slowly discovers he is humanity's last hope to stop an extinction-level solar dimming crisis. 
Fast-paced, scientifically grounded, and hilarious. 10/10 sci-fi masterpiece.
View all 84 comments...
#scifi #projecthailmary #booktok #mustread
""",
    },
    {
        "category": "Movie Recommendation",
        "text": """
X / Twitter
Bookmark | Copy link | 18.2K Views
Recommendation of the day:
'Arrival' (2016) directed by Denis Villeneuve is a cinema masterpiece.
Amy Adams plays a brilliant linguist recruited by the military to communicate with mysterious alien visitors before geopolitical tensions trigger World War III.
A breathtaking meditation on time, language, and human connection. Available on Netflix.
#movies #cinematography #arrival #scifi
""",
    },
    {
        "category": "LinkedIn Job Post",
        "text": """
LinkedIn Feed
Promoted • 1st • Follow • 3d
We're hiring at CloudScale Systems! 🚀
We are looking for a Senior Backend Engineer (Python / FastAPI / Distributed Systems).
Location: Fully Remote (US/EU timezones)
Compensation: $160,000 - $190,000 + equity
Requirements: 5+ years with async Python, FastAPI, Docker, and PostgreSQL/Redis.
If you love building high-throughput APIs with clean architecture, click the link below to apply or DM me directly.
Link to apply: https://cloudscale.example.com/careers/sr-backend
#hiring #python #fastapi #backend #remotework
""",
    },
    {
        "category": "Coding Tutorial Reel Caption",
        "text": """
Reels • Instagram
Original audio • 12.4k shares • 320 comments
Save this reel before you forget! ⚡
Stop using bare `asyncio.gather()` in modern Python (3.11+). Use `asyncio.TaskGroup` instead!
TaskGroup gives you structured concurrency: if one task fails, all sibling tasks are safely and automatically cancelled, preventing silent dangling coroutines.
Example:
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(fetch_user())
    t2 = tg.create_task(fetch_orders())
Follow @python_craft for daily clean code tips.
#python #programming #asyncio #coding #developer
""",
    },
]


def main() -> None:
    print("=" * 60)
    print("Testing LLM extraction (app.llm.extract_save)...")
    print("=" * 60)

    for i, sample in enumerate(SAMPLES, 1):
        print(f"\n[{i}/4] Testing Sample: {sample['category']}")
        print("-" * 50)
        result = extract_save(sample["text"])
        print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print("Extraction test run completed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
