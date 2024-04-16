import lipsum
import csv
from scipy.spatial.distance import cosine
from typing import List, Tuple, Dict
from transformers import BartTokenizer, BartForConditionalGeneration
!pip install 'transformers[torch]'
!pip install transformers
from sentence_transformers import SentenceTransformer
st_model = SentenceTransformer('paraphrase-MiniLM-L6-v2')
import pandas as pd
import spacy
import nltk

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

def fetch_letters(mock_data=True) -> Dict[str, Dict[str, str]]:
    if not mock_data:
        # Fetch data from the database
        pass
    return {
        "letter1": {
            "id": "letter1",
            "data_sent": "2021-01-01",
            "sender": "John Doe",
            "transcript": lipsum.generate_words(100),
            "summary": lipsum.generate_words(10),
            "recommended_department": "HMRC",
            "umage_url": "https://via.placeholder.com/150"
        },
        "letter2": {
            "id": "letter2",
            "data_sent": "2021-01-01",
            "sender": "Jane Doe",
            "transcript": lipsum.generate_words(100),
            "summary": lipsum.generate_words(10),
            "recommended_department": "Minister of Defense",
            "umage_url": "https://via.placeholder.com/150"
        },
        "letter3": {
            "id": "letter3",
            "data_sent": "2021-01-01",
            "sender": "John Doe",
            "transcript": lipsum.generate_words(100),
            "summary": lipsum.generate_words(10),
            "recommended_department": "Department of Health",
            "umage_url": "https://via.placeholder.com/150"
        },
        "letter4": {
            "id": "letter4",
            "data_sent": "2021-01-01",
            "sender": "Jane Doe",
            "transcript": lipsum.generate_words(100),
            "summary": lipsum.generate_words(10),
            "recommended_department": "HMRC",
            "umage_url": "https://via.placeholder.com/150"
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

# test = summarize('single-page-letters.csv')
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


