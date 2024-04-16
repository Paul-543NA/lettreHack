import lipsum
from typing import List, Tuple, Dict

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