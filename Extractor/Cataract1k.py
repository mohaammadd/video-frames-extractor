import cv2
import pandas as pd
import os
import re
from collections import defaultdict

# Define a mapping from original phase names/numbers to new custom phase names

PHASE_MAPPING = {
    'Viscoelastic': 'Viscoelastic',
    'Capsulorhexis': 'Capsulorhexis',
    'Hydrodissection': 'Hydrodissection',
    'Phacoemulsification': 'Phaco',
    'Irrigation/Aspiration': 'IrrigationAspiration',
    'Capsule Pulishing': 'CortexRemoval',
    'Lens Implantation': 'LensImplantation',
    'Lens positioning': 'LensPositioning',
    'Viscoelastic_Suction': 'ViscoelasticSuction',
    'Tonifying/Antibiotics': 'TonifyingAntibiotics',
    'Anterior_Chamber Flushing': 'AnteriorChamberFlushing'
}

def get_case_number_from_filename(filename):
    """
    Extracts the case number from the video filename using a regular expression.
    """
    match = re.search(r'case_(\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract case number from filename: {filename}")

def map_phase_name(phase_name):
    """
    Maps the original phase name to the custom phase name using the PHASE_MAPPING.
    """
    return PHASE_MAPPING.get(phase_name, phase_name)  # If not found, return the original name

def insert_idle_phases(df):
    """
    Inserts idle phases in gaps between actual phases.
    """
    new_rows = []

    # Iterate over each row and check for gaps between consecutive phases
    for i in range(len(df) - 1):
        current_row = df.iloc[i]
        next_row = df.iloc[i + 1]
        new_rows.append(current_row)

        # Calculate the frame gap
        frame_gap = next_row['frame'] - current_row['endFrame'] - 1

        # If there's a gap, insert an Idle phase
        if frame_gap > 0:
            idle_phase = {
                'caseId': current_row['caseId'],
                'comment': 'Idle',  # Insert idle phase
                'frame': current_row['endFrame'] + 1,
                'endFrame': next_row['frame'] - 1,
                'sec': current_row['endSec'],
                'endSec': next_row['sec']
            }
            new_rows.append(pd.Series(idle_phase))

    # Add the last row (no need to check for a gap after the last phase)
    new_rows.append(df.iloc[-1])

    return pd.DataFrame(new_rows)

def create_writer(phase, case_number, phase_counters, frame_size, fps, output_base_dir):
    """
    Creates a video writer for a specific phase, handling repeated phases with unique names.
    """
    phase_counters[phase] += 1

    # Ensure case number is 4 digits
    case_number_str = f"ID{int(case_number):04d}"
    output_filename = f"Cataract1k_{case_number_str}_{phase}"

    if phase_counters[phase] > 1:
        output_filename += f"_{phase_counters[phase]}"  # Handle repeated phases

    output_filename += ".mp4"

    # Create directory for the phase (directly in the output base dir)
    phase_dir = os.path.join(output_base_dir, phase)
    os.makedirs(phase_dir, exist_ok=True)

    # Output path for the subvideo
    output_path = os.path.join(phase_dir, output_filename)

    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, frame_size)

    return writer, output_path

def process_video(video_file, csv_file, output_base_dir):
    """
    Processes a single video file, splitting it into multiple phases based on the CSV file.
    Handles repeated phases by saving subsequent occurrences as separate video files.
    """
    case_number = get_case_number_from_filename(os.path.basename(video_file))

    # Read the CSV and insert idle phases
    df = pd.read_csv(csv_file)
    df = insert_idle_phases(df)

    # Open the video file
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        print(f"Error: Could not open video file: {video_file}")
        return

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (frame_width, frame_height)

    phase_counters = defaultdict(int)

    # Iterate over the phase rows and create subvideos for each phase
    for idx, row in df.iterrows():
        original_phase = row['comment']
        start_frame = row['frame']
        end_frame = row['endFrame']

        # Map the original phase name to the custom phase name
        phase = map_phase_name(original_phase)

        # Create video writer for this phase
        writer, output_path = create_writer(phase, case_number, phase_counters, frame_size, fps, output_base_dir)

        # Jump to the start frame and write frames until the end frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        for frame_number in range(start_frame, end_frame + 1):
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)

        writer.release()
        print(f"Saved video for phase '{phase}' from frame {start_frame} to {end_frame} at {output_path}")

    cap.release()
    print(f"Processing complete for {video_file}. Videos saved in respective phase folders.")

def process_all_videos(annotations_dir, video_dir, output_base_dir):
    """
    Process all videos in the specified directory using their corresponding CSV files.
    """
    for root, dirs, files in os.walk(annotations_dir):
        for file in files:
            if file.endswith("_annotations_phases.csv"):
                csv_file = os.path.join(root, file)
                case_number = get_case_number_from_filename(file)
                video_file = os.path.join(video_dir, f"case_{case_number}.mp4")

                if os.path.exists(video_file):
                    print(f"Processing video: {video_file}")
                    process_video(video_file, csv_file, output_base_dir)
                else:
                    print(f"Warning: No corresponding video file found for {csv_file}")

if __name__ == "__main__":
    annotations_dir = ''
    video_dir = ''
    output_base_dir = ''

    # Process all videos and save subvideos in Google Drive
    process_all_videos(annotations_dir, video_dir, output_base_dir)
