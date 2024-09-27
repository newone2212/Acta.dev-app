from flask import Flask, request, jsonify
import json
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

manage_file = 'manage.json'

# Load the manage.json file or create it if it doesn't exist
# try:
#     with open(manage_file, 'r') as file:
#         manage_data = json.load(file)
# except FileNotFoundError:
#     manage_data = {}


def save_sentences_to_doc(sentences, transcript_id):
    # Ensure the transcripts directory exists
    os.makedirs("transcripts", exist_ok=True)
    file_path = os.path.join("transcripts", f"{transcript_id}.doc")
    
    with open(file_path, 'w') as f:
        for sentence in sentences:
            speaker_name = sentence.get('speaker_name', 'Unknown Speaker')
            raw_text = sentence.get('raw_text', '')
            f.write(f"{speaker_name}: {raw_text}\n")
    
    return file_path
    

def fetch_transcript(transcript_id):
    url = os.getenv('API_URL')
    payload = json.dumps({
        "query": """
        query Transcript($transcriptId: String!) {
            transcript(id: $transcriptId) {
                audio_url
                video_url
                participants
                sentences {
                    raw_text
                    speaker_name
                }
            }
        }""",
        "variables": {
            "transcriptId": transcript_id
        }
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer b2a7bb7c-a1b2-4edc-b301-1b3ec186dd2c'
    }

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


def create_bite(transcript_id, start_time, end_time, media_type):
    url = os.getenv('API_URL')
    payload = json.dumps({
        "query": """
        mutation CreateBite($transcriptId: ID!, $startTime: Float!, $endTime: Float!, $mediaType: String!) {
            createBite(transcript_Id: $transcriptId, start_time: $startTime, end_time: $endTime, media_type: $mediaType) {
                summary
                status
                id
            }
        }""",
        "variables": {
            "transcriptId": transcript_id,
            "startTime": start_time,
            "endTime": end_time,
            "mediaType": media_type
        }
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer f0ce832c-f0cf-454b-8058-15231e49ae02'
    }

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def fetch_transcripts(user_id):
    try:
        url = os.getenv('API_URL')
        print(url)
        payload = json.dumps({
            "query": """
                query Transcripts($userId: String) {
                    transcripts(user_id: $userId) {
                        title
                        id
                    }
                }""",
                "variables": {
                    "userId": user_id
                }
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer b2a7bb7c-a1b2-4edc-b301-1b3ec186dd2c'
        }

        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            result = response.json()
            # Extract the list of transcripts
            transcripts = result.get('data', {}).get('transcripts', [])
            return transcripts
        else:
            response.raise_for_status()
    except Exception as e:
        print(str(e))

manage_file = 'manage.json'

# Load the existing data from the file
if os.path.exists(manage_file):
    with open(manage_file, 'r') as file:
        manage_data = json.load(file)
else:
    manage_data = {}

@app.route('/add_meeting', methods=['POST'])
def add_meeting():
    try:
        data = request.json
        name = data.get('name')
        url = data.get('url')

        if not name or not url:
            return jsonify({'error': 'Name and URL are required'}), 400

        # Check if the name is already in the manage_data
        if name in manage_data:
            return jsonify({'error': 'Name already exists'}), 400

        manage_data[name] = url
        with open(manage_file, 'w') as file:
            json.dump(manage_data, file, indent=4)

        return jsonify({'message': 'Meeting added successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/join_meeting', methods=['POST'])
def join_meeting():
    try:
        data = request.json
        name = data.get('name')

        if not name or name not in manage_data:
            return jsonify({'error': 'Name is required and must be in the list'}), 400

        meeting_link = manage_data[name]

        api_url = os.getenv('API_URL')
        bearer_token = os.getenv('BEARER_TOKEN')

        payload = json.dumps({
            "query": "mutation AddToLiveMeeting($meetingLink: String!) { addToLiveMeeting(meeting_link: $meetingLink) { success } }",
            "variables": {
                "meetingLink": meeting_link
            }
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {bearer_token}'
        }

        response = requests.post(api_url, headers=headers, data=payload)

        if response.status_code == 200:
            return jsonify({'message': 'Joined meeting successfully'}), 200
        else:
            return jsonify({'error': 'Failed to join meeting'}), 500
    except Exception as e:
        return jsonify({"error":str(e)})


@app.route('/select_recording', methods=['GET'])
def select_recording():
    try:
        # data = request.json
        user_id = os.getenv('user_id')

        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400

         # Fetch transcripts using the function
        transcripts = fetch_transcripts(user_id)

        return jsonify({'transcripts': transcripts}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process_transcript', methods=['POST'])
def process_transcript():
    try:
        data = request.json
        transcript_id = data.get('transcript_id')

        if not transcript_id:
            return jsonify({'error': 'Transcript ID is required'}), 400

        # Step 1: Create a bite
        create_bite_response = create_bite(transcript_id, 0, 3600, 'audio')
        
        if 'errors' in create_bite_response:
            return jsonify({'error': 'Failed to create bite', 'details': create_bite_response['errors']}), 500

        # Extract summary from create_bite_response
        summary = create_bite_response.get('data', {}).get('createBite', {}).get('summary', 'No summary available')

        # Step 2: Fetch the transcript details
        transcript_response = fetch_transcript(transcript_id)
        
        # if 'errors' in transcript_response:
        #     return jsonify({'error': 'Failed to fetch transcript', 'details': transcript_response['errors']}), 500

        # Extract audio URL and sentences from transcript_response
        transcript_data = transcript_response.get('data', {}).get('transcript', {})
        audio_url = transcript_data.get('audio_url', 'No audio URL available')
        sentences = transcript_data.get('sentences', [])

        # Save sentences to a document in the "transcripts" folder
        doc_path = save_sentences_to_doc(sentences, transcript_id)

        return jsonify({'summary': summary, 'audio_url': audio_url, 'doc_path': doc_path}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

if __name__ == '__main__':
    app.run(debug=True)
