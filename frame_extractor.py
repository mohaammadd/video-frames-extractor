import os
import cv2
import pandas as pd

VIDEO_DIR = '/path/to/videos/'  # Directory containing your video files
PHASE_DIR = '/path/to/phase_files/'  # Directory containing your CSV files
OUTPUT_DIR = '/path/to/output/'  # Directory to save the extracted frames
MAX_FRAMES = 15  # Maximum number of frames to extract per phase
MIN_SAMPLING_RATE = 0.3  # Minimum sampling rate in seconds

def create_directory(directory):
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            print(f"Directory created: {directory}")
        except Exception as e:
            print(f"Failed to create directory {directory}: {e}")

def save_frames(video_path, csv_path, output_dir, max_frames, min_sampling_rate):
    # Extract case_id from the video filename (remove the extension)
    case_id = os.path.splitext(os.path.basename(video_path))[0]

    # Load the CSV file
    try:
        df = pd.read_csv(csv_path)
        print(f"Successfully loaded {csv_path}")
    except Exception as e:
        print(f"Failed to load CSV file: {e}")
        return

    # Open the video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return

    # Get the frame rate of the video
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        print("Error: Could not retrieve frame rate from video.")
        return

    # Create the main output directory if it doesn't exist
    create_directory(output_dir)

    # Iterate over each phase in the CSV file
    for _, row in df.iterrows():
        phase_name = row['comment']  # Assuming 'comment' column has phase names
        start_sec = float(row['sec'])  # Assuming 'sec' column has start times in seconds
        end_sec = float(row['endsec'])  # Assuming 'endsec' column has end times in seconds

        # Convert start and end times to frame numbers
        start_frame = int(start_sec * fps)
        end_frame = int(end_sec * fps)

        # Calculate the total number of frames in the phase
        total_frames = end_frame - start_frame
        if total_frames <= 0:
            print(f"Invalid frame range for phase '{phase_name}' in '{case_id}'. Skipping.")
            continue

        # Calculate the sampling rate
        sampling_rate = total_frames / max_frames

        # Ensure the sampling rate is at least the minimum specified
        if sampling_rate < min_sampling_rate * fps:
            sampling_rate = min_sampling_rate * fps

        # Create a directory for the phase
        phase_dir = os.path.join(output_dir, case_id, phase_name)
        create_directory(phase_dir)

        # Extract frames at the calculated sampling rate
        for i in range(max_frames):
            frame_num = int(start_frame + i * sampling_rate)
            if frame_num > end_frame:
                break

            # Set the video to the specified frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()

            if not ret:
                print(f"Error: Could not read frame {frame_num} from video '{case_id}'.")
                continue

            # Save the frame with the specified format: 'ARAS_case_id_phase_name_frame_number.png'
            frame_filename = os.path.join(phase_dir, f"ARAS_{case_id}_{phase_name}_{frame_num}.png")
            try:
                cv2.imwrite(frame_filename, frame)
                print(f"Saved {frame_filename}")
            except Exception as e:
                print(f"Failed to save frame: {e}")

    # Release the video capture object
    cap.release()
    print(f"All frames for '{case_id}' have been saved.")

if __name__ == "__main__":
    # List all video files in the video directory
    video_files = [f for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')]
    
    for video_file in video_files:
        video_path = os.path.join(VIDEO_DIR, video_file)
        
        # Find the corresponding phase file based on the video file name
        phase_file = os.path.splitext(video_file)[0] + '_phases.csv'
        phase_path = os.path.join(PHASE_DIR, phase_file)
        
        if not os.path.exists(phase_path):
            print(f"Phase file '{phase_file}' not found for video '{video_file}'. Skipping.")
            continue
        
        # Define the output directory for this video
        video_output_dir = os.path.join(OUTPUT_DIR, os.path.splitext(video_file)[0])
        
        # Process the video and extract frames
        save_frames(video_path, phase_path, video_output_dir, MAX_FRAMES, MIN_SAMPLING_RATE)
