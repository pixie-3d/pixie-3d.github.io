import os
import socket
import subprocess
import argparse
from pathlib import Path
import cv2
import numpy as np
import socket
import subprocess
import argparse
import json

# -----------------------------------------------------------------------------
# Helpers for runtime environment (copied from run_all_teaser_render.py)
# -----------------------------------------------------------------------------
# --------- config ---------
PANE_W, PANE_H = 960, 540 # chosen pane size
TARGET_W = PANE_W * 5              # 5-pane concat
TARGET_H = PANE_H
# TOP, BOTTOM, LEFT, RIGHT
CROP_DIMS = {
    "vasedeck": (417, 418, 77-77, 77+77),  #-> final dim: (2160, 3840, 3)
    "bonsai": (175+50, 175-50, 23, 23),  # -> final dim: (1728, 3072, 3)
    "bouquet": (234, 234, 98+98, 98-98), # -> final dim: (1008, 1792, 3)
}

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def process_frames(src_dir: Path, crop, out_dir: Path):
    t, b, l, r = crop
    out_dir.mkdir(parents=True, exist_ok=True)
    for fn in sorted(src_dir.glob("*.png")):
        im = cv2.imread(str(fn))
        im = im[t: im.shape[0]-b, l: im.shape[1]-r]
        # Lanczos resize to pane size
        im = cv2.resize(im, (PANE_W, PANE_H), interpolation=cv2.INTER_LANCZOS4)
        cv2.imwrite(str(out_dir / fn.name), im)

def encode_video(frames_dir: Path, out_mp4: Path, fps: int):
    # build input list for ffmpeg
    txt = frames_dir / "inputs.txt"
    txt.write_text("\n".join([f"file '{f.name}'" for f in sorted(frames_dir.glob('*.png'))]))
    os.system(
        f"ffmpeg -y -r {fps} -f concat -safe 0 -i {txt} "
        f"-c:v libx264 -pix_fmt yuv420p -preset slow -crf 18 "
        f"-vf scale={PANE_W}:{PANE_H}:flags=lanczos {out_mp4}"
    )

def preprocess_object(obj_id, feature_root):
    HOME_PATH_PREFIX = Path("/home/vlongle/code/diffPhys3d")
    config_path = HOME_PATH_PREFIX / "third_party" / "PhysGaussian" / "config" / "real_scene" / f"custom_{obj_id}_viz_config.json"
    config = load_json(config_path)
    fps = int(1.0 / config["frame_dt"])
    crop = CROP_DIMS[obj_id]
    for feat in ["rgb", "material", "E", "density", "nu"]:
        frames = feature_root / obj_id / feat / "frames"
        out_frames = frames.parent / "processed_frames"
        os.system(f"rm -rf {out_frames}")
        process_frames(frames, crop, out_frames)
        encode_video(out_frames, out_frames / "output.mp4", fps)





def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def on_desktop():
    """Return True when running on the author's desktop machine (by IP)."""
    local_desktop_ip = '158.130.50.18'
    return get_ip_address() == local_desktop_ip


# -----------------------------------------------------------------------------
# Slurm helpers
# -----------------------------------------------------------------------------


def submit_to_slurm(cmd: str, *, idx: int, args):
    """Submit *cmd* to Slurm using *sbatch --wrap* with the CLI parameters."""
    os.makedirs("slurm_outs/realworld_viz", exist_ok=True)

    job_name = f"{args.job_name}_{idx}"
    sbatch_cmd = [
        "sbatch",
        f"--job-name={job_name}",
        f"--output=slurm_outs/realworld_viz/{job_name}-%j.out",
        f"--time={args.time}",
        f"--partition={args.partition}",
        f"--qos={args.qos}",
        f"--gpus={args.gpus}",
        f"--mem={args.mem}",
        f"--cpus-per-task={args.cpus}",
        "--wrap",
        cmd,
    ]
    print("[sbatch] " + " ".join(sbatch_cmd))
    subprocess.run(sbatch_cmd, check=True)


# -----------------------------------------------------------------------------
# CLI parsing
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Visualize real-world objects either locally or via Slurm",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    p.add_argument("--slurm", action="store_true", help="Submit each run_viz.py call as its own Slurm job.")

    p.add_argument(
        "--obj_ids",
        nargs="+",
        default=["bouquet", "vasedeck", "bonsai"],
        help="List of object IDs to process.",
    )

    p.add_argument(
        "--model_feature",
        default="clip",
        help="Model feature string passed to run_viz.py",
    )

    p.add_argument(
        "--features",
        nargs="+",
        default=["rgb", "material", "E", "density", "nu"],
        help="Per-feature visualisations to generate.",
    )

    # Slurm-related options (only used when --slurm is passed)
    p.add_argument("--job_name", default="realworld_viz", help="Base name for Slurm jobs.")
    p.add_argument("--time", default="08:00:00", help="Job time limit (HH:MM:SS)")
    p.add_argument("--partition", default="eaton-compute", help="Slurm partition")
    p.add_argument("--qos", default="ee-high", help="Quality of service")
    p.add_argument("--gpus", default="1", help="GPUs per job (passed to --gpus)")
    p.add_argument("--mem", default="64G", help="Memory per job")
    p.add_argument("--cpus", default="64", help="CPUs per task")

    return p.parse_args()


# -----------------------------------------------------------------------------
# Main logic (refactored)
# -----------------------------------------------------------------------------


def main():
    args = parse_args()

    # Decide default execution mode: desktop → local, cluster → slurm (no explicit warning)
    cmd_idx = 0

    path_prefix = "/mnt/kostas-graid/datasets/vlongle/diffphys3d" if not on_desktop() else "/home/vlongle/diffPhys3d"
    for obj_id in args.obj_ids:
        # First submit / execute heavy run_viz.py jobs for each feature
        for feature in args.features:
            cmd = (
                f"python run_viz.py --obj_id {obj_id} --feature {feature} "
                f"--model_feature {args.model_feature}"
            )

            if args.slurm:
                submit_to_slurm(cmd, idx=cmd_idx, args=args)
                cmd_idx += 1
            elif on_desktop():
                print("[exec]", cmd)
                ret = os.system(cmd)
                if ret != 0:
                    raise RuntimeError(f"Command failed with exit code {ret >> 8}")


        # -------------------------------------------------------------
        # Post-processing (concatenate + copy) – only when running locally
        # -------------------------------------------------------------
        if not args.slurm:
            preprocess_object(obj_id, Path("/mnt/kostas-graid/datasets/vlongle/diffphys3d/test_viz_gs_clip"))
            input_videos = [
                f"{path_prefix}/test_viz_gs_{args.model_feature}/{obj_id}/{feat}/processed_frames/output.mp4"
                for feat in args.features
            ]

            missing = [v for v in input_videos if not os.path.exists(v)]
            if missing:
                print(f"[WARN] Missing videos for {obj_id}: {missing}. Skipping concatenation.")
                continue

            # Build ffmpeg concat command (horizontal stack)
            ffmpeg_inputs = " ".join([f"-i {v}" for v in input_videos])
            filter_inputs = "".join([f"[{idx}:v]" for idx in range(len(input_videos))])
            filter_complex = f"{filter_inputs}hstack=inputs={len(input_videos)}[v]"

            output_video = (
                f"test_viz_gs_{args.model_feature}/{obj_id}/concat_{'_'.join(args.features)}.mp4"
            )

            ffmpeg_path = "ffmpeg" ## have to be on a compute node.NOT the login node.
            ffmpeg_cmd = (
                f"{ffmpeg_path} -y {ffmpeg_inputs} -filter_complex '{filter_complex}' "
                f"-map '[v]' -c:v libx264 -preset slow -crf 18 {output_video}"
            )
            print("[exec]", ffmpeg_cmd)
            os.system(ffmpeg_cmd)

            # Copy to website folder and generate thumbnail
            # web_dir = f"umi-on-legs.github.io/static/videos/ours_real_world/renders/{obj_id}"
            web_dir = f"/home/vlongle/code/pixie-3d.github.io/static/videos/ours_real_world/renders/{obj_id}"
            os.makedirs(web_dir, exist_ok=True)

            target_video = os.path.join(web_dir, "concat.mp4")
            os.system(f"cp {output_video} {target_video}")
            print(f"Copied {output_video} to {target_video}")

            thumb_path = os.path.join(web_dir, "thumbnail.jpg")

            thumb_cmd = (
                f"ffmpeg -y -i {target_video} "
                f"-vf crop={PANE_W}:{PANE_H}:0:0 -vframes 1 -q:v 2 {thumb_path}"
            )
            os.system(thumb_cmd)
            print(f"Generated thumbnail at {thumb_path}")



    if args.slurm:
        print(
            "✅ All run_viz.py jobs submitted to Slurm. Concatenation/copy steps are skipped.\n"
            "   Re-run this script without --slurm after the jobs finish to perform video stitching."
        )


if __name__ == "__main__":
    main()





