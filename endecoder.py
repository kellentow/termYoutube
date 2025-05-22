from cv2 import resize, INTER_NEAREST
from concurrent.futures import ProcessPoolExecutor

global ansi,pool
ansi = []
pool = ProcessPoolExecutor()

def gen_ansi(quality,return_val=True):
    """Generates ansi escape sequences to color the terminal with

    Args:
        quality (int): how many bits you want per channel (min 1 bit)
        return_val (bool, optional): Decides if it should return or put that in the module globals. Defaults to True.

    Returns:
        None or list: The ansi list
    """
    quality = 2**(8-quality)
    ansi_out = []
    for r in range(0, 256, quality):
        ansi_out.append([])
        for g in range(0, 256, quality):
            ansi_out[r//quality].append([])
            for b in range(0, 256, quality):
                fg = f"\x1b[38;2;{r};{g};{b}m"
                bg = f"\x1b[48;2;{r};{g};{b}m"
                ansi_out[r//quality][g//quality].append((fg, bg))
    if return_val:
        return ansi_out
    global ansi
    ansi = ansi_out

def image_to_text(image, cols=100):
    """Turns an image into a ANSI text version

    Args:
        image (list-like): ndarray((w,h,3)) like list
        cols (int, optional): width of converted image

    Returns:
        Str: Text version of image (USES ANSI)
    """
    h, w, _ = image.shape
    aspect = h / w
    rows = max(1, int(aspect * cols / 2))
    small = resize(image, (cols, rows * 2), interpolation=INTER_NEAREST)
    row_pairs = [(small[2*i], small[2*i+1]) for i in range(rows)]
    return '\n'.join(list(pool.map(_worker, row_pairs, ansi, chunksize=16)))

def _worker(rows,ansi):
    out = []
    quality = 256//len(ansi)
    last_fg = last_bg = None
    for (r1, g1, b1), (r2, g2, b2) in zip(*rows):
        rr1, gg1, bb1 = r1//quality, g1//quality, b1//quality
        rr2, gg2, bb2 = r2//quality, g2//quality, b2//quality
        fg = ansi[rr1][gg1][bb1][0] if last_fg != (rr1, gg1, bb1) else ''
        bg = ansi[rr2][gg2][bb2][1] if last_bg != (rr2, gg2, bb2) else ''
        last_fg, last_bg = (rr1, gg1, bb1), (rr2, gg2, bb2)
        out.append(f"{fg}{bg}▀")
    out.append("\x1b[0m")
    return ''.join(out)