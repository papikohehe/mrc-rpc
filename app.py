import streamlit as st
import pandas as pd
from collections import Counter

def find_repeated_sequences(data_rows, min_length=15):
    """
    Finds repeated sequences of text within a list of (task_id, sentence) tuples.

    Args:
        data_rows (list): A list of tuples, where each tuple is (task_id, sentence_string).
                          task_id is assumed to be the first element, sentence the second.
        min_length (int): The minimum length of the repeated sequence to consider.

    Returns:
        dict: A dictionary where keys are repeated sequences and values are
              a list of tuples (original_row_index, task_id, sentence_string, start_char_index)
              where they were found.
    """
    all_sequences_data = [] # Stores (sequence_text, original_row_index, task_id, sentence, start_char_index)

    # Generate all possible sequences of min_length or greater from each sentence
    # We'll use the original row index from the DataFrame (0-based)
    for original_row_idx, row_data in enumerate(data_rows):
        # Assume first element is task_id, second is sentence
        # Convert to string to handle potential non-string types (e.g., numbers, None)
        task_id = str(row_data[0])
        sentence = str(row_data[1])
        
        if pd.isna(sentence) or len(sentence) < min_length: # Skip if sentence is NaN or too short
            continue

        for j in range(len(sentence) - min_length + 1):
            seq = sentence[j : j + min_length]
            all_sequences_data.append((seq, original_row_idx + 2, task_id, sentence, j)) # +2 for 1-based row display after header

    # Group sequences by their text content
    grouped_sequences = {}
    for seq_text, original_row_idx, task_id, sentence, char_idx in all_sequences_data:
        if seq_text not in grouped_sequences:
            grouped_sequences[seq_text] = []
        grouped_sequences[seq_text].append((original_row_idx, task_id, sentence, char_idx))

    repeated_sequences = {}

    for seq_text, occurrences in grouped_sequences.items():
        # Check if the sequence appears in more than one *unique* sentence (based on original_row_index)
        unique_sentence_rows = set(occ[0] for occ in occurrences) # Use original_row_idx for uniqueness
        
        if len(unique_sentence_rows) > 1:
            repeated_sequences[seq_text] = occurrences
            
    return repeated_sequences


st.set_page_config(layout="wide")
st.title("CSV Sentence Sequence Checker (Thai)")

st.markdown("""
This app checks a CSV file for repeated sequences of text within the sentence data.
It identifies sequences longer than 15 characters that appear in multiple sentences.
**The app assumes your CSV has a header row and that the first column contains 'task id'
and the second column contains 'sentence' data.** Processing starts from the second row (after the header).
""")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        # Read the CSV. We don't specify column names here;
        # pandas will infer them or assign default integers (0, 1, 2...)
        df = pd.read_csv(uploaded_file)

        # Prepare data: list of (first_column_value, second_column_value) tuples
        # We assume the first column (index 0) is task id and second (index 1) is sentence.
        data_to_process = []
        for index, row in df.iterrows():
            if len(row) >= 2: # Ensure there are at least two columns
                data_to_process.append((row.iloc[0], row.iloc[1])) # Use .iloc to get by positional index
            else:
                st.warning(f"Row {index + 2} skipped: Not enough columns (expected at least 2).") # +2 for 1-based row after header

        if not data_to_process:
            st.warning("No valid data rows found after processing. Please check your CSV format.")
        else:
            st.success("File uploaded successfully! Processing...")

            with st.spinner("Checking for repeated sequences... This might take a while for large files."):
                repeated_seqs_data = find_repeated_sequences(data_to_process, min_length=15)

            if repeated_seqs_data:
                st.subheader("Repeated Sequences Found:")
                st.write("The following sequences of 15 characters or more were found in multiple sentences:")
                for seq, occurrences in repeated_seqs_data.items():
                    st.markdown(f"**Sequence:** `{seq}`")
                    
                    # Filter occurrences to only show unique sentences where it appears for summary
                    unique_sentences_for_summary = set(occ[0] for occ in occurrences) # Use row index for uniqueness

                    st.write(f"This sequence appears in {len(unique_sentences_for_summary)} unique sentences across the dataset:")
                    
                    # Display all occurrences
                    for original_row_idx, task_id, sentence, char_idx in occurrences:
                        # Highlight the repeated sequence
                        if len(sentence) >= char_idx + len(seq):
                            highlighted_sentence = sentence[:char_idx] + \
                                                   f"<mark>**{sentence[char_idx : char_idx + len(seq)]}**</mark>" + \
                                                   sentence[char_idx + len(seq):]
                        else: 
                            highlighted_sentence = sentence # Fallback if for some reason index is out of bounds
                        
                        st.markdown(f"- **Row {original_row_idx}** | **Task ID:** `{task_id}` | **Sentence:** {highlighted_sentence}", unsafe_allow_html=True)
                    st.markdown("---")
            else:
                st.info("No repeated sequences of 15 characters or more found in the sentences.")

    except Exception as e:
        st.error(f"An unexpected error occurred during file processing: {e}. Please ensure your CSV file is correctly formatted.")

st.markdown("""
---
*Note: This app performs a simple substring search. It might not catch semantically similar but syntactically different phrases.*
*It processes all rows from the CSV, assuming the first row is a header and subsequent rows contain the data in the first two columns.*
""")
