import streamlit as st
import pandas as pd
from collections import Counter
import io

# --- Configuration ---
CHECK_LENGTHS = [20, 40, 60] # The lengths to check for
SMALLEST_CHECK_LENGTH = min(CHECK_LENGTHS) # The minimum length for initial search

def find_repeated_sequences(data_rows, min_length_for_search=SMALLEST_CHECK_LENGTH):
    """
    Finds repeated sequences of text within a list of (task_id, sentence) tuples.
    This function finds all sequences >= min_length_for_search.
    Categorization by specific lengths (e.g., 20, 40, 60) happens outside this function.

    Args:
        data_rows (list): A list of tuples, where each tuple is (task_id, sentence_string).
                          task_id is assumed to be the first element, sentence the second.
        min_length_for_search (int): The absolute minimum length for substrings to consider.

    Returns:
        dict: A dictionary where keys are repeated sequences (str) and values are
              a list of tuples (original_csv_row_number, task_id, sentence_string, start_char_index)
              where they were found.
    """
    all_sequences_data = []

    for original_row_idx_df, row_data in enumerate(data_rows):
        original_csv_row_number = original_row_idx_df + 2 

        task_id = str(row_data[0]) if len(row_data) > 0 else "N/A"
        sentence = str(row_data[1]) if len(row_data) > 1 else ""
        
        if pd.isna(sentence) or len(sentence) < min_length_for_search:
            continue

        for j in range(len(sentence) - min_length_for_search + 1):
            seq = sentence[j : j + min_length_for_search]
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
It identifies sequences longer than **{', '.join(map(str, CHECK_LENGTHS))} characters**.
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

            with st.spinner(f"Checking for repeated sequences of at least {SMALLEST_CHECK_LENGTH} characters... This might take a while for large files."):
                repeated_seqs_data = find_repeated_sequences(data_to_process, min_length_for_search=SMALLEST_CHECK_LENGTH)

            if repeated_seqs_data:
                st.subheader("Repeated Sequences Found:")
                
                export_data = []
                seen_export_entries = set() 
                
                # --- Prepare data for CSV Export first and categorize for display ---
                categorized_results = {length: [] for length in CHECK_LENGTHS}
                
                for seq, occurrences in repeated_seqs_data.items():
                    current_seq_length = len(seq)
                    
                    # Populate export_data for CSV (de-duplicated)
                    for original_csv_row_number, task_id, sentence, char_idx in occurrences:
                        entry_key = (seq, original_csv_row_number, task_id, sentence)
                        if entry_key not in seen_export_entries:
                            seen_export_entries.add(entry_key)
                            export_data.append({
                                "Repeated Sequence": seq,
                                "Length of Sequence (chars)": current_seq_length, # Actual length of the sequence
                                "Original CSV Row Number": original_csv_row_number,
                                "Task ID": task_id,
                                "Full Sentence": sentence
                            })
                    
                    # Categorize for display (allowing a sequence to appear in multiple categories if it crosses thresholds)
                    # For example, a 65-char sequence will appear in 20+, 40+, and 60+ sections
                    for threshold in sorted(CHECK_LENGTHS):
                        if current_seq_length >= threshold:
                            categorized_results[threshold].append((seq, occurrences))


                # --- Place Download Button on Top ---
                if export_data:
                    st.info("Download your comprehensive results below:")
                    export_df = pd.DataFrame(export_data)
                    
                    st.download_button(
                        label="Download All Repeated Sequences (CSV)",
                        data=export_df.to_csv(index=False, encoding='utf-8-sig'),
                        file_name="repeated_sequences_report.csv",
                        mime="text/csv"
                    )
                    st.markdown("---") 
                    
                # --- Then, display individual results categorized by length ---
                st.write("Results categorized by minimum sequence length:")

                found_any_in_categories = False
                for threshold in sorted(CHECK_LENGTHS):
                    sequences_for_this_threshold = [item for item in categorized_results[threshold] if len(item[0]) >= threshold]
                    
                    if sequences_for_this_threshold:
                        found_any_in_categories = True
                        st.subheader(f"Sequences of {threshold} Characters or More:")
                        st.write(f"Found {len(sequences_for_this_threshold)} unique repeated sequences of at least {threshold} characters.")

                        for seq, occurrences in sequences_for_this_threshold:
                            st.markdown(f"**Sequence:** `{seq}` (Length: {len(seq)} chars)")
                            
                            unique_sentences_for_summary = set(occ[0] for occ in occurrences)
                            st.write(f"This sequence appears in {len(unique_sentences_for_summary)} unique sentences:")
                            
                            for original_csv_row_number, task_id, sentence, char_idx in occurrences:
                                if len(sentence) >= char_idx + len(seq):
                                    highlighted_sentence = sentence[:char_idx] + \
                                                           f"<mark>**{sentence[char_idx : char_idx + len(seq)]}**</mark>" + \
                                                           sentence[char_idx + len(seq):]
                                else: 
                                    highlighted_sentence = sentence
                                
                                st.markdown(f"- **Row {original_csv_row_number}** | **Task ID:** `{task_id}` | **Sentence:** {highlighted_sentence}", unsafe_allow_html=True)
                            st.markdown("---")
                    
                if not found_any_in_categories:
                    st.info(f"No repeated sequences of at least {SMALLEST_CHECK_LENGTH} characters found meeting the criteria.")
                
            else:
                st.info(f"No repeated sequences of at least {SMALLEST_CHECK_LENGTH} characters found in the sentences.")

    except pd.errors.EmptyDataError:
        st.error("The uploaded CSV file is empty.")
    except Exception as e:
        st.error(f"An unexpected error occurred during file processing: {e}. Please ensure your CSV file is correctly formatted.")

st.markdown("""
---
*Note: This app performs a simple substring search. It might not catch semantically similar but syntactically different phrases.*
*It processes all rows from the CSV, assuming the first row is a header and subsequent rows contain the data in the first two columns.*
""")
