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
        match = re.search(r'case_(\d+)', filename, re.IGNORECASE)
        if match:
            return match.group(1)
        raise ValueError(f"Could not extract case number from filename: {filename}")

    def read_csv(self, csv_file):
        """
        Reads the CSV file containing frame numbers and phase names and returns a DataFrame.
        """
        df = pd.read_csv(csv_file, header=None)
        df.columns = ['Frame Number', 'Phase Name']
        return df

    def map_phases(self, df):
        """
        Standardizes phase names using a predefined mapping.
        """
        phase_mapping = {
            'not_initialized': 'Idle',
            'Incision': 'Incision',
            'Viscoelasticum': 'Viscoelastic',
            'Rhexis': 'Capsulorhexis',
            'Hydrodissektion': 'Hydrodissection',
            'Phako': 'Phaco',
            'Irrigation-Aspiration': 'Irrigation',
            'Kapselpolishing': 'CortexRemoval',
            'Linsenimplantation': 'LensImplantation',
            'Visco-Absaugung': 'ViscoelasticSuction',
            'Tonisieren': 'TonifyingAntibiotic_1',
            'Antibiotikum': 'TonifyingAntibiotic_2'
        }
        df['Phase Name'] = df['Phase Name'].replace(phase_mapping)
        return df

    def create_writer(self, phase, phase_counters, case_number, frame_size, fps):
        """
        Initializes a cv2.VideoWriter object for the given phase.
        Handles repeated phases by appending _2, _3, etc., to the file name for repeated occurrences.
        """
        phase_counters[phase] += 1
        output_filename = f"Cataract21_ID00{case_number}_{phase}"
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

        # Read the CSV and map the phases
        df = self.read_csv(csv_file)
        df = self.map_phases(df)

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
        writers = {}
        frames_to_process = min(total_frames, len(df))

        previous_phase = None
        start_frame = None

        # Process each frame in the video
        for frame_number in range(frames_to_process):
            ret, frame = cap.read()
            if not ret:
                print(f"Failed to read frame {frame_number}")
                break

            phase = df.loc[frame_number, 'Phase Name']

            # If phase changes (or it's the first frame)
            if phase != previous_phase:
                # Close the previous writer if exists
                if previous_phase is not None and previous_phase in writers:
                    writers[previous_phase].release()
                    print(f"Closing writer for phase: {previous_phase}")

                # Create a new writer for the current phase
                writers[phase] = self.create_writer(phase, phase_counters, case_number, frame_size, fps)
                start_frame = frame_number  # Record the start frame for this phase

            # Write the current frame to the appropriate phase video
            writers[phase].write(frame)
            previous_phase = phase

        # Release all resources
        for writer in writers.values():
            writer.release()
        cap.release()

        print(f"Processing complete for {video_file}. Videos saved in respective phase folders.")


def main(directory, output_base_dir):
    """
    Main function to process all video files in the specified directory.
    """
    processor = PhaseVideoProcessor(output_base_dir)

    for filename in os.listdir(directory):
        if filename.endswith(".mp4"):
            video_file = os.path.join(directory, filename)
            csv_file = os.path.join(directory, filename.replace('.mp4', '.csv'))

            if os.path.exists(csv_file):
                processor.process_video(video_file, csv_file)
            else:
                print(f"Warning: No corresponding CSV file found for {video_file}")


if __name__ == "__main__":
    # Define input and output directories (update these paths for your environment)
    input_directory = ''
    output_directory = ''

    main(input_directory, output_directory)
