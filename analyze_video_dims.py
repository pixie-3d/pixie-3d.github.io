#!/usr/bin/env python3
"""
Script to analyze frame dimensions of real-world scene videos.
Analyzes the concat.mp4 files for each scene mentioned in index.html.
"""

import cv2
import os
from pathlib import Path

def analyze_video_dimensions(video_path):
    """Analyze video dimensions and return width, height, fps, and frame count."""
    if not os.path.exists(video_path):
        return None
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        return None
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    cap.release()
    
    return {
        'width': width,
        'height': height,
        'fps': fps,
        'frame_count': frame_count,
        'duration': frame_count / fps if fps > 0 else 0
    }

def main():
    # Scene names from index.html
    scenes = [
        "bouquet",
        "bonsai", 
        "vasedeck",
        "burger_combine",
        "bun",
        "dog"
    ]
    
    base_path = "static/videos/ours_real_world/renders"
    
    print("Video Dimension Analysis")
    print("=" * 50)
    
    all_dims = []
    
    for scene in scenes:
        video_path = os.path.join(base_path, scene, "concat.mp4")
        print(f"\nAnalyzing: {scene}")
        print(f"Path: {video_path}")
        
        dims = analyze_video_dimensions(video_path)
        
        if dims is None:
            print(f"❌ Could not analyze video (file not found or corrupted)")
            continue
            
        print(f"✅ Dimensions: {dims['width']} x {dims['height']}")
        print(f"   FPS: {dims['fps']:.2f}")
        print(f"   Frames: {dims['frame_count']}")
        print(f"   Duration: {dims['duration']:.2f}s")
        
        all_dims.append({
            'scene': scene,
            **dims
        })
    
    # Summary
    if all_dims:
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        
        # Check if all videos have same dimensions
        widths = [d['width'] for d in all_dims]
        heights = [d['height'] for d in all_dims]
        
        if len(set(widths)) == 1 and len(set(heights)) == 1:
            print(f"✅ All videos have consistent dimensions: {widths[0]} x {heights[0]}")
        else:
            print("⚠️  Videos have different dimensions:")
            for dim in all_dims:
                print(f"   {dim['scene']}: {dim['width']} x {dim['height']}")
        
        # FPS summary
        fps_values = [d['fps'] for d in all_dims]
        if len(set(fps_values)) == 1:
            print(f"✅ All videos have consistent FPS: {fps_values[0]:.2f}")
        else:
            print("⚠️  Videos have different FPS:")
            for dim in all_dims:
                print(f"   {dim['scene']}: {dim['fps']:.2f}")
        
        # Duration summary
        durations = [d['duration'] for d in all_dims]
        avg_duration = sum(durations) / len(durations)
        print(f"📊 Average duration: {avg_duration:.2f}s")
        print(f"📊 Duration range: {min(durations):.2f}s - {max(durations):.2f}s")
    
    else:
        print("\n❌ No videos could be analyzed")

if __name__ == "__main__":
    main()
