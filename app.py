import streamlit as st
import pandas as pd
from collections import defaultdict

def find_repeated_sequences(data_rows, min_length_for_search):
    all_substrings_sources = defaultdict(set)

    for original_row_idx_df, row_data in enumerate(data_rows):
        original_csv_row_number = original_row_idx_df + 2 
        task_id = str(row_data[0]) if len(row_data) > 0 else "N/A"
        sentence = str(row_data[1]) if len(row_data) > 1 else ""
        
        if pd.isna(sentence) or len(sentence) < min_length_for_search:
            continue

        for i in range(len(sentence) - min_length_for_search + 1):
            for k in range(min_length_for_search, len(sentence) - i + 1):
                sub = sentence[i : i + k]
                source_tuple = (original_csv_row_number, task_id, sentence)
                all_substrings_sources[sub].add(source_tuple)

    repeated_sequences = {}

    for sub_text, source_set in all_substrings_sources.items():
        if len(source_set) > 1:
            occurrences_list = []
            for (csv_row_num, tid, full_sent) in source_set:
                start_idx = 0
                while True:
                    start_idx = full_sent.find(sub_text, start_idx)
                    if start_idx == -1:
                        break
                    occurrences_list.append((csv_row_num, tid, full_sent, start_idx))
                    start_idx += 1
            if occurrences_list:
                repeated_sequences[sub_text] = occurrences_list
    
    return repeated_sequences

# --- Streamlit App ---
st.set_page_config(layout="wide")
st.title("CSV Sentence Repetition Checker (Thai)")

st.markdown("""
Upload a CSV file with at least two columns: task ID and sentence.
This tool finds and highlights **repeated sequences of text** across multiple rows.
""")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
user_length = st.number_input("Minimum sequence length to search for:", min_value=2, max_value=1000, value=20, step=1)

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, header=None)
        data_to_process = []

        for index in range(1, len(df)):
            row = df.iloc[index]
            if len(row) >= 2:
                data_to_process.append((row.iloc[0], row.iloc[1]))

        if not data_to_process:
            st.warning("No valid data rows found.")
        else:
            st.success("File uploaded. Processing...")

            with st.spinner(f"Searching for repeated sequences of at least {user_length} characters..."):
                all_found_sequences_data = find_repeated_sequences(data_to_process, user_length)

            export_data = []
            st.markdown(f"### Results (Min Length: {user_length} characters)")
            st.markdown(f"**Found {len(all_found_sequences_data)} unique repeated sequences**")

            for seq, occurrences in sorted(all_found_sequences_data.items(), key=lambda x: len(x[0]), reverse=True):
                for original_csv_row_number, task_id, sentence, char_idx in occurrences:
                    export_data.append({
                        "Repeated Sequence": seq,
                        "Length of Sequence (chars)": len(seq),
                        "Original CSV Row Number": original_csv_row_number,
                        "Task ID": task_id,
                        "Full Sentence": sentence
                    })

            if export_data:
                # Sort before export
                export_df = pd.DataFrame(export_data)
                export_df.sort_values(by=["Repeated Sequence", "Task ID", "Full Sentence"], inplace=True)
                
                # Download button at top
                st.download_button(
                    label="📥 Download Results as CSV",
                    data=export_df.to_csv(index=False, encoding='utf-8-sig'),
                    file_name=f"repeated_sequences_minlen_{user_length}.csv",
                    mime="text/csv"
                )

                # Render results
                for seq, occurrences in sorted(all_found_sequences_data.items(), key=lambda x: len(x[0]), reverse=True):
                    st.markdown(f"---\n#### Sequence: `{seq}` (Length: {len(seq)} chars)")
                    for original_csv_row_number, task_id, sentence, char_idx in occurrences:
                        if len(sentence) >= char_idx + len(seq):
                            highlighted = sentence[:char_idx] + \
                                          f"<mark><b>{sentence[char_idx : char_idx + len(seq)]}</b></mark>" + \
                                          sentence[char_idx + len(seq):]
                        else:
                            highlighted = sentence
                        st.markdown(f"- **Row {original_csv_row_number}** | **Task ID:** `{task_id}` | **Sentence:** {highlighted}", unsafe_allow_html=True)
            else:
                st.info("No repeated sequences found.")

    except pd.errors.EmptyDataError:
        st.error("Uploaded file is empty.")
    except Exception as e:
        st.error(f"Error while processing file: {e}")

st.markdown("---\n_Developed for Thai CSV sentence deduplication and substring analysis._")
