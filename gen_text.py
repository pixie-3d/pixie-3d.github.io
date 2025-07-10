"""
gen_text.py ─ Add an animated title to a video.
- Renders "Pixie" with an animated gradient and "Physics from Pixels" subtitle.
- The title fades in and out over 3 seconds.
- Composites the title onto an input video.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import moviepy.editor as mpy
import argparse


def lerp(c0, c1, t):
    """Linear-interpolate two RGB tuples (0-255)."""
    return tuple(int((1 - t) * a + t * b) for a, b in zip(c0, c1))


def add_title_to_video(
    video_in_path: str,
    out_path: str,
    font_path: str = "/System/Library/Fonts/Cochin.ttc",  # macOS default
    size_large: int = 320,
    size_small: int = 144,
    line_spacing: int = 20,
    duration: float = 3.0,
    fade_duration: float = 0.5,
):
    """
    Adds an animated title to the input video and saves it to the output path.
    """
    # ──────────────────────────────────── 1.  Fonts & metrics
    try:
        f_big = ImageFont.truetype(font_path, size_large)
        f_small = ImageFont.truetype(font_path, size_small)
    except IOError:
        print(f"Font not found at {font_path}. Using default font.")
        f_big = ImageFont.load_default()
        f_small = ImageFont.load_default()

    # Use a dummy image to measure text size
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    
    # .textsize is deprecated, using .textbbox instead
    bbox_big = dummy_draw.textbbox((0, 0), "Pixie", font=f_big)
    w_big, h_big = bbox_big[2] - bbox_big[0], bbox_big[3] - bbox_big[1]
    
    bbox_small = dummy_draw.textbbox((0, 0), "Physics from Pixels", font=f_small)
    w_small, h_small = bbox_small[2] - bbox_small[0], bbox_small[3] - bbox_small[1]

    width = max(w_big, w_small)
    height = h_big + line_spacing + h_small

    # ──────────────────────────────────── 2.  Gradient & Mask setup
    stops = [(255, 110, 196),  # #ff6ec4
             (120, 115, 245),  # #7873f5
             (255, 110, 196)]  # #ff6ec4

    mask = Image.new("L", (w_big, h_big), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.text((-bbox_big[0], -bbox_big[1]), "Pixie", font=f_big, fill=255)
    
    x_pixie = (width - w_big) // 2
    x_sub = (width - w_small) // 2
    y_sub = h_big + line_spacing

    # ──────────────────────────────────── 3.  Frame & mask generation functions

    def make_rgba(t):
        """Return an RGBA numpy array for the animated text at time t."""
        # Canvas for the text
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Gradient word "Pixie"
        grad = Image.new("RGBA", (w_big, h_big))
        p = grad.load()

        anim_offset = t / 6.0

        for x in range(w_big):
            t_norm = x / (w_big - 1) if w_big > 1 else 0
            t_shifted = t_norm + anim_offset

            t_grad = t_shifted * (len(stops) - 1)
            seg, seg_t = divmod(t_grad, 1)
            seg = int(seg) % (len(stops) - 1)

            c = lerp(stops[seg], stops[seg + 1], seg_t)
            for y in range(h_big):
                p[x, y] = (*c, 255)

        img.paste(grad, (x_pixie, 0), mask)

        # Subtitle (solid white)
        draw.text((x_sub, y_sub - bbox_small[1]), "Physics from Pixels", font=f_small,
                  fill=(255, 255, 255, 255))

        return np.array(img)

    # Color frames: discard alpha channel
    def make_frame(t):
        return make_rgba(t)[..., :3]

    # Mask frames: take alpha channel and normalise to [0,1]
    def make_mask(t):
        return make_rgba(t)[..., 3] / 255.0

    # ──────────────────────────────────── 4.  MoviePy processing
    # Load input video
    video = mpy.VideoFileClip(video_in_path)

    # Create the animated text clip (RGB) and its mask (grayscale)
    text_clip = mpy.VideoClip(make_frame, duration=duration)
    mask_clip = mpy.VideoClip(make_mask, ismask=True, duration=duration)

    # Fade in/out by animating the mask transparency
    mask_clip = (
        mask_clip
        .fx(mpy.vfx.fadein, fade_duration, initial_color=0.0)
        .fx(mpy.vfx.fadeout, fade_duration, final_color=0.0)
    )

    text_clip = text_clip.set_mask(mask_clip).set_duration(duration)

    # Position at the center of the screen
    final_text_clip = text_clip.set_position(('center', 'center'))

    # Composite text over video
    final_clip = mpy.CompositeVideoClip([video, final_text_clip])

    # ──────────────────────────────────── 5.  Save
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    final_clip.write_videofile(out_path, codec='libx264', audio_codec='aac')
    print(f"Saved {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Add animated title to a video.')
    parser.add_argument('input_video', help='Path to the input video file.')
    parser.add_argument('-o', '--output_video', default='output.mp4', help='Path to the output video file.')
    # parser.add_argument('--font_path', default="/Users/longle/Downloads/Cochin_Bold/Cochin_Bold.otf", help='Path to the font file.')
    parser.add_argument('--font_path', default="Cochin_Bold/Cochin_Bold.otf", help='Path to the font file.')
    args = parser.parse_args()

    add_title_to_video(args.input_video, args.output_video, font_path=args.font_path)
