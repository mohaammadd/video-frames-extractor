import cv2
import pandas as pd
import os
import re
from collections import defaultdict

class PhaseVideoProcessor:
    """
    Class to handle the processing of cataract surgery videos, splitting them based on phases defined in a CSV.
    It also handles repeated phases by appending an underscore and a number (e.g., _2, _3) to the file name for repeated phases.
    """
    def __init__(self, output_base_dir):
        self.output_base_dir = output_base_dir
        os.makedirs(output_base_dir, exist_ok=True)  # Ensure base directory exists

    def get_case_number_from_filename(self, filename):
        """
        Extracts the case number from the video filename using a regular expression.
        """
        match = re.search(r'case_(\d+)', filename, re.IGNORECASE)  # Adjusted to match 'case_123'
        if match:
            return match.group(1)
        raise ValueError(f"Could not extract case number from filename: {filename}")

    def read_csv(self, csv_file):
        """
        Reads the CSV file containing frame numbers and phase numbers and returns a DataFrame.
        """
        df = pd.read_csv(csv_file)
        return df

    def map_phase_numbers_to_names(self, df):
        phase_mapping = {
            0: 'Idle',
            1: 'Incision',
            2: 'Viscoelastic',
            3: 'Capsulorhexis',
            4: 'Hydrodissection',
            5: 'Phacoemulsification',
            6: 'IrrigationAspiration',
            7: 'CortexRemoval',
            8: 'LensImplantation',
            9: 'ViscoelasticSuction',
            10:'TonifyingAntibiotic'
        }
        df['Phase Name'] = df['Phase'].map(phase_mapping)
        return df

    def create_writer(self, phase, phase_counters, case_number, frame_size, fps):
        """
        Initializes a cv2.VideoWriter object for the given phase.
        Handles repeated phases by appending _2, _3, etc., to the file name for repeated occurrences.
        """
        phase_counters[phase] += 1

        # Ensure 4-digit case number for ID formatting
        case_number_str = f"ID{int(case_number):04d}"
        output_filename = f"Cataract101_{case_number_str}_{phase}"
        
        if phase_counters[phase] > 1:
            output_filename += f"_{phase_counters[phase]}"
        output_filename += ".mp4"

        # Create phase directory if it doesn't exist
        phase_dir = os.path.join(self.output_base_dir, phase)
        os.makedirs(phase_dir, exist_ok=True)

        output_path = os.path.join(phase_dir, output_filename)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, frame_size)

        print(f"Initializing VideoWriter for phase: {phase}, output path: {output_path}")
        return writer

    def process_video(self, video_file, csv_file):
        """
        Processes a single video file, splitting it into multiple phases based on the CSV file.
        Handles repeated phases by saving subsequent occurrences as separate video files.
        """
        case_number = self.get_case_number_from_filename(os.path.basename(video_file))

        # Read the CSV and map phase numbers to phase names
        df = self.read_csv(csv_file)
        df = self.map_phase_numbers_to_names(df)

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
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"Processing video: {video_file}")
        print(f"Total frames: {total_frames}, FPS: {fps}, Frame Size: {frame_size}")

        phase_counters = defaultdict(int)
        previous_phase = None

        # Iterate over the phase rows and create videos for each phase
        for idx, row in df.iterrows():
            phase = row['Phase Name']
            start_frame = row['FrameNo']

            # Set the end frame as either the next phase's start frame or the total frame count
            if idx + 1 < len(df):
                end_frame = df.loc[idx + 1, 'FrameNo'] - 1
            else:
                end_frame = total_frames - 1  # Process until the last frame for the final phase

            # Create the video writer for this phase
            writer = self.create_writer(phase, phase_counters, case_number, frame_size, fps)

            # Read and write frames from start_frame to end_frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)  # Jump to start_frame
            for frame_number in range(start_frame, end_frame + 1):
                ret, frame = cap.read()
                if not ret:
                    print(f"Failed to read frame {frame_number}")
                    break
                writer.write(frame)

            writer.release()  # Close the video file after writing the phase
            print(f"Saved video for phase '{phase}' from frame {start_frame} to {end_frame}")

        cap.release()
        print(f"Processing complete for {video_file}. Videos saved in respective phase folders.")


def generate_csv_files(main_csv_path, output_directory):
    """
    Generates individual CSV files for each video based on the main CSV file provided.
    It adds a 'Phase 0' (Idle) before the first phase starts.
    """
    # Load the CSV with semicolon as the delimiter
    df = pd.read_csv(main_csv_path, delimiter=';')

    # Ensure the output directory for new CSV files exists
    os.makedirs(output_directory, exist_ok=True)

    # Group the data by VideoID to create separate CSVs
    for video_id, group in df.groupby('VideoID'):
        # Sort by frame number to ensure proper phase order
        group = group.sort_values(by='FrameNo').reset_index(drop=True)
        
        # Insert the Idle phase (Phase 0) before the first phase
        first_frame_no = group.loc[0, 'FrameNo']
        idle_row = pd.DataFrame({
            'FrameNo': [0],  # Start of the video
            'Phase': [0]     # Idle phase
        })
        
        # Prepend the Idle phase to the current video group
        group = pd.concat([idle_row, group[['FrameNo', 'Phase']]], ignore_index=True)
        
        # Save the CSV for this video
        output_csv_path = os.path.join(output_directory, f'case_{video_id}.csv')
        group.to_csv(output_csv_path, index=False)
        print(f"Generated CSV for video {video_id} at: {output_csv_path}")


def main(main_csv_path, video_directory, output_base_dir, csv_output_directory):
    """
    Main function to generate CSV files from the main CSV, and then process all videos in the specified directory.
    """
    # Step 1: Generate CSV files
    generate_csv_files(main_csv_path, csv_output_directory)
    
    # Step 2: Process videos using the generated CSV files
    processor = PhaseVideoProcessor(output_base_dir)
    
    for filename in os.listdir(video_directory):
        if filename.endswith(".mp4"):
            video_file = os.path.join(video_directory, filename)

            # Try to match video_id from the filename
            match = re.search(r'case_(\d+)', filename)  # Adjusted to match 'case_123'
            if match:
                video_id = match.group(1)
                csv_file = os.path.join(csv_output_directory, f'case_{video_id}.csv')

                if os.path.exists(csv_file):
                    processor.process_video(video_file, csv_file)
                else:
                    print(f"Warning: No corresponding CSV file found for {video_file}")
            else:
                print(f"Warning: Could not extract video ID from filename {filename}")


if __name__ == "__main__":
    main_csv_path = ''
    video_directory = ''
    output_base_dir =  ''
    csv_output_directory = ''

    main(main_csv_path, video_directory, output_base_dir, csv_output_directory)