import json
import uuid
from base64 import b64encode
from anthropic import Anthropic
from pathlib import Path

from google.cloud import storage
from firebase_admin import db

BUCKET_NAME = "bucket-images-correspondance"
CREDENTIALS_FILE = Path("./gcs_credentials.json")
CREDENTIALS_FILE_2 = Path("./credentials.json")
CREDENTIALS = json.load(open(CREDENTIALS_FILE_2))
ANTHROPIC_API_KEY = CREDENTIALS["ANTHROPIC_API_KEY"]

def upload_to_gcs(bucket_name, source_file_path, destination_blob_name, credentials_file):
    # Initialize the Google Cloud Storage client with the credentials
    storage_client = storage.Client.from_service_account_json(credentials_file)

    # Get the target bucket
    bucket = storage_client.bucket(bucket_name)

    # Upload the file to the bucket
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)

def send_blob_to_gcs(blob, image_id):
    # Write the blob into a file
    with open(f"{image_id}.jpg", "wb") as f:
        f.write(blob)

    # Upload the file to GCS
    upload_to_gcs(BUCKET_NAME, f"{image_id}.jpg", f"{image_id}.jpg", CREDENTIALS_FILE)

    # Remove the temporary file
    Path(f"{image_id}.jpg").unlink()


def get_image_url_from_gcs(bucket_name, blob_name, credentials_file):
    # Initialize the Google Cloud Storage client with the credentials
    storage_client = storage.Client.from_service_account_json(credentials_file)

    # Get the target bucket
    bucket = storage_client.bucket(bucket_name)

    # Get the blob URL
    blob = bucket.blob(blob_name)
    return blob.public_url


def upload_image_metadata_to_firestore(image_metadata, image_id):
    # Get the reference to the database
    ref = db.reference("/lettres")
    image_metadata["image_url"] = get_image_url_from_gcs(BUCKET_NAME, f"{image_id}.jpg", CREDENTIALS_FILE)

    print("Res:")
    # Print the final json nicely
    print(json.dumps(image_metadata, indent=4))

    # Add the metadata to the database
    ref.child(image_id).set(image_metadata)

def extract_metadata_From_image(image_blob, image_id):
    fields = [
        {
            "title": "Date",
            "tag": "date",
            "description": "The date the letter was written in YYYY-MM-DD format, or N/A if unknown. If the year and month are known but not the day, use the first day of the month.",
        },
        {
            "title": "Sender",
            "tag": "sender",
            "description": "The person or department which sent the letter, or N/A if unknown",
        },
        {
            "title": "Recipient",
            "tag": "recipient",
            "description": "The person or department which received the letter, or N/A if unknown",
        },
        {
            "title": "Subject",
            "tag": "subject",
            "description": "A one-line subject of the letter if present, otherwise infer this yourself from the context",
        },
        {
            "title": "Document type",
            "tag": "document-type",
            "description": "State the category type of the document (letter, meeting minutes, balance sheet etc)",
        },
    ]

    fields_string = "\n".join(
        f"- {field['title']}: {field['description']}. Use the key name '{field['tag']}' ."
        for field in fields
    )
    prompt = f"""

    Transcribe the text in this image in full, in json format, with the key "text".

    Please also extract the following fields:

    {fields_string}

    """.strip()

    client = Anthropic(
        api_key=ANTHROPIC_API_KEY,
    )
    image_media_type = "image/jpeg"
    print("Sending to Claude-3...")
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image_media_type,
                            "data": b64encode(image_blob).decode("utf-8"),
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    parsed_doc = message.content[0].text
    data = parsed_doc

    try:
        if not data.startswith("{"):
            data = data[data.index("{"):]
    except ValueError as e:
        data = '{\n    "text": "",\n    "date": "N/A",\n    "sender": "N/A",\n    "recipient": "N/A",\n    "subject": "N/A",\n    "document-type": "N/A"\n}'
    if not data.endswith("{"):
        data = data[: data.rfind("}") + 1]
    try:
        data.index("}")
    except ValueError as ve:
        print(f"File is not complete")
        pass
    try:
        data.index('"date":')
    except ValueError as ve:
        print(f"File is not complete")
        pass
    if data.index("}") < data.index('"date":'):
        data = (
                data[: data.index("}")]
                + ","
                + data[data[data.find("{") + 1:].find("{") + 2:]
        )

    json_f = json.loads(data)
    json_f["source"] = image_id

    ## SECOND PROMPT

    print("Sending to Claude-3 again...")
    ministry_descriptions = {
        "Prime Minister's Office, No. 10 Downing Street": '10 Downing Street is the official residence and the office of the British Prime Minister. The office helps the Prime Minister to establish and deliver the government’s overall strategy and policy priorities, and to communicate the government’s policies to Parliament, the public and international audiences.',
        "Attorney General's Office": 'The Attorney General’s Office (AGO) provides legal advice and support to the Attorney General and the Solicitor General (the Law Officers) who give legal advice to government. The AGO helps the Law Officers perform other duties in the public interest, such as looking at sentences which may be too low.',
        'Cabinet Office': 'We support the Prime Minister and ensure the effective running of government. We are also the corporate headquarters for government, in partnership with HM Treasury, and we take the lead in certain critical policy areas.',
        'Department for Business and Trade': 'We are the department for economic growth. We support businesses to invest, grow and export, creating jobs and opportunities across the country.',
        'Department fot Culture, Media and Sport': 'The Department for Culture, Media and Sport supports culture, arts, media, sport, tourism and civil society across every part of England — recognising the UK’s world-leading position in these areas and the importance of these sectors in contributing so much to our economy, way of life and our reputation around the world.',
        'Department for Education': 'The Department for Education is responsible for children’s services and education, including early years, schools, higher and further education policy, apprenticeships and wider skills in England.',
        'Department for Energy, Security and Net Zero': 'Securing our long-term energy supply, bringing down bills and halving inflation.',
        'Department for Environment, Food and Rural Affairs': 'We are responsible for improving and protecting the environment. We aim to grow a green economy and sustain thriving rural communities. We also support our world-leading food, farming and fishing industries.',
        'Department for Levelling-up, Housing and Communities': 'The Department for Levelling Up, Housing and Communities supports communities across the UK to thrive, making them great places to live and work.',
        'Department for Science, Innovation and Technology': 'Driving innovation that will deliver improved public services, create new better-paid jobs and grow the economy.',
        'Department for Transport': 'We work with our agencies and partners to support the transport network that helps the UK’s businesses and gets people and goods travelling around the country. We plan and invest in transport infrastructure to keep the UK on the move.',
        'Department for Work and Pensions': 'The Department for Work and Pensions (DWP) is responsible for welfare, pensions and child maintenance policy. As the UK’s biggest public service department it administers the State Pension and a range of working age, disability and ill health benefits to around 20 million claimants and customers.',
        'Department for Health and Social Care': 'We support ministers in leading the nation’s health and social care to help people live more independent, healthier lives for longer.',
        'Foreign, Commonwealth and Development Office': 'We support ministers in leading the nation’s health and social care to help people live more independent, healthier lives for longer.',
        'HM Treasury': 'HM Treasury is the government’s economic and finance ministry, maintaining control over public spending, setting the direction of the UK’s economic policy and working to achieve strong and sustainable economic growth.',
        'Home Office': 'The first duty of the government is to keep citizens safe and the country secure. The Home Office plays a fundamental role in the security and economic prosperity of the UK.',
        'Ministry of Defence': 'We work for a secure and prosperous United Kingdom with global reach and influence. We will protect our people, territories, values and interests at home and overseas, through strong armed forces and in partnership with allies, to ensure our security, support our national interests and safeguard our prosperity.',
        'Ministry of Justice': 'The Ministry of Justice is a major government department, at the heart of the justice system. We work to protect and advance the principles of justice. Our vision is to deliver a world-class justice system that works for everyone in society.',
        'Northern Ireland Office': 'We ensure the smooth working of the devolution settlement in Northern Ireland.',
        'Office of the Advocate General for Scotland': 'The Office of the Advocate General (OAG) is the UK government’s Scottish legal team.\n\nWe provide legal advice, drafting and litigation services to the UK government in relation to Scotland.\n\nWe also support the Advocate General in his role as a Law Officer.',
        'Office of the Leader of the House of Commons': 'We provide support to the Leader of the House of Commons, who is responsible for planning and supervising the government’s legislative programme (including the King’s speech), and managing government business within the House of Commons while also upholding the rights and interests of the backbench members of the House.',
        'Office of the Leader of the House of Lords': 'We provide support to the Leader of the House of Lords. The Leader of the House is appointed by the Prime Minister, is a member of Cabinet, and is responsible for the conduct of government business in the Lords. The Leader advises the House on procedure and order, and she and her office are available to assist and advise all members of the House.',
        'Office of the Secretary of State for Scotland': 'The Office of the Secretary of State for Scotland supports the Secretary of State in promoting the best interests of Scotland within a stronger United Kingdom. It ensures Scottish interests are fully and effectively represented at the heart of the UK government, and the UK government’s responsibilities are fully and effectively represented in Scotland.',
        'Office of the Secretary of State for Wales': 'The Office of the Secretary of State for Wales supports the Welsh Secretary and the Parliamentary Under Secretary of State in promoting the best interests of Wales within a stronger United Kingdom. It ensures Welsh interests are represented at the heart of the UK government and the UK government’s responsibilities are represented in Wales.',
        'UK Export Finance': 'We advance prosperity by ensuring no viable UK export fails for lack of finance or insurance, doing that sustainably and at no net cost to the taxpayer.'}

    prompt = f"""
    You are an assistant that works for the UK Government that helps determine, given text from a letter, which gov department is responsible for replying to a given letter. This determination is formed from the content of the letter, figure out the relevant policy area and determine the department whose responsibility it is to form a response.
    Multiple departments can be given but generally it should be kept to 1.

    Give your response in JSON only. Do not write any other text other than the JSON data.
    Use JSON format with the keys "department" and "justification"
    Justification should be very brief (i.e. x policy is covered in the remit by x department)

    ---

    The following are government departments you can consider with their remit:
    {ministry_descriptions}

    ---

    Letter:\n
    """

    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": (prompt + json_f["text"]).strip()}
        ],
    )
    triage_res = message.content[0].text
    triage_res_dict = json.loads(triage_res.removeprefix("```json").removesuffix("```"))

    # Merge the two responses
    json_f["Departments"] = triage_res_dict["department"]
    json_f["Department_Justification"] = triage_res_dict["justification"]
    json_f["summary"] = "John Greenborough has sent you a copy of the excellent CBI Resolution on the Budget, which Clive showed you on Wednesday. He also offers his good wishes for the Summit. I attach a draft reply to the CBI's resolution. I will send it to the Prime Minister in due course."

    return json_f


def upload_image(image_blob):
    image_id = "z" + str(uuid.uuid4())
    print("Getting metadata from image...")
    image_metadata = extract_metadata_From_image(image_blob, image_id)
    image_metadata["id"] = image_id
    print(f"Uploading ID to GCS: {image_id}")
    send_blob_to_gcs(image_blob, image_id)
    print(f"Uploading metadata to Firestore with ID: {image_id}")
    upload_image_metadata_to_firestore(image_metadata, image_id)
    # send_blob_to_gcs(image_blob, image_id)
    print(f"Image uploaded with ID: {image_id}")