import cv2
import os
import argparse

def put_text(img, text, org, font_scale, thickness, align_right=False):
    """Utility to draw text with a shadow for better readability."""
    font = cv2.FONT_HERSHEY_DUPLEX
    (text_w, _), _ = cv2.getTextSize(text, font, font_scale, thickness)
    
    x, y = org
    if align_right:
        x -= text_w
        
    shadow_offset = int(2 * font_scale)
    # Shadow
    cv2.putText(img, text, (x + shadow_offset, y + shadow_offset), font, font_scale, (0, 0, 0), thickness + 1, cv2.LINE_AA)
    # Text
    cv2.putText(img, text, (x, y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

def main(inp_path: str, out_path: str, scene_name: str = "Bouquet", pane_count: int = 5, repeat: int = 2):
    cap = cv2.VideoCapture(inp_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {inp_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    # fps = 30.0
    # fps = 15.0
    # if fps <= 1e-2:
    #     fps = 30.0  # fallback default FPS when metadata missing

    # Load all frames once so we can easily re-index when repeating segments
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()

    pane_w = width // pane_count
    rgb_x0, rgb_x1 = 0, pane_w
    mat_x0, mat_x1 = pane_w, 2 * pane_w

    out_h, out_w = height, pane_w
    half = pane_w // 2  # middle x coordinate for split
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    writer = cv2.VideoWriter(out_path, fourcc, fps, (out_w, out_h))
    
    font_scale = out_h / 540 * 0.9
    thickness = 2
    margin = int(15 * font_scale)

    # Feature mapping (pane index → label)
    feature_list = [
        (1, "Material"),
        (2, "Young E"),
        (3, "Density"),
        (4, "Poisson"),
    ]

    total_frames = len(frames)
    # Effective frames after looping the entire video `repeat` times
    effective_total_frames = total_frames * repeat
    seg_len = effective_total_frames // len(feature_list)  # longer segment per feature
    # fade_frames = min(int(0.1 * seg_len), seg_len // 3)
    fade_frames = 0
    total_output_frames = effective_total_frames

    # Pre-compute text height using generic label
    (_, text_h), _ = cv2.getTextSize("RGB", cv2.FONT_HERSHEY_DUPLEX, font_scale, thickness)

    out_frame_count = 0
    for idx in range(total_output_frames):
        # Select the frame from the original clip, looping when we reach the end
        frame = frames[idx % total_frames]

        seg_idx = idx // seg_len  # which feature we are on (0-based)
        in_seg_frame = idx % seg_len

        rgb = frame[:, rgb_x0:rgb_x1]

        curr_pane_idx, curr_label = feature_list[seg_idx]

        # Determine previous feature for fading
        prev_pane_idx, prev_label = feature_list[seg_idx - 1] if seg_idx > 0 else (curr_pane_idx, curr_label)

        curr_x0, curr_x1 = curr_pane_idx * pane_w, (curr_pane_idx + 1) * pane_w
        prev_x0, prev_x1 = prev_pane_idx * pane_w, (prev_pane_idx + 1) * pane_w

        curr_feat = frame[:, curr_x0:curr_x1]
        prev_feat = frame[:, prev_x0:prev_x1]

        # Alpha for fade
        # `in_seg_frame` already computed above
        if fade_frames > 0 and in_seg_frame < fade_frames and seg_idx > 0:
            alpha = in_seg_frame / fade_frames
            right_half = cv2.addWeighted(prev_feat[:, half:], 1 - alpha, curr_feat[:, half:], alpha, 0)
            right_label = curr_label if alpha > 0.5 else prev_label
        elif fade_frames > 0 and in_seg_frame > seg_len - fade_frames and seg_idx < len(feature_list) - 1:
            alpha = (seg_len - in_seg_frame) / fade_frames
            next_pane_idx, next_label = feature_list[seg_idx + 1]
            next_x0, next_x1 = next_pane_idx * pane_w, (next_pane_idx + 1) * pane_w
            next_feat = frame[:, next_x0:next_x1]
            right_half = cv2.addWeighted(curr_feat[:, half:], alpha, next_feat[:, half:], 1 - alpha, 0)
            right_label = curr_label if alpha >= 0.5 else next_label
        else:
            right_half = curr_feat[:, half:]
            right_label = curr_label

        comp = rgb.copy()
        comp[:, half:] = right_half

        cv2.line(comp, (half, 0), (half, out_h), (255, 255, 255), 4)

        # Draw labels
        put_text(comp, "RGB", (margin, margin + text_h), font_scale, thickness)
        put_text(comp, right_label, (out_w - margin, margin + text_h), font_scale, thickness, align_right=True)
        put_text(comp, scene_name, (margin, out_h - margin), font_scale, thickness)
        
        writer.write(comp)

    writer.release()
    cap.release()
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate split RGB | feature video with labels.")
    parser.add_argument("--inp", default="static/videos/ours_real_world/renders/bouquet/concat.mp4", help="Path to concat video")
    parser.add_argument("--out", default="static/videos/ours_real_world/bouquet_rgb_mat.mp4", help="Output mp4 path")
    parser.add_argument("--scene", default="Bouquet", help="Scene name label")
    parser.add_argument("--repeat", type=int, default=2, help="How many times to repeat each feature segment")
    args = parser.parse_args()
    main(args.inp, args.out, args.scene, repeat=args.repeat) 