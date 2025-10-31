from dotenv import load_dotenv
import os

load_dotenv()

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
print(YOUTUBE_API_KEY)
