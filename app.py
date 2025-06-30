import streamlit as st
import pandas as pd
from collections import Counter
import io

# --- Configuration ---
CHECK_LENGTHS = [20, 40, 60] # The specific lengths to check for
# The smallest length to search for initially, ensures we capture all possible candidates
SMALLEST_CHECK_LENGTH = min(CHECK_LENGTHS) 

def find_repeated_sequences(data_rows, min_length_for_search=SMALLEST_CHECK_LENGTH):
    """
    Finds repeated sequences of text within a list of (task_id, sentence) tuples.
    This function finds all sequences >= min_length_for_search that are repeated.
    Categorization by specific lengths (e.g., 20, 40, 60) happens outside this function.

    Args:
        data_rows (list): A list of tuples, where each tuple is (task_id, sentence_string).
                          task_id is assumed to be the first element, sentence the second.
        min_length_for_search (int): The absolute minimum length for substrings to consider
                                     as a potential repeated sequence.

    Returns:
        dict: A dictionary where keys are repeated sequences (str) and values are
              a list of tuples (original_csv_row_number, task_id, sentence_string, start_char_index)
              where they were found.
    """
    all_sequences_data = []

    for original_row_idx_df, row_data in enumerate(data_rows):
        # original_row_idx_df is 0-based from the DataFrame slice (after header removal)
        # So, +2 gives the 1-based row number in the original CSV (including header)
        original_csv_row_number = original_row_idx_df + 2 

        # Handle cases where row_data might not have enough elements gracefully
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
        # Check if the sequence appears in more than one *unique* sentence (based on original_csv_row_number)
        unique_sentence_rows = set(occ[0] for occ in occurrences)
        
        if len(unique_sentence_rows) > 1:
            repeated_sequences[seq_text] = occurrences
            
    return repeated_sequences


st.set_page_config(layout="wide")
st.title("CSV Sentence Sequence Checker (Thai)")

st.markdown(f"""
This app checks a CSV file for repeated sequences of text within the sentence data.
It provides results categorized by sequence length: **{', '.join(map(str, sorted(CHECK_LENGTHS)))} characters**.
Sequences are prioritized, meaning a 60-char sequence will only appear in the 60+ category, not in 40+ or 20+.

**The app assumes your CSV has a header row and that the first column contains 'task id'
and the second column contains 'sentence' data.** Processing starts from the second row (after the header).
""")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, header=None)
        
        data_to_process = []
        for index in range(1, len(df)): # Start from index 1 to skip the header row
            row = df.iloc[index]
            
            if len(row) >= 2: # Ensure there are at least two columns
                data_to_process.append((row.iloc[0], row.iloc[1]))
            else:
                st.warning(f"Row {index + 1} skipped (CSV row number, including header): Not enough columns (expected at least 2).")

        if not data_to_process:
            st.warning("No valid data rows found after processing. Please check your CSV format and ensure it has at least 2 columns and data beyond the header.")
        else:
            st.success("File uploaded successfully! Processing...")

            with st.spinner(f"Searching for all repeated sequences of at least {SMALLEST_CHECK_LENGTH} characters..."):
                all_found_sequences_data = find_repeated_sequences(data_to_process, min_length_for_search=SMALLEST_CHECK_LENGTH)

            # --- Exclusive Categorization Logic ---
            # Initialize containers for exclusive results (seq_text: occurrences_list)
            exclusive_results = {length: {} for length in CHECK_LENGTHS}
            
            # Sort lengths in descending order for prioritization
            sorted_check_lengths_desc = sorted(CHECK_LENGTHS, reverse=True)

            processed_sequences_text = set() # To ensure each unique sequence text is categorized only once

            for seq_text, occurrences in all_found_sequences_data.items():
                if seq_text in processed_sequences_text:
                    continue # Already categorized by a higher priority length

                seq_len = len(seq_text)

                assigned_to_category = False
                for threshold in sorted_check_lengths_desc:
                    if seq_len >= threshold:
                        exclusive_results[threshold][seq_text] = occurrences
                        assigned_to_category = True
                        break # Assign to the highest matching category and move on
                
                processed_sequences_text.add(seq_text) # Mark sequence text as processed for categorization

            # --- Prepare Export DataFrames and Display Sections ---
            st.subheader("Repeated Sequences Found (Prioritized by Length):")
            
            # List to store tuples for download buttons for better layout
            download_buttons_data = []

            any_results_found = False

            # Create and display buttons and results for each category
            for threshold in sorted_check_lengths_desc:
                category_label = f"{threshold}+ Characters"
                if threshold == min(CHECK_LENGTHS):
                    # For the smallest threshold, indicate the upper bound if not caught by higher categories
                    category_label = f"{threshold}-{max(CHECK_LENGTHS)-1} Characters" if len(CHECK_LENGTHS) > 1 else f"{threshold}+ Characters"

                current_category_sequences = exclusive_results[threshold]
                
                if current_category_sequences:
                    any_results_found = True
                    st.markdown(f"#### {category_label}")
                    
                    export_data_for_category = []
                    seen_export_entries_for_category = set()

                    for seq, occurrences in current_category_sequences.items():
                        seq_len = len(seq)
                        for original_csv_row_number, task_id, sentence, char_idx in occurrences:
                            entry_key = (seq, original_csv_row_number, task_id, sentence)
                            if entry_key not in seen_export_entries_for_category:
                                seen_export_entries_for_category.add(entry_key)
                                export_data_for_category.append({
                                    "Repeated Sequence": seq,
                                    "Length of Sequence (chars)": seq_len,
                                    "Original CSV Row Number": original_csv_row_number,
                                    "Task ID": task_id,
                                    "Full Sentence": sentence
                                })
                        
                        # Display for UI
                        st.markdown(f"**Sequence:** `{seq}` (Length: {seq_len} chars)")
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
                        st.markdown("---") # Separator for each sequence

                    # Add download button data for this category
                    export_df_category = pd.DataFrame(export_data_for_category)
                    download_buttons_data.append({
                        "label": f"Download {category_label} (CSV)",
                        "data": export_df_category.to_csv(index=False, encoding='utf-8-sig'),
                        "file_name": f"repeated_sequences_{threshold}plus_report.csv"
                    })
                    st.markdown("<br>", unsafe_allow_html=True) # Space before next category
            
            # Render download buttons at the top if results found in any category
            if download_buttons_data:
                st.info("Download results for each category below:")
                cols = st.columns(len(download_buttons_data)) # Create columns for buttons
                for i, btn_data in enumerate(download_buttons_data):
                    with cols[i]:
                        st.download_button(
                            label=btn_data["label"],
                            data=btn_data["data"],
                            file_name=btn_data["file_name"],
                            mime="text/csv"
                        )
                st.markdown("---") # Separator after buttons
            elif not any_results_found:
                 st.info(f"No repeated sequences of at least {SMALLEST_CHECK_LENGTH} characters found meeting the criteria.")


    except pd.errors.EmptyDataError:
        st.error("The uploaded CSV file is empty.")
    except Exception as e:
        st.error(f"An unexpected error occurred during file processing: {e}. Please ensure your CSV file is correctly formatted.")

st.markdown("""
---
*Note: This app performs a simple substring search. It might not catch semantically similar but syntactically different phrases.*
*It processes all rows from the CSV, assuming the first row is a header and subsequent rows contain the data in the first two columns.*
""")
