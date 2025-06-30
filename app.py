import streamlit as st
import pandas as pd
from collections import Counter
import io # Required for in-memory CSV creation

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

    for original_row_idx, row_data in enumerate(data_rows):
        # Handle cases where row_data might not have enough elements gracefully
        task_id = str(row_data[0]) if len(row_data) > 0 else "N/A"
        sentence = str(row_data[1]) if len(row_data) > 1 else ""
        
        if pd.isna(sentence) or len(sentence) < min_length: # Skip if sentence is NaN or too short
            continue

        for j in range(len(sentence) - min_length + 1):
            seq = sentence[j : j + min_length]
            all_sequences_data.append((seq, original_row_idx + 2, task_id, sentence, j)) # +2 for 1-based row display after header

    grouped_sequences = {}
    for seq_text, original_row_idx, task_id, sentence, char_idx in all_sequences_data:
        if seq_text not in grouped_sequences:
            grouped_sequences[seq_text] = []
        grouped_sequences[seq_text].append((original_row_idx, task_id, sentence, char_idx))

    repeated_sequences = {}

    for seq_text, occurrences in grouped_sequences.items():
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
        df = pd.read_csv(uploaded_file, header=None) # Read without header
        
        data_to_process = []
        # Iterate from the second row (index 1) onwards for actual data
        for index in range(1, len(df)): # Start from index 1 to skip header
            row = df.iloc[index]
            
            if len(row) >= 2: # Ensure there are at least two columns
                data_to_process.append((row.iloc[0], row.iloc[1])) # Use .iloc to get by positional index
            else:
                st.warning(f"Row {index + 1} skipped (CSV row number, including header): Not enough columns (expected at least 2).")

        if not data_to_process:
            st.warning("No valid data rows found after processing. Please check your CSV format and ensure it has at least 2 columns and data beyond the header.")
        else:
            st.success("File uploaded successfully! Processing...")

            with st.spinner("Checking for repeated sequences... This might take a while for large files."):
                repeated_seqs_data = find_repeated_sequences(data_to_process, min_length=15)

            if repeated_seqs_data:
                st.subheader("Repeated Sequences Found:")
                st.write("The following sequences of 15 characters or more were found in multiple sentences:")
                
                export_data = [] # List to store data for export CSV
                
                for seq, occurrences in repeated_seqs_data.items():
                    st.markdown(f"**Sequence:** `{seq}`")
                    
                    unique_sentences_for_summary = set(occ[0] for occ in occurrences) # Use row index for uniqueness

                    st.write(f"This sequence appears in {len(unique_sentences_for_summary)} unique sentences across the dataset:")
                    
                    for original_row_idx, task_id, sentence, char_idx in occurrences:
                        # Prepare data for export
                        export_data.append({
                            "Repeated Sequence": seq,
                            "Length of Sequence (chars)": len(seq),
                            "Original Row": original_row_idx,
                            "Task ID": task_id,
                            "Full Sentence": sentence
                        })

                        # Highlight for display
                        if len(sentence) >= char_idx + len(seq):
                            highlighted_sentence = sentence[:char_idx] + \
                                                   f"<mark>**{sentence[char_idx : char_idx + len(seq)]}**</mark>" + \
                                                   sentence[char_idx + len(seq):]
                        else: 
                            highlighted_sentence = sentence # Fallback
                        
                        st.markdown(f"- **Row {original_row_idx}** | **Task ID:** `{task_id}` | **Sentence:** {highlighted_sentence}", unsafe_allow_html=True)
                    st.markdown("---")
                
                st.info("Generating download file...") # <-- New debugging message
                export_df = pd.DataFrame(export_data)
                
                st.download_button(
                    label="Download Results as CSV",
                    data=export_df.to_csv(index=False, encoding='utf-8-sig'), # utf-8-sig for proper Thai display in Excel
                    file_name="repeated_sequences_report.csv",
                    mime="text/csv"
                )

            else:
                st.info("No repeated sequences of 15 characters or more found in the sentences.")

    except pd.errors.EmptyDataError:
        st.error("The uploaded CSV file is empty.")
    except Exception as e:
        st.error(f"An unexpected
