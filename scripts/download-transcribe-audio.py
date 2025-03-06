import requests
import yt_dlp
import re
import os
import feedparser
from urllib.parse import urlparse
from pywhispercpp.model import Model

def is_audio_url(url):
    """
    Checks if the URL directly points to an audio file.
    """
    try:
        response = requests.head(url, allow_redirects=True)
        content_type = response.headers.get("Content-Type", "").lower()
        return content_type.startswith("audio/")
    except requests.RequestException as e:
        print("Error checking URL:", e)
        return False

def extract_audio_from_page(url):
    """
    Fetches the webpage HTML and extracts the first <audio> tag's src attribute.
    """
    try:
        response = requests.get(url)
        if response.status_code == 200:
            audio_match = re.search(r'<audio[^>]+src="([^"]+)"', response.text, re.IGNORECASE)
            if audio_match:
                return audio_match.group(1)  
        print("No <audio> tag found on the webpage.")
        return None
    except requests.RequestException as e:
        print("Error fetching webpage:", e)
        return None

def download_audio_file(url):
    """
    Downloads an audio file from a given direct URL.
    Returns the filename of the downloaded file.
    """
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            filename = url.split("/")[-1]  
            with open(filename, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Download complete! Saved as {filename}")
            return filename
        else:
            print("Failed to download. Server responded with:", response.status_code)
            return None
    except requests.RequestException as e:
        print("Error downloading file:", e)
        return None

def download_youtube_audio(youtube_url):
    """
    Downloads the best available audio from a YouTube video.
    Returns the filename of the downloaded MP3.
    """
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
            print("Downloading YouTube audio... Please wait.")
            info = ydl.extract_info(youtube_url, download=True)
            filename = f"{info['title']}.mp3"
            print(f"Download complete! File saved as {filename}")
            return filename
    except Exception as e:
        print("Error downloading YouTube audio:", e)
        return None

def is_youtube_url(url):
    """
    Checks if a URL is from YouTube.
    """
    youtube_patterns = [
        r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$"
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def is_podcast_rss_url(url):
    """
    Checks if a URL is likely a podcast RSS feed.
    This function performs both URL pattern matching and content checking.
    """
    try:
        parsed_url = urlparse(url)
        if (parsed_url.path.endswith('.xml') or 
            'rss' in parsed_url.path.lower() or 
            'feed' in parsed_url.path.lower()):
            return True
            
        # For URLs that don't have obvious patterns
        if 'feeds' in parsed_url.netloc.lower() or 'feeds' in parsed_url.path.lower():
            return True
    except:
        pass
        
    # If URL pattern doesn't match, try checking the content
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        
        # Check content type
        content_type = response.headers.get('Content-Type', '').lower()
        if 'xml' in content_type or 'rss' in content_type:
            return True
            
        # Check first few lines of content for RSS/XML indicators
        content_start = response.text[:1000].lower()
        if '<?xml' in content_start and ('<rss' in content_start or '<feed' in content_start):
            return True
    except:
        pass
        
    return False

def is_apple_podcasts_url(url):
    """
    Checks if a URL is from Apple Podcasts.
    """
    apple_patterns = [
        r"^(https?://)?(www\.)?podcasts\.apple\.com/.+$"
    ]
    return any(re.match(pattern, url) for pattern in apple_patterns)

def extract_rss_from_apple_podcasts(url):
    """
    Extracts the RSS feed URL from an Apple Podcasts page.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            # Look for the feed URL in the page content
            # Apple often includes it in a JSON-LD script tag
            feed_match = re.search(r'"feedUrl":\s*"([^"]+)"', response.text)
            if feed_match:
                return feed_match.group(1)  # Extract the feed URL
                
            # Alternative: look for a link with type="application/rss+xml"
            feed_link = re.search(r'<link[^>]+type="application/rss\+xml"[^>]+href="([^"]+)"', response.text)
            if feed_link:
                return feed_link.group(1)
                
        print("Couldn't find RSS feed URL on the Apple Podcasts page.")
        return None
    except requests.RequestException as e:
        print(f"Error fetching Apple Podcasts page: {e}")
        return None

def parse_podcast_rss(rss_url, download_latest=True):
    """
    Parses a podcast RSS feed and returns a list of episodes with their audio URLs.
    If download_latest is True, only returns the latest episode.
    """
    try:
        feed = feedparser.parse(rss_url)
        
        # Check if this is a valid podcast feed
        if not feed.entries:
            print("No episodes found in the RSS feed.")
            return []
        
        episodes = []
        for entry in feed.entries:
            title = entry.get('title', 'Unnamed Episode')
            
            # Find the audio enclosure
            audio_url = None
            for link in entry.get('links', []):
                if link.get('rel') == 'enclosure' and link.get('type', '').startswith('audio/'):
                    audio_url = link.get('href')
                    break
            
            # If no enclosure found, look for enclosures directly
            if not audio_url and 'enclosures' in entry:
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('audio/'):
                        audio_url = enclosure.get('href')
                        break
            
            if audio_url:
                episodes.append({
                    'title': title,
                    'audio_url': audio_url,
                    'published': entry.get('published', 'Unknown date')
                })
                
                # If we only want the latest episode, break after first entry since RSS feeds typically list episodes in reverse chronological order
                if download_latest and episodes:
                    break
        
        return episodes
    except Exception as e:
        print(f"Error parsing podcast RSS: {e}")
        return []

def download_podcast_episode(episode):
    """
    Downloads an episode from a podcast RSS feed.
    """
    print(f"Downloading podcast episode: {episode['title']}")
    
    # Generate a clean filename from the episode title
    clean_title = re.sub(r'[^\w\s-]', '', episode['title']).strip()
    clean_title = re.sub(r'[-\s]+', '-', clean_title)
    filename = f"{clean_title}.mp3"
    
    try:
        response = requests.get(episode['audio_url'], stream=True)
        if response.status_code == 200:
            with open(filename, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"Download complete! Saved as {filename}")
            return filename
        else:
            print(f"Failed to download. Server responded with: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error downloading file: {e}")
        return None

def transcribe_audio(audio_file):
    """
    Transcribes an audio file using Whisper model.
    """
    print(f"Transcribing {audio_file}...")
    
    # Load the Whisper model
    model = Model("models/ggml-medium.en.bin") 
    
    # Transcribe the audio file
    segments = model.transcribe(audio_file)
    
    # Convert list to string (join all elements)
    text = "\n".join([segment.text for segment in segments])
    
    # Generate output filename based on input filename
    output_filename = os.path.splitext(audio_file)[0] + "_transcription.txt"
    
    # Write the output to a text file
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(text)
    
    print(f"Transcription complete! Saved as {output_filename}")
    return output_filename

def main():
    """
    Main function to handle user input, download audio, and transcribe it.
    """
    print("Universal Audio Downloader and Transcriber")
    url = input("Enter a URL: ").strip()

    if not url:
        print("No URL entered. Please restart and try again.")
        return

    audio_filename = None
    
    if is_youtube_url(url):
        print("Detected YouTube URL. Using yt-dlp to download audio...")
        audio_filename = download_youtube_audio(url)
    
    elif is_apple_podcasts_url(url):
        print("Detected Apple Podcasts URL. Extracting RSS feed...")
        rss_url = extract_rss_from_apple_podcasts(url)
        if rss_url:
            print(f"Found RSS feed: {rss_url}")
            episodes = parse_podcast_rss(rss_url, download_latest=True)
            
            if episodes:
                latest_episode = episodes[0]
                print(f"Found latest episode: {latest_episode['title']} ({latest_episode['published']})")
                audio_filename = download_podcast_episode(latest_episode)
            else:
                print("No episodes found or RSS feed could not be parsed.")
        else:
            print("Failed to extract RSS feed from Apple Podcasts URL.")
    
    elif is_podcast_rss_url(url):
        print("Detected podcast RSS feed. Getting latest episode...")
        episodes = parse_podcast_rss(url, download_latest=True)
        
        if episodes:
            latest_episode = episodes[0]
            print(f"Found latest episode: {latest_episode['title']} ({latest_episode['published']})")
            audio_filename = download_podcast_episode(latest_episode)
        else:
            print("No episodes found or RSS feed could not be parsed.")
    
    elif is_audio_url(url):
        print("Direct audio file detected. Downloading...")
        audio_filename = download_audio_file(url)
    
    else:
        print("Checking for embedded audio on the webpage...")
        audio_src = extract_audio_from_page(url)
        if audio_src:
            print(f"Found embedded audio: {audio_src}")
            audio_filename = download_audio_file(audio_src)
        else:
            print("No audio file found on the page.")
    
    # Transcribe the downloaded audio if available
    if audio_filename and os.path.exists(audio_filename):
        transcribe_audio(audio_filename)
    else:
        print("No audio file available for transcription.")

if __name__ == "__main__":
    main()