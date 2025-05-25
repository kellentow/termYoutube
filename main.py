import yt_dlp, time, sys, threading, av, os, argparse, ctypes
from concurrent.futures import ThreadPoolExecutor
from endecoder import image_to_text, gen_ansi

parser = argparse.ArgumentParser(prog='TermYoutube',description='Shows youtube videos in the terminal!',epilog='Thanks for downloading!')
parser.add_argument('-q','--quality', type=int, default=5,help="color quality of the outputted video")
parser.add_argument('-w','--width', type=int, default=144,help="width of the outputted video")
parser.add_argument('-u','--url',help="Provide a Youtube video url (if not supplied requires interactive terminal)")
parser.add_argument('-i','--igndelt', action='store_true', help="Ignores time passing and outputs the video frame for frame")
args = parser.parse_args()

if os.name == 'nt':
    import ctypes

    # Enable ANSI escape sequences on < Windows 10
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
    mode = ctypes.c_ulong()
    kernel32.GetConsoleMode(handle, ctypes.byref(mode))
    kernel32.SetConsoleMode(handle, mode.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
sys.stdout.write("\033[?25l") # no more cursor
sys.stdout.write("\033[2J\033[H") # clear screen
sys.stdout.flush()

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
if __name__ == "__main__":
    ydl_opts = {
        'format': 'best/worst',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'noplaylist': True,
    }
    url = args.url
    if url is None:
        url = youtube_search_and_select()
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        stream_url = info['url']
        #print(stream_url)

# ------------------------------------------------------------------
# Producer: decode frames via PyAV
# ------------------------------------------------------------------
if __name__ == "__main__":
    frame_buffer = {}
    container = av.open(stream_url)
    video_stream = container.streams.video[0]
    fps = float(video_stream.average_rate) if video_stream.average_rate else 30.0
    buffer_lock = threading.Lock()
    executor = ThreadPoolExecutor(max_workers=16)
    width = args.width
    inflight = threading.Semaphore(60)
    running = True

def frame_to_text(frame_idx, img, cols=100): #wrapper for image_to_text
    try:
        text = image_to_text(img, cols=cols)
        with buffer_lock:
            frame_buffer[frame_idx] = text
    except KeyboardInterrupt:
        global running
        running = False #user wants to quit, disable just incase main thread doesn't catch it

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
    global container, video_stream, running
    last_frame_idx = 0
    while running:
        try:
            for frame_idx, frame in enumerate(container.decode(video=0), start=last_frame_idx):
                while len(frame_buffer.keys()) > 120: #limit buffered frames (2s at 60fps)
                    time.sleep(0.1)
                inflight.acquire() # block if already 60 pending
                img = frame.to_ndarray(format='rgb24')
                future = executor.submit(frame_to_text, frame_idx, img, width)
                future.add_done_callback(lambda _: inflight.release())
        except (av.error.EOFError, OSError) as e:
            print(f"Stream error: {e}. Reconnecting...")
            time.sleep(1)  # Wait before reconnecting
            container, video_stream = reconnect_stream()
        except KeyboardInterrupt:
            running = False
            break
        except Exception as e:
            print(f"Oops (Decoder): {e}")

if __name__ == "__main__":
    quality = args.quality
    gen_ansi(quality,False)
    # Start decoding thread
    decoder_thread = threading.Thread(target=producer, daemon=True)
    decoder_thread.start()
    time.sleep(1)    
    start_time = time.time()
    idx=-1
    
    try:
        while running:
            if not args.igndelt:
                current_time = time.time() - start_time
                percent_done = min(1,max(0,current_time/(video_stream.frames/fps)))
                idx = int(current_time * fps)
            else:
                idx+=1
                percent_done = min(1,max(0,idx/video_stream.frames))
                current_time = idx/fps
            with buffer_lock:
                if idx in frame_buffer:
                    frame = frame_buffer[idx]
                else:
                    time.sleep(0.1)
                    idx-=1
                    continue
                for key in list(frame_buffer.keys()):
                    if key < idx:
                        del frame_buffer[key]
            timestamp = f"[{secs_to_str(current_time)}-{secs_to_str(video_stream.frames/fps)}]"
            timeline_width = width - len(timestamp) - 5
            timeline = f" <{"-"*int(percent_done*timeline_width)}o{"-"*int((1-percent_done)*timeline_width)}> "
            frame += "\n"+timestamp+timeline
            sys.stdout.buffer.write(b"\033[0m\x1b[H" + frame.encode("utf-8"))
            sys.stdout.buffer.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\033[H\033[2JExiting.")
    except Exception as e:
        print(f"Oops: {e}")
    finally:
        running = False
        with buffer_lock:
            frame_buffer = {}
        decoder_thread.join()
        executor.shutdown(wait=True)