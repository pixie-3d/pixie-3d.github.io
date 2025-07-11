# Standard video and image processing
import cv2
import os

# Use imageio's FFmpeg writer for reliable MP4 output
import imageio.v2 as imageio

FEATURES = [
    (1, "Material"),
    (2, "Young E"),
    (3, "Density"),
    (4, "Poisson"),
]

VIDEO_PATHS = {
    "bouquet": "static/videos/ours_real_world/renders/bouquet/concat.mp4",
    "bonsai": "static/videos/ours_real_world/renders/bonsai/concat.mp4",
    "vasedeck": "static/videos/ours_real_world/renders/vasedeck/concat.mp4",
}

repeats = {
    "bouquet": 2,
    "bonsai": 4,
    "vasedeck": 4,
}

OUTPUT = "static/videos/ours_real_world/real_demo_combined.mp4"
FPS = 30


def put_text(img, text, org, font_scale, thickness, align_right=False):
    font = cv2.FONT_HERSHEY_DUPLEX
    (w, _), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = org
    if align_right:
        x -= w
    cv2.putText(img, text, (x + 2, y + 2), font, font_scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)


def process_scene(scene_name, writer, writer_size):
    path = VIDEO_PATHS[scene_name]
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"Cannot open {path}")
        return

    # Read all frames into memory so we can loop over them multiple times
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()

    total_frames = len(frames)
    if total_frames == 0:
        print(f"No frames found in {path}")
        return

    # Determine how many times to loop this clip
    repeat = repeats.get(scene_name, 1)

    # Segment lengths before and after repeating
    orig_seg_len = total_frames // len(FEATURES)
    seg_len = orig_seg_len * repeat

    width = frames[0].shape[1]
    height = frames[0].shape[0]

    pane_w = width // 5  # 5 panes concatenated
    half = pane_w // 2

    font_scale = height / 540 * 0.9
    thk = 2
    margin = int(15 * font_scale)
    (_, text_h), _ = cv2.getTextSize("RGB", cv2.FONT_HERSHEY_DUPLEX, font_scale, thk)

    total_output_frames = seg_len * len(FEATURES)

    target_w, target_h = writer_size

    for idx in range(total_output_frames):
        frame = frames[idx % total_frames]  # progress forward, looping at end
        seg_idx = idx // seg_len

        pane_idx, label = FEATURES[seg_idx]
        rgb = frame[:, 0:pane_w]
        feat = frame[:, pane_idx * pane_w:(pane_idx + 1) * pane_w]

        comp = rgb.copy()
        comp[:, half:] = feat[:, half:]
        cv2.line(comp, (half, 0), (half, height), (255, 255, 255), 4)
        put_text(comp, "RGB", (margin, margin + text_h), font_scale, thk)
        put_text(comp, label, (pane_w - margin, margin + text_h), font_scale, thk, align_right=True)
        put_text(comp, scene_name.capitalize(), (margin, height - margin), font_scale, thk)

        # Ensure frame matches writer's expected size
        if (comp.shape[1], comp.shape[0]) != writer_size:
            comp = cv2.resize(comp, writer_size, interpolation=cv2.INTER_AREA)

        # Convert BGR (OpenCV) → RGB (imageio/FFmpeg expects)
        writer.append_data(cv2.cvtColor(comp, cv2.COLOR_BGR2RGB))


def main():
    first_path = next(iter(VIDEO_PATHS.values()))
    cap0 = cv2.VideoCapture(first_path)
    w = int(cap0.get(cv2.CAP_PROP_FRAME_WIDTH)) // 5  # single pane width
    h = int(cap0.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap0.release()

    writer_size = (w, h)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    # Create FFmpeg-based writer via imageio using H.264 (libx264)
    writer = imageio.get_writer(
        OUTPUT,
        fps=FPS,
        codec="libx264",
        bitrate="8M",
        macro_block_size=None,  # allow arbitrary resolution
    )

    for scene in ["bouquet", "bonsai", "vasedeck"]:
        process_scene(scene, writer, writer_size)

    writer.close()
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main() 