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
            repeated_sequences[sub_text] = list(source_set)
    
    return repeated_sequences

# --- Streamlit App ---
st.set_page_config(layout="wide")
st.title("⚡ Fast CSV Sentence Repetition Checker")

st.markdown("""
Upload a CSV file with columns: task ID and sentence.
This tool detects repeated substrings across different rows.
""")

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])
user_length = st.number_input("Minimum sequence length:", min_value=2, max_value=500, value=20)

max_preview = st.slider("How many repeated sequences to preview?", 0, 100, 10, step=5)

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
            st.success("Processing...")

            with st.spinner("Finding repeated sequences..."):
                all_found_sequences_data = find_repeated_sequences(data_to_process, user_length)

            export_data = []
            for seq, occurrences in all_found_sequences_data.items():
                for original_csv_row_number, task_id, sentence in occurrences:
                    export_data.append({
                        "Repeated Sequence": seq,
                        "Length of Sequence (chars)": len(seq),
                        "Original CSV Row Number": original_csv_row_number,
                        "Task ID": task_id,
                        "Full Sentence": sentence
                    })

            if export_data:
                export_df = pd.DataFrame(export_data)
                export_df.sort_values(by=["Repeated Sequence", "Task ID", "Full Sentence"], inplace=True)

                # --- Download Button ---
                st.download_button(
                    label="📥 Download All Results (CSV)",
                    data=export_df.to_csv(index=False, encoding='utf-8-sig'),
                    file_name=f"repeated_sequences_minlen_{user_length}.csv",
                    mime="text/csv"
                )

                # --- Optional Preview ---
                if max_preview > 0:
                    st.markdown(f"### 🔍 Top {max_preview} repeated sequences preview")
                    preview_df = export_df.drop_duplicates(subset=["Repeated Sequence"]).head(max_preview)
                    for _, row in preview_df.iterrows():
                        st.markdown(f"- **Sequence:** `{row['Repeated Sequence']}` ({row['Length of Sequence (chars)']} chars)")

            else:
                st.info("No repeated sequences found.")

    except pd.errors.EmptyDataError:
        st.error("Uploaded file is empty.")
    except Exception as e:
        st.error(f"Error: {e}")

st.markdown("---\n_Optimized for large datasets. Designed for Thai sentence analysis._")
