Anki GPT-4 Flashcard Generator Add-on
An Anki add-on that utilizes OpenAI's GPT-4 API to generate flashcards based on user-specified topics, seamlessly integrating them into your existing Anki decks. This tool is designed to enhance your study sessions by creating personalized flashcards that match the style and structure of your current decks.

Features
Deck and Note Type Selection: Choose the specific deck and note type (model) where the new flashcards will be added.
Sample-Based Generation: The add-on fetches up to 5 sample cards from the selected deck to guide the AI in generating consistent and relevant flashcards.
Topic Specification: Input any topic, and the AI will generate flashcards related to that subject.
Customizable Quantity: Decide how many flashcards you want to generate in a single batch.
Duplicate Detection: Automatically checks for duplicates to prevent adding flashcards with the same front field.
Preview Feature: Optionally preview each generated flashcard before adding it to your deck.
Tagging and Flagging: Generated flashcards are flagged (red) and tagged with "AI-generated" for easy identification.
Error Logging: All errors are logged in a timestamped log file within the add-on's directory for troubleshooting.
Installation
Download the Add-on Files: Clone or download this repository to your computer.

bash
Copy code
git clone https://github.com/yourusername/anki-gpt4-flashcard-generator.git
Locate Anki's Add-ons Folder:

Open Anki.
Go to Tools > Add-ons > Open Add-ons Folder.
Copy the Add-on:

Place the downloaded add-on folder into the Add-ons directory.
Ensure the folder is named appropriately, e.g., gpt4_flashcard_generator.
Restart Anki:

Close and reopen Anki to load the new add-on.
Usage
Set Up OpenAI API Key:

Upon first use, the add-on will prompt you to enter your OpenAI API key.
Obtain your API key from OpenAI's website.
The key is stored securely in a config.json file within the add-on's directory.
Generate Flashcards:

In Anki, go to Tools > Generate Card(s).

Select a Deck:

Choose the deck where you want to add the new flashcards.
If no decks are available, you'll be prompted to create one first.
Select a Note Type:

If multiple note types are found in the deck, select the desired one.
The add-on uses this note type to structure the new flashcards.
Enter Topic:

Input the topic you want the flashcards to cover.
Specify Number of Cards:

Enter the number of flashcards you wish to generate.
Preview Cards (Optional):

If the preview feature is enabled, you'll have the option to review each card before it's added.
You can choose to accept or skip each card individually.
Review Generated Cards:

Generated cards are added to the selected deck.
They are flagged in red and tagged with "AI-generated" for easy identification.
Review them like any other flashcards during your study sessions.
Configuration
OpenAI API Key:

Stored in the config.json file.
To change the API key, edit this file or delete it to be prompted again.
Preview Feature:

Enabled by default.

To toggle the preview feature:

Go to Tools > Toggle Preview Feature.
A message will confirm the current status of the preview feature.
Config File:

Located in the add-on's directory as config.json.

Contains:

json
Copy code
{
  "OPENAI_API_KEY": "your-api-key",
  "PREVIEW_ENABLED": true
}
Troubleshooting
OpenAI API Errors:

Ensure your API key is correct and has sufficient quota.
Check your internet connection.
No Decks or Note Types Found:

Create at least one deck and add some notes to it before using the add-on.
Duplicate Cards Not Added:

The add-on skips cards with duplicate front fields to prevent redundancy.
Error Logs:

Error logs are saved in the logs folder within the add-on's directory.
Each log file is timestamped, e.g., error_log_20231005_123456.log.
Review these logs for detailed error information.
Contributing
Contributions are welcome! Please fork the repository and submit a pull request with your enhancements.

License
This project is licensed under the MIT License.

Disclaimer
This add-on is not affiliated with or endorsed by Anki or OpenAI. Use it responsibly and ensure compliance with OpenAI's Usage Policies when generating content.

Acknowledgments
Anki for the powerful spaced repetition platform.
OpenAI for providing the GPT-4 API.
