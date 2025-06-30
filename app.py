import streamlit as st
import pandas as pd
from collections import defaultdict
import io

# --- Configuration ---
CHECK_LENGTHS = [20, 40, 60] # The specific lengths to check for
# The smallest length to search for initially; ensures we capture all possible candidates
SMALLEST_CHECK_LENGTH = min(CHECK_LENGTHS) 

def find_repeated_sequences(data_rows, min_length_for_search=SMALLEST_CHECK_LENGTH):
    """
    Identifies all unique substrings of length >= min_length_for_search that appear
    in more than one unique original sentence.

    Args:
        data_rows (list): A list of tuples, where each tuple is (task_id, sentence_string).
        min_length_for_search (int): The absolute minimum length for substrings to consider.

    Returns:
        dict: A dictionary where keys are repeated sequences (str) and values are
              a list of tuples (original_csv_row_number, task_id, sentence_string, start_char_index)
              where they were found. The 'seq' (key) will now be the full length of the repeated substring found.
    """
    # Stores {substring_text: set_of_source_tuples}
    # A source_tuple is (original_csv_row_number, task_id, full_sentence)
    all_substrings_sources = defaultdict(set)

    for original_row_idx_df, row_data in enumerate(data_rows):
        original_csv_row_number = original_row_idx_df + 2 

        task_id = str(row_data[0]) if len(row_data) > 0 else "N/A"
        sentence = str(row_data[1]) if len(row_data) > 1 else ""
        
        if pd.isna(sentence) or len(sentence) < min_length_for_search:
            continue

        # Generate ALL substrings of length >= min_length_for_search
        # This is computationally intensive for very long sentences/many sentences.
        for i in range(len(sentence) - min_length_for_search + 1):
            for k in range(min_length_for_search, len(sentence) - i + 1):
                sub = sentence[i : i + k]
                source_tuple = (original_csv_row_number, task_id, sentence)
                all_substrings_sources[sub].add(source_tuple)

    repeated_sequences = {} # {seq_text: list_of_occurrences_full_details}
    
    # Filter for substrings that appear in more than one unique source sentence
    for sub_text, source_set in all_substrings_sources.items():
        if len(source_set) > 1:
            occurrences_list = []
            for (csv_row_num, tid, full_sent) in source_set:
                # Find all start indices of sub_text within full_sent to report occurrences
                start_idx = 0
                while True:
                    start_idx = full_sent.find(sub_text, start_idx)
                    if start_idx == -1:
                        break
                    occurrences_list.append((csv_row_num, tid, full_sent, start_idx))
                    # Move past the found substring to find non-overlapping occurrences within the same sentence
                    # If you need overlapping matches, remove `+1` (or change to `+len(sub_text)`)
                    start_idx += 1 

            if occurrences_list:
                repeated_sequences[sub_text] = occurrences_list
    
    return repeated_sequences


st.set_page_config(layout="wide")
st.title("CSV Sentence Sequence Checker (Thai)")

st.markdown(f"""
This app checks a CSV file for repeated sequences of text within the sentence data.
It provides results categorized by sequence length: **{', '.join(map(str, sorted(CHECK_LENGTHS)))} characters**.
Sequences are prioritized: a sequence found to be 60+ chars long will only appear in the 60+ category,
not in the 40-59 or 20-39 categories.

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

            with st.spinner(f"Searching for all repeated sequences of at least {SMALLEST_CHECK_LENGTH} characters. This might take some time for large files..."):
                all_found_sequences_data = find_repeated_sequences(data_to_process, min_length_for_search=SMALLEST_CHECK_LENGTH)

            # --- Exclusive Categorization Logic ---
            # Initialize containers for exclusive results (seq_text: occurrences_list)
            # Use a dict with key=threshold and value=dict_of_sequences_for_this_threshold
            exclusive_results = {length: {} for length in CHECK_LENGTHS}
            
            # Sort lengths in descending order for prioritization (e.g., [60, 40, 20])
            sorted_check_lengths_desc = sorted(CHECK_LENGTHS, reverse=True)

            # Use a set to ensure each unique sequence text is categorized only once
            processed_sequences_text = set() 

            for seq_text, occurrences in all_found_sequences_data.items():
                if seq_text in processed_sequences_text:
                    continue # This check is important if a smaller substring was already categorized as part of a larger one.

                seq_len = len(seq_text)

                for threshold in sorted_check_lengths_desc:
                    if seq_len >= threshold:
                        # Add to this category and mark as processed.
                        exclusive_results[threshold][seq_text] = occurrences
                        processed_sequences_text.add(seq_text) 
                        break # Assign to the highest matching category and move on

            # --- Prepare Export DataFrames and Display Sections ---
            st.subheader("Repealed Sequences Found (Prioritized by Length):")
            st.markdown(f"**Total unique sequences found across all categories: {len(processed_sequences_text)}**")
            st.markdown("---")
            
            # Use a list to store data for download buttons for better layout
            download_buttons_data = []

            any_results_found = False

            # Create and display buttons and results for each category
            for threshold in sorted_check_lengths_desc: # Iterate in descending order for display
                category_label_display = ""
                if threshold == max(CHECK_LENGTHS):
                    category_label_display = f"{threshold}+ Characters"
                elif threshold == min(CHECK_LENGTHS) and len(CHECK_LENGTHS) > 1:
                    # For the smallest threshold, indicate the upper bound if not caught by higher categories
                    next_higher_threshold_idx = sorted(CHECK_LENGTHS).index(threshold) + 1
                    upper_bound = sorted(CHECK_LENGTHS)[next_higher_threshold_idx] - 1
                    category_label_display = f"{threshold}-{upper_bound} Characters"
                else: # For intermediate thresholds
                    next_higher_threshold_idx = sorted(CHECK_LENGTHS).index(threshold) + 1
                    upper_bound = sorted(CHECK_LENGTHS)[next_higher_threshold_idx] - 1
                    category_label_display = f"{threshold}-{upper_bound} Characters"

                current_category_sequences = exclusive_results[threshold]
                
                if current_category_sequences:
                    any_results_found = True
                    st.markdown(f"#### {category_label_display}")
                    st.write(f"Found {len(current_category_sequences)} unique repeated sequences in this category.")
                    
                    export_data_for_category = []
                    seen_export_entries_for_category = set() # For de-duplication in export CSV

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
                        "label": f"Download {category_label_display} (CSV)",
                        "data": export_df_category.to_csv(index=False, encoding='utf-8-sig'),
                        "file_name": f"repeated_sequences_{threshold}_chars.csv"
                    })
                    st.markdown("<br>", unsafe_allow_html=True) # Space before next category
            
            # Render download buttons prominently at the top
            if download_buttons_data:
                st.info("Download results for each category below:")
                # Sort buttons by their original threshold order (ascending) for consistent display
                download_buttons_data.sort(key=lambda x: int(x['file_name'].split('_')[2])) 
                
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
            
            if not any_results_found:
                 st.info(f"No repeated sequences of at least {SMALLEST_CHECK_LENGTH} characters found meeting the criteria.")


    except pd.errors.EmptyDataError:
        st.error("The uploaded CSV file is empty.")
    except Exception as e:
        st.error(f"An unexpected error occurred during file processing: {e}. Please ensure your CSV file is correctly formatted.")

st.markdown("""
---
*Note: This app performs a substring search to find repeated sequences. It might not catch semantically similar but syntactically different phrases.*
*It processes all rows from the CSV, assuming the first row is a header and subsequent rows contain the data in the first two columns.*
""")
