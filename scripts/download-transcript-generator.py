import requests
import yt_dlp
import re
import os
import feedparser
from pywhispercpp.model import Model

def download_audio(url):
    # Universal function to download audio from various source types.
    # Returns the filename of the downloaded file.
    # Check if YouTube URL
    if "youtube.com" in url or "youtu.be" in url:
        return download_youtube_audio(url)
    
    # Check if podcast RSS feed
    if "xml" in url or "rss" in url or "feed" in url:
        return download_podcast_episode(url)
    
    # Check if Apple Podcasts
    if "podcasts.apple.com" in url:
        rss_url = extract_rss_from_apple_podcasts(url)
        return download_podcast_episode(rss_url) if rss_url else None
    
    # Try direct download or extracting from page
    try:
        # Try direct download first
        response = requests.head(url, allow_redirects=True)
        if response.headers.get("Content-Type", "").lower().startswith("audio/"):
            return download_direct_audio(url)
        
        # If not direct audio, check for embedded audio
        response = requests.get(url)
        audio_match = re.search(r'<audio[^>]+src="([^"]+)"', response.text, re.IGNORECASE)
        if audio_match:
            return download_direct_audio(audio_match.group(1))
    except requests.RequestException:
        pass
    
    return None

def download_youtube_audio(youtube_url):
    # Downloads audio from a YouTube video
    options = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': 'best',
        }],
        'outtmpl': '%(title)s.%(ext)s',
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            print("Downloading YouTube audio...")
            info = ydl.extract_info(youtube_url, download=True)
            filename = f"{info['title']}.mp3"
            print(f"Download complete: {filename}")
            return filename
    except Exception as e:
        print(f"Error downloading YouTube audio: {e}")
        return None

def download_direct_audio(url):
    # Downloads audio from a direct URL
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            filename = url.split("/")[-1]
            with open(filename, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Download complete: {filename}")
            return filename
    except requests.RequestException as e:
        print(f"Error downloading file: {e}")
    return None

def extract_rss_from_apple_podcasts(url):
    # Extracts RSS feed URL from Apple Podcasts page
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        feed_match = re.search(r'"feedUrl":\s*"([^"]+)"', response.text)
        return feed_match.group(1) if feed_match else None
    except:
        return None

def download_podcast_episode(rss_url):
    # Downloads the latest episode from a podcast RSS feed
    try:
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            print("No episodes found in RSS feed")
            return None
        
        # Get the first (latest) episode
        entry = feed.entries[0]
        title = entry.get('title', 'Unnamed Episode')
        
        # Find audio URL
        audio_url = None
        # Check for enclosures
        if hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('audio/'):
                    audio_url = enclosure.get('href')
                    break
        
        # Check for links if no enclosure found
        if not audio_url:
            for link in entry.get('links', []):
                if link.get('rel') == 'enclosure' and link.get('type', '').startswith('audio/'):
                    audio_url = link.get('href')
                    break
        
        if audio_url:
            print(f"Downloading podcast: {title}")
            return download_direct_audio(audio_url)
        else:
            print("No audio URL found in the podcast feed")
            return None
    except Exception as e:
        print(f"Error parsing podcast RSS: {e}")
        return None

def transcribe_audio(audio_file):
    # Transcribes audio using Whisper model
    print(f"Transcribing {audio_file}...")
    model = Model("models/ggml-medium.en.bin")
    segments = model.transcribe(audio_file)
    text = "\n".join([segment.text for segment in segments])
    
    output_filename = os.path.splitext(audio_file)[0] + "_transcription.txt"
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(text)
    
    print(f"Transcription saved as {output_filename}")
    return output_filename

def main():
    print("Audio Downloader and Transcriber")
    url = input("Enter a URL: ").strip()
    
    if not url:
        print("No URL entered. Exiting.")
        return
    
    print(f"Processing URL: {url}")
    audio_filename = download_audio(url)
    
    if audio_filename and os.path.exists(audio_filename):
        transcribe_audio(audio_filename)
    else:
        print("Failed to download audio for transcription.")

if __name__ == "__main__":
    main()