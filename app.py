import streamlit as st
import pandas as pd
from collections import Counter
import io

# --- Configuration ---
MIN_SEQUENCE_LENGTH = 20

def find_repeated_sequences(data_rows, min_length=MIN_SEQUENCE_LENGTH):
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
    all_sequences_data = []

    for original_row_idx_df, row_data in enumerate(data_rows):
        original_csv_row_number = original_row_idx_df + 2 

        task_id = str(row_data[0]) if len(row_data) > 0 else "N/A"
        sentence = str(row_data[1]) if len(row_data) > 1 else ""
        
        if pd.isna(sentence) or len(sentence) < min_length:
            continue

        for j in range(len(sentence) - min_length + 1):
            seq = sentence[j : j + min_length]
            all_sequences_data.append((seq, original_csv_row_number, task_id, sentence, j))

    grouped_sequences = {}
    for seq_text, original_csv_row_number, task_id, sentence, char_idx in all_sequences_data:
        if seq_text not in grouped_sequences:
            grouped_sequences[seq_text] = []
        grouped_sequences[seq_text].append((original_csv_row_number, task_id, sentence, char_idx))

    repeated_sequences = {}

    for seq_text, occurrences in grouped_sequences.items():
        unique_sentence_rows = set(occ[0] for occ in occurrences)
        
        if len(unique_sentence_rows) > 1:
            repeated_sequences[seq_text] = occurrences
            
    return repeated_sequences


st.set_page_config(layout="wide")
st.title("CSV Sentence Sequence Checker (Thai)")

st.markdown(f"""
This app checks a CSV file for repeated sequences of text within the sentence data.
It identifies sequences **longer than {MIN_SEQUENCE_LENGTH} characters** that appear in multiple sentences.
**The app assumes your CSV has a header row and that the first column contains 'task id'
and the second column contains 'sentence' data.** Processing starts from the second row (after the header).
""")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, header=None)
        
        data_to_process = []
        for index in range(1, len(df)):
            row = df.iloc[index]
            
            if len(row) >= 2:
                data_to_process.append((row.iloc[0], row.iloc[1]))
            else:
                st.warning(f"Row {index + 1} skipped (CSV row number, including header): Not enough columns (expected at least 2).")

        if not data_to_process:
            st.warning("No valid data rows found after processing. Please check your CSV format and ensure it has at least 2 columns and data beyond the header.")
        else:
            st.success("File uploaded successfully! Processing...")

            with st.spinner("Checking for repeated sequences... This might take a while for large files."):
                repeated_seqs_data = find_repeated_sequences(data_to_process, min_length=MIN_SEQUENCE_LENGTH)

            if repeated_seqs_data:
                st.subheader("Repeated Sequences Found:")
                
                # --- Prepare data for CSV Export first ---
                export_data = []
                seen_export_entries = set() 
                
                for seq, occurrences in repeated_seqs_data.items():
                    for original_csv_row_number, task_id, sentence, char_idx in occurrences:
                        entry_key = (seq, original_csv_row_number, task_id, sentence)

                        if entry_key not in seen_export_entries:
                            seen_export_entries.add(entry_key)
                            export_data.append({
                                "Repeated Sequence": seq,
                                "Length of Sequence (chars)": len(seq),
                                "Original CSV Row Number": original_csv_row_number,
                                "Task ID": task_id,
                                "Full Sentence": sentence
                            })
                
                # --- Place Download Button on Top ---
                if export_data:
                    st.info("Download your results below:")
                    export_df = pd.DataFrame(export_data)
                    
                    st.download_button(
                        label="Download Results as CSV",
                        data=export_df.to_csv(index=False, encoding='utf-8-sig'),
                        file_name="repeated_sequences_report.csv",
                        mime="text/csv"
                    )
                    st.markdown("---") # Add a separator after the button
                    
                # --- Then, display individual results ---
                st.write(f"The following sequences of {MIN_SEQUENCE_LENGTH} characters or more were found in multiple sentences:")
                
                for seq, occurrences in repeated_seqs_data.items():
                    st.markdown(f"**Sequence:** `{seq}`")
                    
                    unique_sentences_for_summary = set(occ[0] for occ in occurrences)

                    st.write(f"This sequence appears in {len(unique_sentences_for_summary)} unique sentences across the dataset:")
                    
                    for original_csv_row_number, task_id, sentence, char_idx in occurrences:
                        if len(sentence) >= char_idx + len(seq):
                            highlighted_sentence = sentence[:char_idx] + \
                                                   f"<mark>**{sentence[char_idx : char_idx + len(seq)]}**</mark>" + \
                                                   sentence[char_idx + len(seq):]
                        else: 
                            highlighted_sentence = sentence
                        
                        st.markdown(f"- **Row {original_csv_row_number}** | **Task ID:** `{task_id}` | **Sentence:** {highlighted_sentence}", unsafe_allow_html=True)
                    st.markdown("---")
                
            else:
                st.info(f"No repeated sequences of {MIN_SEQUENCE_LENGTH} characters or more found in the sentences.")

    except pd.errors.EmptyDataError:
        st.error("The uploaded CSV file is empty.")
    except Exception as e:
        st.error(f"An unexpected error occurred during file processing: {e}. Please ensure your CSV file is correctly formatted.")

st.markdown("""
---
*Note: This app performs a simple substring search. It might not catch semantically similar but syntactically different phrases.*
*It processes all rows from the CSV, assuming the first row is a header and subsequent rows contain the data in the first two columns.*
""")
