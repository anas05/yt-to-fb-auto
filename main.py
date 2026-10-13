import os
import requests
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL

CHANNEL_HANDLE = "https://www.youtube.com/@CaraLanelle/videos"
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
    print(f"DEBUG: Fetching latest video from -> {CHANNEL_HANDLE}")
    ydl_opts = {
        'playlist_items': '1',
        'extract_flat': 'in_playlist',
        'quiet': True,
        'no_warnings': True
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(CHANNEL_HANDLE, download=False)
            if not info or 'entries' not in info or not info['entries']:
                print("No videos found.")
                return None
            
            latest = info['entries'][0]
            video_id = latest.get('id')
            title = latest.get('title')
            link = f"https://www.youtube.com/watch?v={video_id}"
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

            return {
                "id": video_id,
                "title": title,
                "link": link,
                "thumbnail": thumbnail_url
            }
    except Exception as e:
        print(f"Error fetching via yt-dlp: {e}")
        return None

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
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
