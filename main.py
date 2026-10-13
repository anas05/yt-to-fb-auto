import os
import feedparser
import requests
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi

CHANNEL_ID = os.environ.get("YT_CHANNEL_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

POSTED_VIDEOS_FILE = "posted_videos.txt"

def get_posted_videos():
    if os.path.exists(POSTED_VIDEOS_FILE):
        with open(POSTED_VIDEOS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_posted_video(video_id):
    with open(POSTED_VIDEOS_FILE, "a") as f:
        f.write(f"{video_id}\n")

def get_latest_video():
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
    feed = feedparser.parse(rss_url)
    
    if not feed.entries:
        print("No videos found in feed.")
        return None

    latest_entry = feed.entries[0]
    video_id = latest_entry.yt_videoid
    title = latest_entry.title
    link = latest_entry.link
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    return {
        "id": video_id,
        "title": title,
        "link": link,
        "thumbnail": thumbnail_url
    }

def get_transcript(video_id):
    try:
        ytt = YouTubeTranscriptApi()
        transcript_list = ytt.list_transcripts(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['ar', 'fr', 'en'])
        except:
            transcript = next(iter(transcript_list))

        data = transcript.fetch()
        full_text = " ".join([item['text'] for item in data])
        return full_text
    except Exception as e:
        print(f"Warning: Couldn't fetch transcript: {e}")
        return None

def generate_news_summary(title, transcript):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
Anta journalist w content creator f Facebook.
Swb post b l-Darija/العربية b style dyal News/Akhbar جذاب w professionel 3la had l-video.

Titre dyal video: {title}

Transcript dyal video:
{transcript if transcript else 'No transcript available. Base summary on the title.'}

L-Format dyal Post:
- Headline mchawqa (Headline / عنوان عاجل).
- Résumé dyal 3-5 nqat mhemin mn chno tgal f video.
- Call to Action sghir bach ychoufo la video kamla.
- Hashtags mnasbin.

Ma-tdirch مقدمات b7al "Ha howa l-post". A3tini l-texte dyal l-post direct!
"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

def post_to_facebook(message, image_url, video_link):
    full_message = f"{message}\n\n📌 Chahd l-video kamel hna: {video_link}"
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    
    payload = {
        "url": image_url,
        "caption": full_message,
        "access_token": FB_ACCESS_TOKEN
    }
    
    res = requests.post(url, data=payload)
    if res.status_code == 200:
        print("Successfully posted to Facebook!")
        return True
    else:
        print(f"Error posting to Facebook: {res.text}")
        return False

def main():
    posted_videos = get_posted_videos()
    video = get_latest_video()

    if not video:
        print("No video found.")
        return

    print(f"Latest Video ID: {video['id']} - Title: {video['title']}")

    if video['id'] in posted_videos:
        print("Video already posted. Skipping...")
        return

    print("Fetching transcript...")
    transcript = get_transcript(video['id'])

    print("Generating news summary with Gemini...")
    summary = generate_news_summary(video['title'], transcript)

    print("Posting to Facebook Page...")
    success = post_to_facebook(summary, video['thumbnail'], video['link'])

    if success:
        save_posted_video(video['id'])
        print("Done!")

if __name__ == "__main__":
    main()
