import streamlit as st
import pandas as pd
from collections import Counter

def find_repeated_sequences(sentences_with_ids, min_length=15):
    """
    Finds repeated sequences of text within a list of (task_id, sentence) tuples.

    Args:
        sentences_with_ids (list): A list of tuples, where each tuple is (task_id, sentence_string).
        min_length (int): The minimum length of the repeated sequence to consider.

    Returns:
        dict: A dictionary where keys are repeated sequences and values are
              a list of tuples (original_row_index, task_id, sentence_string, start_char_index)
              where they were found.
    """
    all_sequences_data = [] # Stores (sequence_text, original_row_index, task_id, sentence, start_char_index)

    # Generate all possible sequences of min_length or greater from each sentence
    # We'll use the original row index from the DataFrame (0-based)
    for original_row_idx, (task_id, sentence) in enumerate(sentences_with_ids):
        if pd.isna(sentence): # Skip if sentence is NaN
            continue
        for j in range(len(sentence) - min_length + 1):
            seq = sentence[j : j + min_length]
            all_sequences_data.append((seq, original_row_idx + 1, task_id, sentence, j)) # +1 for 1-based row display

    # Group sequences by their text content
    grouped_sequences = {}
    for seq_text, original_row_idx, task_id, sentence, char_idx in all_sequences_data:
        if seq_text not in grouped_sequences:
            grouped_sequences[seq_text] = []
        grouped_sequences[seq_text].append((original_row_idx, task_id, sentence, char_idx))

    repeated_sequences = {}

    for seq_text, occurrences in grouped_sequences.items():
        # Check if the sequence appears in more than one *unique* sentence (based on task_id/original_row_index)
        # To avoid counting multiple occurrences within the same sentence as "repeated across sentences"
        unique_sentence_occurrences = set((occ[0], occ[1]) for occ in occurrences) # (original_row_index, task_id)
        
        if len(unique_sentence_occurrences) > 1:
            repeated_sequences[seq_text] = occurrences
            
    return repeated_sequences


st.set_page_config(layout="wide")
st.title("CSV Sentence Sequence Checker (Thai)")

st.markdown("""
This app checks a CSV file for repeated sequences of text within the 'sentence' column.
It will identify sequences longer than 15 characters that appear in multiple sentences.
The app assumes your CSV has a header row and 'task id' and 'sentence' columns.
Processing will start from the second row of the CSV.
""")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        # Read the CSV, assuming header is present and data starts from row 2
        df = pd.read_csv(uploaded_file)

        # We assume 'task id' and 'sentence' columns exist.
        # Ensure we are working with string type for sentences to prevent errors with NaNs.
        df['sentence'] = df['sentence'].astype(str)

        # Prepare data: list of (task_id, sentence) tuples
        # We process all rows, as the problem states "from row 2 onwards" implies processing the entire data after header.
        sentences_to_process = []
        for index, row in df.iterrows():
            sentences_to_process.append((row['task id'], row['sentence']))

        st.success("File uploaded successfully! Processing...")

        with st.spinner("Checking for repeated sequences... This might take a while for large files."):
            repeated_seqs_data = find_repeated_sequences(sentences_to_process, min_length=15)

        if repeated_seqs_data:
            st.subheader("Repeated Sequences Found:")
            st.write("The following sequences of 15 characters or more were found in multiple sentences:")
            for seq, occurrences in repeated_seqs_data.items():
                st.markdown(f"**Sequence:** `{seq}`")
                
                # Filter occurrences to only show unique sentences where it appears for summary
                unique_sentences_for_summary = set()
                for original_row_idx, task_id, sentence, char_idx in occurrences:
                    unique_sentences_for_summary.add((original_row_idx, task_id))

                st.write(f"This sequence appears in {len(unique_sentences_for_summary)} unique sentences across the dataset:")
                
                # Display all occurrences, including potentially multiple within the same sentence
                for original_row_idx, task_id, sentence, char_idx in occurrences:
                    # Highlight the repeated sequence
                    highlighted_sentence = sentence[:char_idx] + \
                                           f"<mark>**{sentence[char_idx : char_idx + len(seq)]}**</mark>" + \
                                           sentence[char_idx + len(seq):]
                    
                    st.markdown(f"- **Row {original_row_idx}** | **Task ID:** `{task_id}` | **Sentence:** {highlighted_sentence}", unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No repeated sequences of 15 characters or more found in the sentences.")

    except KeyError as ke:
        st.error(f"Error: Missing expected column. Please ensure your CSV has 'task id' and 'sentence' columns. Detail: {ke}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}. Please ensure your CSV file is correctly formatted.")

st.markdown("""
---
*Note: This app performs a simple substring search. It might not catch semantically similar but syntactically different phrases.*
*It processes all rows from the CSV, assuming the first row is a header and subsequent rows contain 'task id' and 'sentence' data.*
""")
