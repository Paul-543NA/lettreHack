import lipsum
import csv
from scipy.spatial.distance import cosine
from typing import List, Tuple, Dict
from transformers import BartTokenizer, BartForConditionalGeneration
from sentence_transformers import SentenceTransformer
st_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
import pandas as pd

from pathlib import Path
from firebase_admin import db
from google.cloud import storage

BUCKET_NAME = "bucket-images-correspondance"
CREDENTIALS_FILE = Path("./gcs_credentials.json")

def upload_to_gcs(bucket_name, source_file_path, destination_blob_name, credentials_file):
    # Initialize the Google Cloud Storage client with the credentials
    storage_client = storage.Client.from_service_account_json(credentials_file)

    # Get the target bucket
    bucket = storage_client.bucket(bucket_name)

    # Upload the file to the bucket
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)

    print(f"File {source_file_path} uploaded to gs://{bucket_name}/{destination_blob_name}")

def get_image_url_from_gcs(bucket_name, blob_name, credentials_file):
    # Initialize the Google Cloud Storage client with the credentials
    storage_client = storage.Client.from_service_account_json(credentials_file)

    # Get the target bucket
    bucket = storage_client.bucket(bucket_name)

    # Get the blob URL
    blob = bucket.blob(blob_name)
    return blob.public_url

def get_department_recommendation(transcript: str)  -> List[str]:
    return ["HMRC", "Minister of Defense", "Department of Health"]

def get_transccript_abd_metadata_from_image(image_file: str) -> Dict[str, str]:
    return {
        "transcript": "This is a transcript",
        "data_sent": "2021-01-01",
        "sender": "John Doe",
        "sentiment": "positive",
    }

def get_summary_from_transcript(transcript: str) -> str:
    return "This is a summary"

def get_relevant_letters_For_keyword(keyword: str, letters: Dict[str, str]) -> List[str]:
    return ["letter1", "letter2"]

def fetch_letters(mock_data=False) -> Dict[str, Dict[str, str]]:

    if not mock_data:
        # Fetch data from firestore
        ref = db.reference("/lettres")
        lettres_list: List = ref.get()
        lettres_dict = {}
        for key, lettre in lettres_list.items():
            lettres_dict[lettre["id"]] = lettre
            # Add the url to the letter id column
            lettres_dict[lettre["id"]]["lid"] = f"[{lettre['id']}]({lettre['image_url']})"
        return lettres_dict

    return {
        "letter1": {
            'id': 0,
            'text': "SECRET\n\nCHANCELLOR\n\nTreasurable\n(1) P.J Ledl\n(2) The Ptiley Hr.\n\nR. secroo:\n\ncc Chief Secretary\nFinancial Secretary\nSir D Mass\nSir L Airey\nSir F Atkinson\nSir K Couzens\nMr Barrett\nMr Littler\nMr Brideman\nMr Hancock\nMr Middleton\nMr Unwin\nMr P G Davies\nMr Pottrill\nMr Gill\nMrs Gilmore\nMr Hodges\nMrs Lomax\nMr Folger\nMr Williams\nMr Macrae\nMr Ridley\nMr Cardona\nMr Cropper\n\nMr Fforde\nChief Cashier\nMr Goodhart\n\nSPEECH TO THE INSTITUTE OF BANKERS, FRIDAY 16 NOVEMBER\n\nI attach a draft speech which concentrates on monetary policy\nbut contains also a section prepared by Mr Hancock on exchange\ncontrols.  The material may not be entirely consistent with\nthe latest version of tomorrow's statement, and has not yet\nbeen checked",
            'date': '1979-11-15',
            'sender': 'C J RILEY',
            'recipient': 'Chancellor',
            'subject': 'Speech to the Institute of Bankers',
            'document-type': 'Letter',
            'source': 'PREM 19-34/0001/-39.jpg',
            'Departments': 'HM Treasury',
            'Department_Justification': "The letter discusses matters related to monetary policy and exchange controls, which fall under the remit of the HM Treasury as the government's economic and finance ministry.",
        },
        "letter2": {
            'id': 1,
            'text': lipsum.generate_sentences(10),
            'date': '1979-11-15',
            'sender': 'C J RILEY',
            'recipient': 'Chancellor',
            'subject': 'Speech to the Institute of Bankers',
            'document-type': 'Letter',
            'source': 'PREM 19-34/0001/-39.jpg',
            'Departments': 'HM Treasury',
            'Department_Justification': "The letter discusses matters related to monetary policy and exchange controls, which fall under the remit of the HM Treasury as the government's economic and finance ministry.",
        },
    }

class BARTSummariser:
    
    def __init__(self, model_dir):
        self.tokenizer = BartTokenizer.from_pretrained(model_dir)
        self.model = BartForConditionalGeneration.from_pretrained(model_dir)
        
    def summarize(self, text, max_length=1024, min_length=100, length_penalty=2.0, num_beams=4):
        inputs = self.tokenizer.encode("summarize: " + text, return_tensors='pt', max_length=1024, truncation=True)
        summary_ids = self.model.generate(inputs, max_length=max_length, min_length=min_length, length_penalty=length_penalty, num_beams=num_beams)
        summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary
        
def chunk_text(text,chunk_size=1024, delimiter='\n'):
    """
    Splits the text into chunks with a max_size of Bart, ideally breaking at the specified delimiter
    """
    chunks = []
    current_chunk = ""

    def add_chunk(chunk):
        while len(chunk) > chunk_size:
            split_index = chunk.rfind(delimiter, 0,max_chunk_size)
            if split_index == -1:
                split_index = max_chunk_size
            chunks.append(chunk[:split_index].strip())
            chunk = chunk[split_index:].lstrip()
        if chunk:
            chunks.append(chunk.strip())
    for paragraph in text.split(delimiter):
        if len(current_chunk) + len(paragraph) + len(delimiter) > chunk_size:
            add_chunk(current_chunk)
            current_chunk = paragraph + delimiter
        else:
            current_chunk += paragraph + delimiter
    if current_chunk:
        add_chunk(current_chunk)
    return chunks 

def batch_summaries(summaries, batch_size):
    """Organize summaries into batches based on a simple count limit."""
    batches = []
    current_batch = []
    current_count = 0
    for summary in summaries:
        if current_count + len(summary.split()) > batch_size:
            batches.append(current_batch)
            current_batch = [summary]
            current_count = len(summary.split())
        else:
            current_batch.append(summary)
            current_count += len(summary.split())
    if current_batch:  # Add the last batch if it has content
        batches.append(current_batch)
    return batches

def iterative_summarization(summaries, summarizer, min_length, max_length):
    """Summarize summaries in batches to manage token limit, then combine."""
    batched_summaries = batch_summaries(summaries, 1024 // max_length)
    refined_summaries = [summarizer.summarize(' '.join(batch), min_length=min_length, max_length=max_length) for batch in batched_summaries]
    return ' '.join(refined_summaries)

def summarize(data_path, chunk_size=1024, max_length=75):  # Assuming 75 tokens is around 30 words for your use case (adjust as needed)
  """
  This function summarizes transcripts from a CSV file using a pre-trained BART model.

  Args:
      data_path: Path to the CSV file containing transcripts (one transcript per row).
      chunk_size: The maximum size of each text chunk for summarization (default 1024 tokens).
      max_length: The maximum length allowed for both chunk summaries and the final summary (adjusted to roughly 30 words).

  Returns:
      A list of summaries, one for each transcript in the CSV.
  """
  summarizer = BARTSummariser('/tmp/huggingface/bart-large-cnn')

  # Read transcripts from CSV
  transcripts = []
  with open(data_path, 'r', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
      transcript = row[0]  # Assuming transcripts are in the first column (adjust index if needed)
      transcripts.append(transcript)
        
  summaries = []
  for transcript in transcripts:
    # Chunk the transcript if necessary
    if len(summarizer.tokenizer.encode(transcript, return_tensors="pt")) > chunk_size:
      chunks = summarizer.tokenizer(transcript, max_length=chunk_size, return_tensors="pt")
      chunk_summaries = []
      for chunk in chunks.input_ids:
        summary = summarizer.model.generate(chunk, max_length=max_length)  # Summarize each chunk
        summary_text = summarizer.tokenizer.decode(summary[0], skip_special_tokens=True)
        chunk_summaries.append(summary_text)
      final_summary = " ".join(chunk_summaries)  # Combine chunk summaries
    else:
      # Summarize the entire transcript if it's within chunk size
      summary = summarizer.model.generate(summarizer.tokenizer.encode(transcript, return_tensors="pt"), max_length=max_length)
      final_summary = summarizer.tokenizer.decode(summary[0], skip_special_tokens=True)

    summaries.append(final_summary)

  return summaries



def add_summaries_to_csv(data_path, summaries, summary_column_name="Summary"):
  """
  Adds a summaries list as a new column to a CSV file.

  Args:
      data_path: Path to the CSV file.
      summaries: A list of strings containing summaries (one summary per row, assumed to match the order of transcripts in the CSV).
      summary_column_name: The name of the new column where summaries will be added (default: "Summary").

  Returns:
      None (Modifies the original CSV file)
  """

  # Read existing data from CSV
  with open(data_path, 'r', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    rows = list(reader)  # Convert reader object to a list

  # Check if summaries length matches original data
  if len(summaries) != len(rows):
    raise ValueError(f"Summaries list length ({len(summaries)}) doesn't match CSV rows ({len(rows)}).")

  # Create a DataFrame from summaries
  summary_df = pd.DataFrame({"summary": summaries})

    # Add summary column using existing logic
  updated_rows = []
  for i, row in enumerate(rows):
    summary = summary_df.iloc[i]["summary"]
    updated_rows.append(row + [summary])

  # Write updated data with summaries back to the CSV
  with open(data_path, 'w', encoding='utf-8', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerows(updated_rows)

###################### test = summarize('single-page-letters.csv')
###################### add_summaries_to_csv('single-page-letters.csv',test)
# need to define keyword as input

def semantic_search_from_csv(csv_path, keyword, top_k=5, threshold=0.8):
  """
  Performs semantic search on a CSV file based on keyword and cosine similarity.

  Args:
      csv_path: Path to the CSV file containing transcripts (one transcript per row).
      keyword: The keyword or phrase to search for.
      top_k: The number of top similar documents to return (default: 5).
      threshold: The minimum cosine similarity score to consider a document relevant (default: 0.8).

  Returns:
      A list of top_k tuples containing (row index, transcript, cosine similarity score).
  """

  # Read transcripts from CSV
  transcripts = []
  with open(csv_path, 'r', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
      transcript = row[0]  # Assuming transcripts are in the first column (adjust index if needed)
      transcripts.append(transcript)

  # Encode transcripts
  document_embeddings = st_model.encode(transcripts)

  # Get keyword embedding
  query_embedding = st_model.encode(keyword)

  # Perform semantic search
  similarities = []
  for i, doc_embedding in enumerate(document_embeddings):
    similarity = cosine(query_embedding, doc_embedding)
    similarities.append((i, transcripts[i], similarity))  # Store transcript along with index and similarity

  # Apply threshold and sort by similarity (descending)
  filtered_results = [(i, transcript, sim) for i, transcript, sim in similarities if sim >= threshold]
  sorted_results = sorted(filtered_results, key=lambda x: x[2], reverse=True)[:top_k]

  return sorted_results


def get_full_info_from_jpeg(image_data: bytes) -> Dict[str, str]:
    return {
        "transcript": "This is a transcript",
        "data_sent": "2021-01-01",
        "sender": "John Doe",
        "sentiment": "positive",
    }

