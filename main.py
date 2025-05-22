import yt_dlp
import time, sys, threading
import av
from concurrent.futures import ThreadPoolExecutor
from endecoder import image_to_text, gen_ansi

# ------------------------------------------------------------------
# Helpers: helps with misc stuff
# ------------------------------------------------------------------
def secs_to_str(sec):
    mins, secs = divmod(sec, 60)
    hrs, mins = divmod(mins, 60)
    string = ""
    if hrs != 0:
        string += f"{hrs:.0f}:"
    if mins != 0:
        string += f"{int(mins):02d}:"
    string += f"{int(secs):02d}"
    return string

# ------------------------------------------------------------------
# Search and select YouTube video URL
# ------------------------------------------------------------------
def youtube_search_and_select():
    query = input("\033[2J\033[HSearch YouTube: ")
    search_term = f"ytsearch5:{query}"
    ydl_opts_search = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': True,
        'noplaylist': True,
        'format': 'best[ext=mp4]/worst',
    }
    print("This may take a moment")
    with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
        info = ydl.extract_info(search_term, download=False)
    entries = info.get('entries', [])
    if not entries:
        print("No results found.")
        sys.exit(1)
    print("\nSearch results:")
    for i, entry in enumerate(entries):
        title = entry.get('title', 'No title')
        duration = entry.get('duration', 0)
        if duration is not None:
            print(f"{i+1}. {title} [{secs_to_str(duration)}]")
    while True:
        choice = input(f"Select a video (1-{len(entries)}): ")
        if choice.isdigit() and 1 <= int(choice) <= len(entries):
            return entries[int(choice)-1]['url']
        print("Invalid choice, try again.")

# ------------------------------------------------------------------
# Fetch stream URL via yt-dlp
# ------------------------------------------------------------------
ydl_opts = {
    'format': 'best/worst',
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'noplaylist': True,
}
url = youtube_search_and_select()
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    stream_url = info['url']
    #print(stream_url)

# ------------------------------------------------------------------
# Producer: decode frames via PyAV
# ------------------------------------------------------------------
container = av.open(stream_url)
video_stream = container.streams.video[0]
fps = float(video_stream.average_rate) if video_stream.average_rate else 30.0
frame_buffer = {}
buffer_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=32)
width = 144

def frame_to_text(frame_idx, img, cols=100): #wrapper for image_to_text
    frame_buffer[frame_idx] = image_to_text(img, cols=cols)

def reconnect_stream():
    """Reconnect to the YouTube stream and return a new container and video stream."""
    global stream_url
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        stream_url = info['url']
    new_container = av.open(stream_url)
    new_video_stream = new_container.streams.video[0]
    return new_container, new_video_stream

def producer():
    global container, video_stream
    last_frame_idx = 0
    while True:
        try:
            for frame_idx, frame in enumerate(container.decode(video=0), start=last_frame_idx):
                while len(frame_buffer.keys()) > 1000:
                    time.sleep(0.1)  # Calm down
                img = frame.to_ndarray(format='rgb24')
                executor.submit(frame_to_text, frame_idx, img, cols=width)
                last_frame_idx = frame_idx + 1
        except (av.AVError, OSError) as e:
            print(f"Stream error: {e}. Reconnecting...")
            time.sleep(2)  # Wait before reconnecting
            container, video_stream = reconnect_stream()

if __name__ == "__main__":
    gen_ansi(5,False)
    # Start decoding thread
    decoder_thread = threading.Thread(target=producer, daemon=True)
    decoder_thread.start()
    time.sleep(1)    
    start_time = time.time()
    
    try:
        while True:
            current_time = time.time() - start_time
            percent_done = min(1,max(0,current_time/(video_stream.frames/fps)))
            idx = int(current_time * fps)
            with buffer_lock:
                if idx in frame_buffer:
                    frame = frame_buffer[idx]
                else:
                    time.sleep(0.1)
                    continue
                for key in list(frame_buffer.keys()):
                    if key < idx:
                        del frame_buffer[key]
            timestamp = f"[{secs_to_str(current_time)}-{secs_to_str(video_stream.frames/fps)}]"
            timeline_width = width - len(timestamp) - 5
            timeline = f" <{"-"*int(percent_done*timeline_width)}o{"-"*int((1-percent_done)*timeline_width)}> "
            frame += "\n"+timestamp+timeline
            sys.stdout.write("\033[0m\x1b[H" + frame)
            sys.stdout.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\033[H\033[2JExiting.")
    