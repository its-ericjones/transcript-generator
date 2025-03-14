import requests
import yt_dlp
import re
import os
import feedparser
from pywhispercpp.model import Model

def sanitize_filename(filename, max_length=255):
    # Replace invalid characters with underscore
    filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
    
    # Replace multiple spaces/underscores with a single one
    filename = re.sub(r'[\s_]+', "_", filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(" .")
    
    # Truncate if too long (leave room for extension)
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        ext_len = len(ext)
        name = name[:max_length - ext_len - 1]
        filename = name + ext
        
    return filename

def validate_url(url):
    pattern = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(pattern.match(url))

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
        return download_podcast_episode(rss_url)
    
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
            raw_filename = f"{info['title']}.mp3"
            filename = sanitize_filename(raw_filename)
            
            # Handle if the sanitized filename is different from what yt-dlp created
            if raw_filename != filename:
                try:
                    os.rename(raw_filename, filename)
                except FileNotFoundError:
                    # If exact filename not found, look for similar files
                    mp3_files = [f for f in os.listdir() if f.endswith('.mp3') and f.startswith(info['title'][:10])]
                    if mp3_files:
                        os.rename(mp3_files[0], filename)
            
            print(f"Download complete: {filename}")
            return filename
    except Exception as e:
        print(f"Error downloading YouTube audio: {e}")
        return None
    
def download_podcast_episode(rss_url):
    # Handle None input case
    if rss_url is None:
        print("No valid RSS URL provided")
        return None
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
            return download_direct_audio(audio_url, title)
        else:
            print("No audio URL found in the podcast feed")
            return None
    except Exception as e:
        print(f"Error parsing podcast RSS: {e}")
        return None
    
def extract_rss_from_apple_podcasts(url):
    # Extracts RSS feed URL from Apple Podcasts page
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        feed_match = re.search(r'"feedUrl":\s*"([^"]+)"', response.text)
        if feed_match:
            return feed_match.group(1)
        else:
            return None
    except:
        return None

def download_direct_audio(url, custom_filename=None):
    # Downloads audio from a direct URL
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            if custom_filename:
                # Use custom filename with proper extension
                content_type = response.headers.get('Content-Type', '')
                ext = '.mp3'  # Default extension
                if 'audio/mpeg' in content_type:
                    ext = '.mp3'
                elif 'audio/wav' in content_type:
                    ext = '.wav'
                elif 'audio/ogg' in content_type:
                    ext = '.ogg'
                elif 'audio/aac' in content_type:
                    ext = '.aac'
                filename = sanitize_filename(f"{custom_filename}{ext}")
            else:
                # Extract filename from URL and sanitize
                raw_filename = url.split("/")[-1]
                filename = sanitize_filename(raw_filename)
            
            with open(filename, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Download complete: {filename}")
            return filename
    except requests.RequestException as e:
        print(f"Error downloading file: {e}")
    return None

def ensure_model_exists():
    model_dir = "models"
    model_path = os.path.join(model_dir, "ggml-medium.en.bin")
    
    if not os.path.exists(model_path):
        print(f"Whisper model not found at {model_path}")
        choice = input("Do you want to download the model now? (y/n): ").strip().lower()
        if choice == 'y':
            print("Please download the model from https://huggingface.co/ggerganov/whisper.cpp")
            print(f"and place it in {os.path.abspath(model_dir)}")
            os.makedirs(model_dir, exist_ok=True)
        return False
    
    return True

def transcribe_audio(audio_file):
    # Transcribes audio using Whisper model
    try:
        print(f"Transcribing {audio_file}...")
        
        # Check if file exists
        if not os.path.exists(audio_file):
            print(f"File not found: {audio_file}")
            return None
        
        # Check if model exists
        if not ensure_model_exists():
            print("Model not available. Transcription aborted.")
            return None
        
        # Initialize the model
        model = Model("models/ggml-medium.en.bin")
        
        # Transcribe the audio
        segments = model.transcribe(audio_file)
        text = "\n".join([segment.text for segment in segments])
        
        # Save the transcription
        output_filename = sanitize_filename(os.path.splitext(audio_file)[0] + "_transcription.txt")
        with open(output_filename, "w", encoding="utf-8") as file:
            file.write(text)
        
        print(f"Transcription saved as {output_filename}")
        return output_filename
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def main():
    print("Audio Downloader and Transcriber")
    url = input("Enter a URL: ").strip()
    
    if not url:
        print("No URL entered. Exiting.")
        return
    
    if not validate_url(url):
        print("Invalid URL format. Please enter a valid URL.")
        return
    
    print(f"Processing URL: {url}")
    audio_filename = download_audio(url)
    
    # Debugging output
    print(f"Audio filename: {audio_filename}")
    print(f"Current working directory: {os.getcwd()}")
    
    if audio_filename and os.path.exists(audio_filename):
        transcribe_audio(audio_filename)
    else:
        if audio_filename is None:
            print("Failed to download audio: No filename returned.")
        elif not os.path.exists(audio_filename):
            print(f"File does not exist: {audio_filename}")
        print("Failed to download audio for transcription.")

if __name__ == "__main__":
    main()