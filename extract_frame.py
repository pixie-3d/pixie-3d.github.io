import cv2
import argparse
import os

def extract_first_frame(video_path, output_path):
    """
    Extracts the first frame of a video and saves it as a PNG image.
    """
    # Check if video file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at '{video_path}'")
        return

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Open the video file
    cap = cv2.VideoCapture(video_path)

    # Check if video opened successfully
    if not cap.isOpened():
        print(f"Error: Could not open video file '{video_path}'")
        return

    # Read the first frame
    ret, frame = cap.read()

    if ret:
        # Save the frame as a PNG image
        cv2.imwrite(output_path, frame)
        print(f"Successfully extracted the first frame to '{output_path}'")
    else:
        print("Error: Could not read the first frame.")

    # Release the video capture object
    cap.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract the first frame from a video.")
    parser.add_argument("video_path", type=str, help="Path to the input video file.")
    parser.add_argument("output_path", type=str, help="Path to save the output PNG image.")
    args = parser.parse_args()

    extract_first_frame(args.video_path, args.output_path) 