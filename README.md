# TermYoutube
A terminal client for YouTube that can be used almost anywhere.

## Features
- **Search YouTube videos**: Search for videos directly from the terminal.
- **Stream video as ANSI art**: Watch YouTube videos rendered as ANSI art in your terminal.
- **Reconnect on stream errors**: Automatically reconnects to the stream if an error occurs.
- **Customizable quality**: Adjust the ANSI art quality and terminal width.

## Requirements
- Python 3.8+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [PyAV](https://github.com/PyAV-Org/PyAV)
- OpenCV (`cv2`)

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/kellentow/termYoutube.git
   cd termYoutube
   ```
2. Install the required dependencies:
    ```bash
    pip install yt-dlp av opencv-python
    ```

## Usage
![Demo](/assets/readme/demo1.gif)
1. Run main.py
    ```bash
    python main.py
    ```
2. Search for a Youtube video by entering the title
3. Select the video from the top 5 results
4. Watch it

## Compatable Terminals
### Windows
* Windows Terminal
* ConEmu
* mintty
* Alacritty
* kitty
### Linux
Linux terminals with ANSI support are much more common
* xterm
* gnome terminal
* konsole

## Known Issues
* High CPU usage from real time decoding
* Stream errors from unstable network
* ~6GB of ram usage