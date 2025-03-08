# Script Breakdown
## Table of Contents
  - [Libraries](#libraries)
    - [Built In Libraries](#built-in-libraries)
    - [Required Libraries](#required-libraries)
  - [The Main Function](#the-main-function)
  - [The URL Parser / Universal Downloader](#the-url-parser--universal-downloader)
  - [Downloading from YouTube](#downloading-from-youtube)
  - [Handling Direct Audio](#handling-direct-audio)
  - [Working with Apple Podcasts](#working-with-apple-podcasts)
  - [Downloading from Podcast RSS Feeds](#downloading-from-podcast-rss-feeds)
  - [Transcribing the Audio](#transcribing-the-audio)

## Libraries

### Built In Libraries

- `os`: provides a way to interact with the operating system directly from Python
- `re`: a library that is used for working with regular expressions (patterns used to match and manipulate strings)

### Required Libraries

- `requests`: handles HTTP operations for direct downloads and webpage scraping
- `yt_dlp`: a library that is used for downloading video from YouTube
- `feedparser`: parses RSS feeds 
- `pywhispercpp`: C/C++ port of OpenAI's original Whisper model (a model specific to ASR - Automatic Speech Recognition) that is more optimized for CPU execution versus being more GPU intensive 

## The Main Function

```python
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
```

This function is starting point of the entire program that coordinates the two main tasks - downloading an audio file and then transcribing it. 

1. A prompt input `("Enter a URL: ")` asks the user to enter in a URL which is then stripped of any whitespace by the `.strip()` method to help prevent any errors when the URL gets processed. 
2. If no URL is entered then the program stops itself. 
3. Confirmation of the URL is printed and then the `download_audio()` function is called which contains all the instructions to determine the type of URL and how to download it. 
4. If the download is successful, then the filename of the audio file is returned and is ready to be used for transcription. However if the download fails for any reason, then `None` is returned. 
5. A two-part verification begins to see if `audio_filename` is not `None` which means that the download didn't fail, and also checks to see that the download file exists on the disk. Once both of these verifications are checked, the program calls the `transcribe_audio()` function with the downloaded file which handles the speech-to-text conversion. 
6. If either verification fails, then an error message is printed. 

## The URL Parser / Universal Downloader

```python
def download_audio(url):
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
        audio_match = re.search(r'%3Caudio[^%3E]+src="([^"]+)"', response.text, re.IGNORECASE)
        if audio_match:
            return download_direct_audio(audio_match.group(1))
    except requests.RequestException:
        pass
    
    return None
```

This function is the heart of the program. It flows from top to bottom until a successful check is found. Once the URL is validated, it is passed along to the appropriate downloader.

1. **YouTube Check**: The first check is to see if the URL is from YouTube. It looks for either "youtube.com" or "youtu.be" (YouTube's official URL shortener) in the URL. If it's determined that the URL is from YouTube, the URL is passed on to the `download_youtube_audio()` function as the value to be used.
2. **Podcast RSS Feed Check**: This second check is ran due to the URL not matching any patterns from YouTube. It looks for "xml", "rss", or "feed" in the URL to identify podcast feeds. RSS (Really Simple Syndication) feeds are standardized XML documents that podcast platforms use to distribute metadata about episodes, including audio file URLs. If it's determined that the URL is from a podcast RSS feed, the URL is passed on to the `download_podcast_episode()` function as the value to be used.
3. **Apple Podcasts**: This third check is ran due to the URL not matching either patterns from YouTube or a podcast RSS feed. Since Apple Podcasts don't expose RSS feeds directly in their URLs, the function `extract_rss_from_apple_podcasts()` is ran to try and locate the actual RSS feed URL from the webpage content. If it's determined that the URL is from Apple Podcasts, the URL is passed on to the the `download_podcast_episode()` function as the value to be used. Even though the URL is being passed onto the same function as a normal RSS feed would be, the specific value is being returned is the URL from the `extract_rss_from_apple_podcasts()` function.
4. **Direct Audio and Web Scraping**: This grouped fourth and fifth checks are ran due to the URL not matching YouTube, Podcast RSS Feed, or Apple Podcasts. Both these checks are wrapped in a try-except block that catches any network, timeout, and HTTP errors. If any of these errors occur, the function continues to the end.
    - **HEAD Request**: This check first makes a lightweight HTTP HEAD request (only fetching the headers, not actual content) to see if the URL is pointing directly to an audio file. Headers provide metadata about the page that help the browser and server determine how to handle the data. The `allow_redirects=True` parameter makes sure that the request follows any HTTP redirects, which is common for download links. If it's determined that the URL is from an audio file, the URL is passed onto the `download_direct_audio()` function as the value to be used.
    - **HTML Parsing**: If the header check doesn't validate that the URL is pointing directly to an audio file, it makes a full GET request to download the entire webpage content. It uses a regular expression to search for any `<audio>` tags with `src` attributes which are common indicators of embedded audio players. The group part of `(audio_match.group(1))` refers to only extracting the URL from the larger search result, an example being `<audio id="episode-player" src="https://media.example.com/podcasts/episode42.mp3">`.
## Downloading from YouTube

```python
def download_youtube_audio(youtube_url):
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
```

1. **Configuring Download Options**: A dictionary is created to hold the options that control how `yt_dlp` behaves.
	-  `'format': 'bestaudio/best'`: This tells `yt_dlp` to prefer the highest quality audio stream available. If no audio-only stream is available, it will fall back to the best available format (which could include video) and extract the audio.
    - `'postprocessors'`: This is an array of post-processing operations that gets applied to the downloaded content:
        - `'key': 'FFmpegExtractAudio'`: Use FFmpeg (an external media processing tool) to extract the audio track.
        - `'preferredcodec': 'mp3'`: Convert the extracted audio to MP3 format.
        - `'preferredquality': 'best'`: Use the highest quality setting for the MP3 conversion.
    - `'outtmpl': '%(title)s.%(ext)s'`: This sets the output template for the filename. `%(title)s` is replaced with the video's title, and `%(ext)s` is replaced with the file extension (.mp3).
2. **The Download Process**: The entire download process is wrapped in a try-except block to catch any exceptions that might occur during the download process, such as network errors, YouTube API changes, or processing failures, and ensure that it won't crash due to any these.
	- `with yt_dlp.YoutubeDL(options) as ydl`: creates a context manager that ensures proper setup and cleanup of the YoutubeDL object, even if errors occur
	- `print("Downloading YouTube audio...")`: Informs user that the download has started
	- `info = ydl.extract_info(youtube_url, download=True)`:
		- Extracts metadata about the video (title, formats available, etc.)
        - Downloads the content according to the specified options (`download=True`)
    - The extracted info is stored in the `info` dictionary
3. **Filename construction**: `filename = f"{info['title']}.mp3"` creates the expected filename using the video's title from the extracted info. 
4. **Success notification**: Prints a confirmation message with the filename.
5. **Return value**: Returns the filename on success, which will be used by the main function to locate the file for transcription. If an error happens to occur, it returns `None` to indicate failure.
## Handling Direct Audio 

```python
def download_direct_audio(url):
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
```

This function handles direct downloads of audio files using the `requests` library. Similar to the `download_youtube_audio()` function, it is being wrapped in a try-except block for catching any network issues, and ensure that it won't crash due to any errors that may occur.
1. **HTTP request**: `response = requests.get(url, stream=True)` initiates an HTTP GET request to download the file. The `stream=True` parameter:
    - Tells `requests` to download the response body in chunks rather than all at once which allows handling large files without loading the entire file into memory
    - The connection remains open, which is more efficient for large downloads
2. **Status code verification**: `if response.status_code == 200:` checks if the HTTP request was successful. A status code of 200 means "OK" in HTTP. This ensures that the function proceeds if the server responded positively.
3. **Filename extraction**: `filename = url.split("/")[-1]` extracts the filename from the URL by:
    - Splitting the URL at each "/" character, creating a list of URL segments
    - Taking the last segment (`[-1]` index), which typically contains the filename
4. **File writing with chunking**: Instead of loading the entire file into memory, chunking breaks the download into smaller pieces, processing data as it arrives rather than waiting for the complete file to download.
    - `with open(filename, "wb") as file:` opens a file in binary write mode ("wb")
    - The `with` statement creates a context manager that ensures the file is properly closed even if an error occurs
    - `for chunk in response.iter_content(1024):` iterates through the content in chunks of 1024 bytes (1 KB)
    - `file.write(chunk)` writes each chunk to the file
5. **Success notification**: Prints a confirmation message with the filename.
6. **Return value**: The function returns the filename on success, which will be used for transcription. If an error happens to occur, it returns `None` to indicate failure.
## Working with Apple Podcasts
Apple Podcasts requires a special approach because the webpage doesn't directly provide the audio file. Instead, we need to find the RSS feed URL first. Apple Podcasts pages contain JSON data with a "feedUrl" property that points to the actual RSS feed.

```python
def extract_rss_from_apple_podcasts(url):
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
```

This function uses web scraping to extract the RSS feed URL. As with other functions, it is wrapped in a try-except block to catch any exception and ensure that it won't crash due to any errors.
1. **Custom headers**: `headers = {'User-Agent': 'Mozilla/5.0'}` sets a User-Agent header to mimic a web browser. This is important because:
    - Some websites block or provide different content to automated scripts so setting a browser-like User-Agent can help avoid these restrictions
2. **HTTP request**: `response = requests.get(url, headers=headers)` makes a GET request to the Apple Podcasts URL, including the custom headers. This downloads the HTML content of the page.
3. **Regular expression search**: `feed_match = re.search(r'"feedUrl":\s*"([^"]+)"', response.text)` uses a regular expression to find the RSS feed URL:
    - `"feedUrl":` looks for the exact string "feedUrl": which is part of the JSON data embedded in Apple Podcasts pages
    - `\s*` matches any whitespace characters (spaces, tabs) between "feedUrl": and the URL
    - `"([^"]+)"` captures text inside double quotes, where:
        - `(` and `)` create a capture group to extract the URL
        - `[^"]+` matches one or more characters that are not double quotes
        - This effectively captures everything between the quotes after "feedUrl":
4. **Conditional return**: A conditional expression is used to:
    - Return the first capture group (the URL) if a match was found
    - Return `None` if no match was found
## Downloading from Podcast RSS Feeds
Even though RSS feeds follow a standardized XML format, their structure can vary due to different reasons such as varying RSS versions, optional elements, automated generator differences, etc. XML provides syntax rules but doesn't define specific tags or their meanings. This function attempts to handle these complexities in a few ways. As with other functions, it is wrapped in a try-except block to catch any exception and ensure that it won't crash due to any errors that may occur.

```python
def download_podcast_episode(rss_url):
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
```

1. **RSS parsing**: `feed = feedparser.parse(rss_url)` uses the feedparser library to download and parse the RSS feed. Feedparser is specialized for handling [RSS](https://en.wikipedia.org/wiki/RSS) and [Atom](https://en.wikipedia.org/wiki/Atom_(web_standard)) feeds, accommodating the many variations and inconsistencies in feed formats.
2. **Empty feed check**: `if not feed.entries:` verifies that the feed contains at least one entry (episode). Some feeds might be valid XML but contain no episodes, such as new or discontinued podcasts.
3. **Episode selection**: `entry = feed.entries[0]` selects the first episode in the feed, which is typically the most recent episode (RSS feeds are usually sorted with newest first). 
4. **Title extraction**: `title = entry.get('title', 'Unnamed Episode')` gets the episode title, using a default value of 'Unnamed Episode' if no title is found.
5. **Audio URL extraction**: Multiple methods are being used due to RSS feeds providing media links either through dedicated enclosure elements or as specially tagged links.
    - **Enclosures method**:
        - `if hasattr(entry, 'enclosures'):` checks if the entry has an enclosures attribute, which is the standard way to include media in RSS
        - Loops through all enclosures to find one with an audio MIME type (a standard identifier that indicates the format of an audio file e.g., 'audio/mpeg', 'audio/mp3)
        - `enclosure.get('type', '').startswith('audio/')` identifies audio files by their MIME type 
        - Extracts the URL from the 'href' attribute if found
    - **Links method**:
        - If no audio URL is found in enclosures, checks the 'links' list
        - Looks for links with 'rel' set to 'enclosure' and 'type' starting with 'audio/'
6. **Download initiation**: If an audio URL is found, the episode title is printed and calls the `download_direct_audio()` function to download the file, passing along the return value.
## Transcribing the Audio
After successfully downloading the audio, this function is ran to convert the audio into text.

```python
def transcribe_audio(audio_file):
    print(f"Transcribing {audio_file}...")
    model = Model("models/ggml-medium.en.bin")
    segments = model.transcribe(audio_file)
    text = "\n".join([segment.text for segment in segments])
    
    output_filename = os.path.splitext(audio_file)[0] + "_transcription.txt"
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(text)
    
    print(f"Transcription saved as {output_filename}")
    return output_filename
```

1. **User notification**: `print(f"Transcribing {audio_file}...")` informs the user that the transcription process has started.
2. **Model loading**: `model = Model("models/ggml-medium.en.bin")` loads the Whisper speech recognition model:
    - 'ggml' refers to the optimized format for efficient inference
    - 'medium' refers to the model size (this particular one balances accuracy and performance)
    - '.en' indicates it's optimized for English (though Whisper can handle multiple languages)
3. **Transcription process**: `segments = model.transcribe(audio_file)` performs the actual transcription:
    - Whisper breaks audio into segments (usually sentence-like units)
    - The model processes each segment and converts it to text
    - This segmentation helps with both accuracy and memory management
4. **Text assembly**: `text = "\n".join([segment.text for segment in segments])` combines all the transcribed segments into a single text document:
    - `[segment.text for segment in segments]` is a list comprehension that extracts the text from each segment
    - `"\n".join(...)` joins these text pieces with newline characters, creating paragraph-like separation between segments
5. **Output filename creation**: `output_filename = os.path.splitext(audio_file)[0] + "_transcription.txt"`generates a filename for the transcription:
    - `os.path.splitext(audio_file)[0]` removes the file extension from the audio filename
    - `+ "_transcription.txt"` appends "transcription.txt" to create the new filename
    - This ensures the transcription file is named similarly to the audio file for easy association
6. **File writing**: The function opens a new text file and writes the transcription into it.
7. **Completion notification**: Informs the user that the transcription is complete and where the file is saved.
8. **Return value**: The function returns the output filename, which could be used for further processing (not currently needed but can be used for future iterations).