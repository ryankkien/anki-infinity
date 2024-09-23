import sys
import os
import json
import requests
from aqt import mw
from aqt.qt import QAction, QInputDialog, QMessageBox
from aqt.utils import showInfo
from anki.notes import Note
import random
import logging

# Set up paths
addon_path = os.path.dirname(__file__)
lib_path = os.path.join(addon_path, "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

# Set up logging
log_file = os.path.join(addon_path, 'debug.log')
logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Function to get or set the OpenAI API key and other configurations
def get_config():
    config_file = os.path.join(addon_path, "config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                logging.debug("Loaded existing config: %s", config)
                return config
        except json.JSONDecodeError as e:
            logging.error("Failed to decode config.json: %s", str(e))
            showInfo(f"Failed to load config.json: {str(e)}")
            return {}
    else:
        config = {}
        # Prompt for OpenAI API Key
        api_key, ok = QInputDialog.getText(mw, "OpenAI API Key", "Enter your OpenAI API key:")
        if ok and api_key:
            config["OPENAI_API_KEY"] = api_key
            logging.debug("User entered OpenAI API key.")
        else:
            showInfo("OpenAI API key is required to use this add-on.")
            logging.warning("OpenAI API key not provided by user.")
            return {}
        # Set default for preview feature
        config["PREVIEW_ENABLED"] = False
        try:
            with open(config_file, "w") as f:
                json.dump(config, f, indent=4)
                logging.debug("Saved new config: %s", config)
        except Exception as e:
            logging.error("Failed to save config.json: %s", str(e))
            showInfo(f"Failed to save config.json: {str(e)}")
        return config

# Load configuration
config = get_config()

# Function to save configuration
def save_config():
    config_file = os.path.join(addon_path, "config.json")
    try:
        with open(config_file, "w") as f:
            json.dump(config, f, indent=4)
            logging.debug("Configuration saved: %s", config)
    except Exception as e:
        logging.error("Failed to save config.json: %s", str(e))
        showInfo(f"Failed to save config.json: {str(e)}")

# Get the OpenAI API key
OPENAI_API_KEY = config.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    showInfo(
        "OpenAI API key not found.\n"
        "Please enter a valid OpenAI API key when prompted."
    )
    def generate_card_with_openai():
        showInfo("OpenAI API key is not set. Cannot generate card.")
        logging.warning("Attempted to generate card without OpenAI API key.")
        return
else:
    def generate_card_with_openai():
        # Prompt the user to select a deck
        decks = mw.col.decks.all_names_and_ids()
        deck_names = [d.name for d in decks]
        if not deck_names:
            showInfo("No decks found. Please create a deck first.")
            logging.warning("No decks available for generating cards.")
            return
        deck_name, ok = QInputDialog.getItem(
            mw, "Select Deck", "Select the deck to add the card to:", deck_names, 0, False
        )
        if not ok or not deck_name:
            logging.info("User canceled deck selection.")
            return

        # Get the deck ID
        deck_id = None
        for d in decks:
            if d.name == deck_name:
                deck_id = d.id
                break
        if deck_id is None:
            showInfo(f"Deck '{deck_name}' not found.")
            logging.error(f"Deck '{deck_name}' not found after selection.")
            return

        # Get the models (note types) used in the selected deck
        note_ids = mw.col.find_notes(f'"deck:{deck_name}"')
        models_in_deck = set()
        for nid in note_ids:
            note = mw.col.getNote(nid)
            models_in_deck.add(note.model()['name'])

        if not models_in_deck:
            showInfo(f"No notes found in deck '{deck_name}'. Please add some notes first.")
            logging.warning(f"No notes found in deck '{deck_name}'.")
            return
        elif len(models_in_deck) == 1:
            model_name = models_in_deck.pop()
            logging.debug(f"Single model '{model_name}' found in deck '{deck_name}'.")
        else:
            # Prompt the user to select a model if multiple are found
            model_name, ok = QInputDialog.getItem(
                mw, "Select Note Type", "Multiple note types found. Select one:", list(models_in_deck), 0, False
            )
            if not ok or not model_name:
                logging.info("User canceled model selection.")
                return
            logging.debug(f"User selected model '{model_name}' for deck '{deck_name}'.")

        # Get the model
        model = mw.col.models.byName(model_name)
        if not model:
            showInfo(f"Model '{model_name}' not found.")
            logging.error(f"Model '{model_name}' not found.")
            return

        # Get the fields of the model
        field_names = [fld['name'] for fld in model['flds']]
        if not field_names:
            showInfo(f"No fields found in model '{model_name}'.")
            logging.error(f"No fields found in model '{model_name}'.")
            return

        # Create a JSON schema for the function
        properties = {}
        for field_name in field_names:
            properties[field_name] = {"type": "string"}

        function = {
            "name": "create_flashcard",
            "description": "Creates a flashcard with the given fields.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": field_names,
            },
        }

        # Fetch up to 5 sample cards from the deck
        sample_count = min(5, len(note_ids))
        if sample_count == 0:
            showInfo(f"No existing cards to sample in deck '{deck_name}'. Please add some notes first.")
            logging.warning(f"No sample notes available in deck '{deck_name}'.")
            return
        sample_note_ids = random.sample(note_ids, sample_count)
        samples = []
        for nid in sample_note_ids:
            note = mw.col.getNote(nid)
            sample = {field: note.fields[idx] for idx, field in enumerate(field_names)}
            samples.append(sample)
        logging.debug(f"Sampled {len(samples)} notes from deck '{deck_name}'.")

        # Prompt the user for a topic
        topic, ok = QInputDialog.getText(
            mw, "Enter Topic", "Enter the topic for the flashcard:"
        )
        if not ok or not topic:
            logging.info("User canceled topic input.")
            return
        logging.debug(f"User entered topic: {topic}")

        # Create the prompt for the OpenAI API
        prompt = (
            f"Generate a new flashcard on the topic of '{topic}' that matches the style and structure of the examples provided. "
            "Ensure that the front field is unique and does not duplicate any existing front terms in the deck."
        )

        # Final messages
        messages = [
            {"role": "system", "content": "You are an expert teacher helping to create flashcards."},
            {"role": "user", "content": prompt},
            {"role": "user", "content": f"Here are the examples:\n{json.dumps(samples, indent=2)}"},
        ]

        try:
            # Prepare headers and data
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o-mini",  # Use a model that supports function calling
                "messages": messages,
                "functions": [function],
                "function_call": {"name": "create_flashcard"},
                "max_tokens": 1000,
                "temperature": 0.7
            }

            # Log the request data
            logging.debug("Request JSON:\n%s", json.dumps(data, indent=2))

            # Make the API request
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data
            )
            response.raise_for_status()

            # Log the response data
            response_data = response.json()
            logging.debug("Response JSON:\n%s", json.dumps(response_data, indent=2))

            message = response_data['choices'][0]['message']

            if 'function_call' in message:
                arguments = message['function_call']['arguments']
                # Log the function arguments
                logging.debug("Function call arguments:\n%s", arguments)

                try:
                    flashcard = json.loads(arguments)
                    logging.debug("Parsed flashcard JSON: %s", flashcard)
                except json.JSONDecodeError as e:
                    # Log and show the error
                    logging.error("Failed to parse function arguments as JSON:\n%s\nError: %s", arguments, str(e))
                    showInfo(f"Failed to parse function arguments as JSON:\n{arguments}\nError: {str(e)}")
                    return
            else:
                showInfo("Failed to get function call from the assistant.")
                logging.error("No function_call found in the assistant's response.")
                return

            # Prepare the note
            note = Note(mw.col, model)
            for idx, field_name in enumerate(field_names):
                note.fields[idx] = flashcard.get(field_name, "")

            # Set the deck for the note
            note.model()['did'] = deck_id

            # Define the front field name (adjust if your model uses a different name)
            front_field_name = 'Front'  # Change this if your front field has a different name

            # Ensure 'front' field exists
            if front_field_name not in flashcard:
                showInfo(f"The generated card does not contain a '{front_field_name}' field. Please check the model's field names.")
                logging.error(f"'{front_field_name}' field missing in generated flashcard.")
                return

            # Check for duplicate 'front' term in the deck
            front_term = flashcard[front_field_name].strip()
            if not front_term:
                showInfo(f"The '{front_field_name}' field of the generated card is empty. Please generate a valid card.")
                logging.warning(f"Generated '{front_field_name}' field is empty.")
                return

            # Search for existing cards with the same front term in the deck
            duplicate_note_ids = mw.col.find_notes(f'deck:"{deck_name}" "{front_field_name}":"{front_term}"')
            if duplicate_note_ids:
                showInfo(f"A card with the {front_field_name} '{front_term}' already exists in the deck '{deck_name}'. The generated card will not be added to avoid duplication.")
                logging.info(f"Duplicate card with '{front_field_name}': '{front_term}' found in deck '{deck_name}'.")
                return

            # If preview is enabled, show the card before adding
            if config.get("PREVIEW_ENABLED", False):
                preview_text = "\n".join([f"{fn}: {note.fields[idx]}" for idx, fn in enumerate(field_names)])
                msg_box = QMessageBox()
                msg_box.setWindowTitle("Preview Generated Card")
                msg_box.setText("Review the generated card before adding it:")
                msg_box.setDetailedText(preview_text)
                msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg_box.setDefaultButton(QMessageBox.Yes)
                ret = msg_box.exec_()
                if ret != QMessageBox.Yes:
                    showInfo("Card addition canceled by user.")
                    logging.info("User canceled adding the generated card after preview.")
                    return

            # Add the note to the collection
            mw.col.addNote(note)
            mw.col.reset()
            mw.reset()
            showInfo(f"Added a new card from OpenAI with {front_field_name} '{front_term}'!")
            logging.info(f"Successfully added new card with '{front_field_name}': '{front_term}' to deck '{deck_name}'.")

        except json.JSONDecodeError:
            showInfo("The response was not valid JSON. Please check the examples and try again.")
            logging.error("Invalid JSON received from OpenAI API.")
        except requests.exceptions.RequestException as e:
            # Log and show request exceptions
            logging.error("OpenAI API request error: %s", str(e))
            if 'response' in locals() and response is not None:
                logging.error("Response content:\n%s", response.text)
                showInfo(f"OpenAI API error: {str(e)}\nResponse content:\n{response.text}")
            else:
                showInfo(f"OpenAI API error: {str(e)}")
        except Exception as e:
            # Log and show any other exceptions
            logging.exception("An unexpected error occurred")
            showInfo(f"An unexpected error occurred: {str(e)}")

def generate_trivia_card():
    try:
        # Fetch a trivia question from an API
        response = requests.get("https://opentdb.com/api.php?amount=1&type=multiple")
        if response.status_code != 200:
            showInfo("Failed to fetch trivia question.")
            logging.error(f"Failed to fetch trivia question. Status code: {response.status_code}")
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
            logging.error(f"Model '{model_name}' not found for trivia card.")
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

        # Add the note to the collection
        mw.col.addNote(note)
        mw.col.reset()
        mw.reset()
        showInfo("Added a new trivia card!")
        logging.info("Successfully added a new trivia card.")

    except requests.exceptions.RequestException as e:
        showInfo(f"Failed to fetch trivia question: {str(e)}")
        logging.error(f"RequestException while fetching trivia question: {str(e)}")
    except Exception as e:
        showInfo(f"An unexpected error occurred while adding trivia card: {str(e)}")
        logging.exception("Unexpected error in generate_trivia_card")

def toggle_preview():
    try:
        # Toggle the preview setting
        current = config.get("PREVIEW_ENABLED", False)
        config["PREVIEW_ENABLED"] = not current
        save_config()
        status = "enabled" if config["PREVIEW_ENABLED"] else "disabled"
        showInfo(f"Preview feature has been {status}.")
        logging.info(f"Preview feature toggled to {status}.")
    except Exception as e:
        showInfo(f"Failed to toggle preview feature: {str(e)}")
        logging.exception("Failed to toggle preview feature.")

def add_menu_items():
    try:
        # Generate Trivia Card Action
        trivia_action = QAction("Generate Trivia Card", mw)
        trivia_action.triggered.connect(generate_trivia_card)
        mw.form.menuTools.addAction(trivia_action)
        logging.debug("Added 'Generate Trivia Card' menu item.")

        # Generate Card with OpenAI Action
        openai_action = QAction("Generate Card with OpenAI", mw)
        openai_action.triggered.connect(generate_card_with_openai)
        mw.form.menuTools.addAction(openai_action)
        logging.debug("Added 'Generate Card with OpenAI' menu item.")

        # Toggle Preview Feature Action
        preview_action = QAction("Toggle Preview Feature", mw)
        preview_action.setCheckable(True)
        preview_action.setChecked(config.get("PREVIEW_ENABLED", False))
        preview_action.triggered.connect(toggle_preview)
        mw.form.menuTools.addAction(preview_action)
        logging.debug("Added 'Toggle Preview Feature' menu item.")
    except Exception as e:
        showInfo(f"Failed to add menu items: {str(e)}")
        logging.exception("Failed to add menu items.")

add_menu_items()
