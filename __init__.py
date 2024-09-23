import sys
import os
import json
import requests
from aqt import mw
from aqt.qt import QAction, QInputDialog
from aqt.utils import showInfo
from anki.notes import Note

addon_path = os.path.dirname(__file__)
lib_path = os.path.join(addon_path, "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

# Function to get or set the OpenAI API key
def get_openai_api_key():
    config_file = os.path.join(addon_path, "config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)
            return config.get("OPENAI_API_KEY")
    else:
        api_key, ok = QInputDialog.getText(mw, "OpenAI API Key", "Enter your OpenAI API key:")
        if ok and api_key:
            with open(config_file, "w") as f:
                json.dump({"OPENAI_API_KEY": api_key}, f)
            return api_key
    return None

# Get the OpenAI API key
OPENAI_API_KEY = get_openai_api_key()

if not OPENAI_API_KEY:
    showInfo(
        "OpenAI API key not found.\n"
        "Please enter a valid OpenAI API key when prompted."
    )
    def generate_card_with_openai():
        showInfo("OpenAI API key is not set. Cannot generate card.")
        return
else:
    def generate_card_with_openai():
        # Prompt the user for a topic.
        topic, ok = QInputDialog.getText(
            mw, "Enter Topic", "Enter the topic for the flashcard:"
        )
        if not ok or not topic:
            return

        # Create the prompt for the OpenAI API.
        prompt = (
            f"Generate a flashcard on the topic of {topic}. "
            "Provide the output strictly in JSON format with the keys 'question' and 'answer'. "
            "Do not include any additional text."
        )

        try:
            # Make the API call to OpenAI.
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are an expert teacher."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
            response.raise_for_status()

            # Extract the assistant's response.
            content = response.json()['choices'][0]['message']['content']

            # Parse the JSON output.
            flashcard = json.loads(content)

            question = flashcard.get('question')
            answer = flashcard.get('answer')

            if not question or not answer:
                showInfo("Failed to get valid flashcard data.")
                return

            # Prepare the note.
            deck_name = "OpenAI Generated Cards"
            model_name = "Basic"

            # Get or create the deck.
            deck_id = mw.col.decks.id(deck_name)
            mw.col.decks.select(deck_id)

            # Get the model.
            model = mw.col.models.byName(model_name)
            if not model:
                showInfo(f"Model '{model_name}' not found.")
                return

            # Create a new note.
            note = Note(mw.col, model)
            note.fields[0] = question  # Front side of the card.
            note.fields[1] = answer    # Back side of the card.

            # Add the note to the collection.
            mw.col.addNote(note)
            mw.col.reset()
            mw.reset()
            showInfo("Added a new card from OpenAI!")
        except json.JSONDecodeError:
            showInfo("The response was not valid JSON.")
        except requests.exceptions.RequestException as e:
            showInfo(f"OpenAI API error: {str(e)}")
        except Exception as e:
            showInfo(f"An unexpected error occurred: {str(e)}")

def generate_trivia_card():
    # Fetch a trivia question from an API
    response = requests.get("https://opentdb.com/api.php?amount=1&type=multiple")
    if response.status_code != 200:
        showInfo("Failed to fetch trivia question.")
        return

    data = response.json()
    question_data = data['results'][0]

    question = question_data['question']
    correct_answer = question_data['correct_answer']
    incorrect_answers = question_data['incorrect_answers']

    # Prepare the note
    deck_name = "Trivia"
    model_name = "Basic"

    # Get the deck and model
    deck_id = mw.col.decks.id(deck_name)
    mw.col.decks.select(deck_id)
    model = mw.col.models.byName(model_name)
    if not model:
        showInfo(f"Model '{model_name}' not found.")
        return

    # Create a new note
    note = Note(mw.col, model)
    note.fields[0] = question  # Front
    note.fields[1] = correct_answer  # Back

    # Add the note to the collection
    mw.col.addNote(note)
    mw.col.reset()
    mw.reset()
    showInfo("Added a new trivia card!")

def add_menu_items():
    trivia_action = QAction("Generate Trivia Card", mw)
    trivia_action.triggered.connect(generate_trivia_card)
    mw.form.menuTools.addAction(trivia_action)

    openai_action = QAction("Generate Card with OpenAI", mw)
    openai_action.triggered.connect(generate_card_with_openai)
    mw.form.menuTools.addAction(openai_action)

add_menu_items()
