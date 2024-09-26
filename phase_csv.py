import pandas as pd
import os
import sys

def get_input_file():
    if len(sys.argv) == 2:
        return sys.argv[1]
    else:
        while True:
            file_path = input("Please enter the path to your input CSV file: ").strip()
            if os.path.exists(file_path):
                return file_path
            else:
                print(f"Error: File '{file_path}' does not exist. Please try again.")

def process_phases(input_file):
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    # Get the video name from the first row
    video_name = df['case'].iloc[0]
    
    # Sort the dataframe by Start Frame
    df = df.sort_values('Start Frame')
    
    # Initialize the list to store all phases including idle
    all_phases = []
    
    # Add initial idle phase if necessary
    if df['Start Frame'].iloc[0] > 0:
        all_phases.append({
            'case': video_name,
            'phase name': 'Idle',
            'Start Frame': 0,
            'End Frame': df['Start Frame'].iloc[0] - 1,
            'Start Time (s)': 0,
            'End Time (s)': (df['Start Frame'].iloc[0] - 1) / 60  # Assuming 60 fps
        })
    
    # Process existing phases and add idle phases
    for i in range(len(df)):
        # Add the current phase
        all_phases.append(df.iloc[i].to_dict())
        
        # If there's a next phase, check for gap and add idle if necessary
        if i < len(df) - 1:
            current_end = df['End Frame'].iloc[i]
            next_start = df['Start Frame'].iloc[i+1]
            if next_start - current_end > 1:
                all_phases.append({
                    'case': video_name,
                    'phase name': 'Idle',
                    'Start Frame': current_end + 1,
                    'End Frame': next_start - 1,
                    'Start Time (s)': (current_end + 1) / 60,  # Assuming 60 fps
                    'End Time (s)': (next_start - 1) / 60  # Assuming 60 fps
                })
    
    # Create a new dataframe with all phases
    new_df = pd.DataFrame(all_phases)
    
    # Sort the new dataframe by Start Frame
    new_df = new_df.sort_values('Start Frame')
    
    # Generate output file name
    input_dir = os.path.dirname(input_file)
    output_file = os.path.join(input_dir, f"{video_name}_phases_with_idle.csv")
    
    # Save the new dataframe to a CSV file
    new_df.to_csv(output_file, index=False)
    
    print(f"Processed data saved to {output_file}")

# Main execution
if __name__ == "__main__":
    input_file = get_input_file()
    process_phases(input_file)