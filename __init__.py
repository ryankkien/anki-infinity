import sys
import os
import json
import requests
from aqt import mw
from aqt.qt import QAction, QInputDialog, QMessageBox
from aqt.utils import showInfo
from anki.notes import Note
import random

addon_path = os.path.dirname(__file__)
lib_path = os.path.join(addon_path, "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

# Function to get or set the OpenAI API key and other configurations
def get_config():
    config_file = os.path.join(addon_path, "config.json")
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return json.load(f)
    else:
        config = {}
        # Prompt for OpenAI API Key
        api_key, ok = QInputDialog.getText(mw, "OpenAI API Key", "Enter your OpenAI API key:")
        if ok and api_key:
            config["OPENAI_API_KEY"] = api_key
        else:
            showInfo("OpenAI API key is required to use this add-on.")
            return {}
        # Set default for preview feature
        config["PREVIEW_ENABLED"] = False
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
        return config

# Load configuration
config = get_config()

# Function to save configuration
def save_config():
    config_file = os.path.join(addon_path, "config.json")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=4)

# Get the OpenAI API key
OPENAI_API_KEY = config.get("OPENAI_API_KEY")

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
        # Prompt the user to select a deck
        decks = mw.col.decks.all_names_and_ids()
        deck_names = [d.name for d in decks]
        if not deck_names:
            showInfo("No decks found. Please create a deck first.")
            return
        deck_name, ok = QInputDialog.getItem(
            mw, "Select Deck", "Select the deck to add the card to:", deck_names, 0, False
        )
        if not ok or not deck_name:
            return

        # Get the deck ID
        # Find the deck ID corresponding to the selected deck name
        deck_id = None
        for d in decks:
            if d.name == deck_name:
                deck_id = d.id
                break
        if deck_id is None:
            showInfo(f"Deck '{deck_name}' not found.")
            return

        # Get the models (note types) used in the selected deck
        note_ids = mw.col.find_notes(f'"deck:{deck_name}"')
        models_in_deck = set()
        for nid in note_ids:
            note = mw.col.getNote(nid)
            models_in_deck.add(note.model()['name'])

        if not models_in_deck:
            showInfo(f"No notes found in deck '{deck_name}'. Please add some notes first.")
            return
        elif len(models_in_deck) == 1:
            model_name = models_in_deck.pop()
        else:
            # Prompt the user to select a model if multiple are found
            model_name, ok = QInputDialog.getItem(
                mw, "Select Note Type", "Multiple note types found. Select one:", list(models_in_deck), 0, False
            )
            if not ok or not model_name:
                return

        # Get the model
        model = mw.col.models.byName(model_name)
        if not model:
            showInfo(f"Model '{model_name}' not found.")
            return

        # Get the fields of the model
        field_names = [fld['name'] for fld in model['flds']]
        if not field_names:
            showInfo(f"No fields found in model '{model_name}'.")
            return

        # Define the front field name (adjust if your model uses a different name)
        front_field_name = 'Front'  # Change this if your front field has a different name

        # Create a JSON format of the card type
        json_format = {field_name: "..." for field_name in field_names}
        json_format_str = json.dumps(json_format)

        # Fetch up to 5 sample cards from the deck
        sample_count = min(5, len(note_ids))
        if sample_count == 0:
            showInfo(f"No existing cards to sample in deck '{deck_name}'. Please add some notes first.")
            return
        sample_note_ids = random.sample(note_ids, sample_count)
        samples = []
        for nid in sample_note_ids:
            note = mw.col.getNote(nid)
            sample = {field: note.fields[idx] for idx, field in enumerate(field_names)}
            samples.append(sample)
        samples_json = json.dumps(samples, indent=2)

        # Adjusted prompt with more precise instructions
        prompt_template = (
            f"I will provide you with examples of flashcards from a deck. "
            f"Please generate a new flashcard on the topic of '{{topic}}' that matches the style and structure of the examples.\n\n"
            f"Here are the examples:\n{samples_json}\n\n"
            f"Now, generate a new flashcard in the same JSON format with the keys {list(field_names)}. "
            f"Ensure that the '{front_field_name}' field is unique and does not duplicate any existing '{front_field_name}' terms in the deck. "
            "Output only the JSON object, and do not include any extra text before or after it."
        )

        # Prompt the user for a topic
        topic, ok = QInputDialog.getText(
            mw, "Enter Topic", "Enter the topic for the flashcards:"
        )
        if not ok or not topic:
            return

        # Prompt the user for the number of cards to generate
        num_cards_str, ok = QInputDialog.getText(
            mw, "Number of Cards", "Enter the number of cards to generate (e.g., 5):"
        )
        if not ok or not num_cards_str:
            return
        try:
            num_cards = int(num_cards_str)
            if num_cards <= 0:
                raise ValueError
        except ValueError:
            showInfo("Please enter a valid positive integer for the number of cards.")
            return

        generated_cards = 0
        duplicate_cards = 0

        for i in range(num_cards):
            final_prompt = prompt_template.replace("{topic}", topic)

            try:
                # Make the API call to OpenAI
                headers = {
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                data = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an expert teacher."},
                        {"role": "user", "content": final_prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.7  # Use higher temperature for more variation
                }
                response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
                response.raise_for_status()

                # Extract the assistant's response
                content = response.json()['choices'][0]['message']['content'].strip()

                try:
                    # Parse the JSON output directly
                    flashcard = json.loads(content)
                except json.JSONDecodeError:
                    # Try to extract JSON from the assistant's response
                    flashcard = extract_json(content)
                    if flashcard is None:
                        showInfo(
                            f"The response was not valid JSON for card {i+1}. Skipping this card."
                            f"\n\nPrompt:\n{final_prompt}\n\nResponse:\n{content}"
                        )
                        continue

                # Ensure 'front' field exists
                if front_field_name not in flashcard:
                    showInfo(f"The generated card does not contain a '{front_field_name}' field. Skipping this card.")
                    continue

                # Check for duplicate 'front' term in the deck
                front_term = flashcard[front_field_name].strip()
                if not front_term:
                    showInfo(f"The '{front_field_name}' field of the generated card is empty. Skipping this card.")
                    continue

                # Search for existing cards with the same front term in the deck
                duplicate_note_ids = mw.col.find_notes(f'"deck:{deck_name}" "{front_field_name}:{front_term}"')
                if duplicate_note_ids:
                    duplicate_cards += 1
                    continue

                # Prepare the note
                note = Note(mw.col, model)
                for idx, field_name in enumerate(field_names):
                    note.fields[idx] = flashcard.get(field_name, "")

                # Set the deck for the note
                note.model()['did'] = deck_id

                # Set the flag to red (flag value 1)
                note.flags = 1

                # If preview is enabled, show the card before adding
                if config.get("PREVIEW_ENABLED", False):
                    preview_text = "\n".join([f"{fn}: {note.fields[idx]}" for idx, fn in enumerate(field_names)])
                    msg_box = QMessageBox()
                    msg_box.setWindowTitle(f"Preview Generated Card {i+1}")
                    msg_box.setText("Review the generated card before adding it:")
                    msg_box.setDetailedText(preview_text)
                    msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg_box.setDefaultButton(QMessageBox.Yes)
                    ret = msg_box.exec_()
                    if ret != QMessageBox.Yes:
                        showInfo(f"Card {i+1} addition canceled by user.")
                        continue

                # Add the note to the collection
                mw.col.addNote(note)
                generated_cards += 1

            except requests.exceptions.RequestException as e:
                showInfo(f"OpenAI API error on card {i+1}: {str(e)}\n\nPrompt:\n{final_prompt}\n\nResponse:\n{content}")
            except Exception as e:
                showInfo(f"An unexpected error occurred on card {i+1}: {str(e)}\n\nPrompt:\n{final_prompt}\n\nResponse:\n{content}")

        mw.col.reset()
        mw.reset()
        showInfo(f"Finished generating cards.\nGenerated: {generated_cards}\nDuplicates skipped: {duplicate_cards}")

    # Helper function to extract JSON from the assistant's response
    def extract_json(text):
        import json
        try:
            # Find the first occurrence of '{' and the last occurrence of '}'
            start = text.index('{')
            end = text.rindex('}') + 1
            json_str = text[start:end]
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            return None

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
    # Combine correct and incorrect answers for multiple choice
    all_answers = incorrect_answers + [correct_answer]
    # Shuffle the answers
    random.shuffle(all_answers)
    # Format the answers as options
    formatted_answers = "\n".join([f"{idx + 1}. {ans}" for idx, ans in enumerate(all_answers)])
    note.fields[1] = f"Correct Answer: {correct_answer}\nOptions:\n{formatted_answers}"  # Back

    # Set the flag to red (flag value 1)
    note.flags = 1

    # Add the note to the collection
    mw.col.addNote(note)
    mw.col.reset()
    mw.reset()
    showInfo("Added a new trivia card!")

def toggle_preview():
    # Toggle the preview setting
    current = config.get("PREVIEW_ENABLED", False)
    config["PREVIEW_ENABLED"] = not current
    save_config()
    status = "enabled" if config["PREVIEW_ENABLED"] else "disabled"
    showInfo(f"Preview feature has been {status}.")

def add_menu_items():
    # Generate Trivia Card Action
    trivia_action = QAction("Generate Trivia Card", mw)
    trivia_action.triggered.connect(generate_trivia_card)
    mw.form.menuTools.addAction(trivia_action)

    # Generate Card with OpenAI Action
    openai_action = QAction("Generate Card(s) with OpenAI", mw)
    openai_action.triggered.connect(generate_card_with_openai)
    mw.form.menuTools.addAction(openai_action)

    # Toggle Preview Feature Action
    preview_action = QAction("Toggle Preview Feature", mw)
    preview_action.setCheckable(True)
    preview_action.setChecked(config.get("PREVIEW_ENABLED", False))
    preview_action.triggered.connect(toggle_preview)
    mw.form.menuTools.addAction(preview_action)

add_menu_items()
