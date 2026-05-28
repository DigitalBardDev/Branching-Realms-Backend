import os
import json
import re
from tkinter import Tk, Label, Button, Entry, filedialog, StringVar, messagebox
from datetime import datetime
from pathlib import Path
import textstat
from better_profanity import profanity
import nltk
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
import threading
import string
import random

# Ensure local/offline access to NLTK data
nltk_data_path = os.path.join(os.path.dirname(__file__), "nltk_data")
if os.path.exists(nltk_data_path):
    nltk.data.path.append(nltk_data_path)

# Confirm the tokenizer can be loaded
try:
    from nltk.tokenize import sent_tokenize
    _ = sent_tokenize("Test sentence. Split me.")
except LookupError as e:
    print("Tokenizer not loading! Here's what went wrong:")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to exit.")
    raise

# Setup constants
LOG_PATH = "story_validation.log"

EMOTION_TAGS = {
    "violence": ["blood", "stab", "kill", "burn", "scream", "die", "wound", "slaughter", "assault", "agony", "mutilate", "strangle", "punch", "brutal", "massacre"],
    "supernatural": ["ghost", "ritual", "sigil", "curse", "glyph", "ward", "specter", "apparition", "enchantment", "hex", "phantom", "necromancy", "summon", "eldritch", "possession"],
    "fear": ["afraid", "terror", "shiver", "creep", "dread", "panic", "unease", "nightmare", "paranoia", "haunted", "menace", "foreboding", "tremble", "disturb", "chilling"],
    "death": ["corpse", "funeral", "grave", "mourning", "decay", "deceased", "expire", "cadaver", "remains", "deathly", "sepulcher", "gravestone", "tomb", "lament"]
}


def expand_keywords_with_synonyms(keywords):
    """Expands the keywords by adding their synonyms from WordNet."""
    expanded_keywords = set(keywords)
    for keyword in keywords:
        for syn in wordnet.synsets(keyword):
            for lemma in syn.lemmas():
                expanded_keywords.add(lemma.name().lower())
    return list(expanded_keywords)

def analyze_text(text, story_title, output_folder):
    words = word_tokenize(text.lower())
    total_words = len(words)
    total_sections = text.count('**')
    flesch = textstat.flesch_reading_ease(text)
    grade = textstat.flesch_kincaid_grade(text)
    contains_profanity = profanity.contains_profanity(text)

    emotion_hits = {key: 0 for key in EMOTION_TAGS}
    
    # Expand keywords with synonyms
    expanded_tags = {tag: expand_keywords_with_synonyms(keywords) for tag, keywords in EMOTION_TAGS.items()}

    # Count matches for expanded keywords
    for word in words:
        word = word.strip()
        for tag, expanded_keywords in expanded_tags.items():
            if word in expanded_keywords:
                emotion_hits[tag] += 1

    analysis_file = Path(output_folder) / f"{story_title.replace(' ', '_')}_analysis.txt"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        f.write(f"Story Analysis - {story_title}\n")
        f.write("=" * 40 + "\n\n")
        f.write("Reading Level\n-------------\n")
        f.write(f"Flesch Reading Ease: {flesch:.1f}\n")
        f.write(f"Flesch-Kincaid Grade Level: {grade:.1f}\n")
        age = "12+" if grade <= 8 else "14+" if grade <= 10 else "16+"
        f.write(f"Estimated Age: {age}\n\n")
        f.write(f"Profanity Detected: {'Yes' if contains_profanity else 'No'}\n\n")
        f.write("Content Tags Detected:\n")
        for tag, count in emotion_hits.items():
            if count > 0:
                f.write(f"  - {tag}: {count} matches\n")
        f.write(f"\nTotal Words: {total_words}\n")
        f.write(f"Estimated Sections: {total_sections}\n")

def validate_story_json(json_data, txt_word_counts, output_path):
    issues = []
    ids = set()
    reachable = set()
    id_to_words = {}

    for section in json_data["sections"]:
        sid = section["id"]
        ids.add(sid)
        original_prefix = sid.split("-")[0]
        id_to_words[original_prefix] = len(section["text"].split())

        for choice in section.get("choices", []):
            reachable.add(choice["nextSectionId"])
            if not choice["text"] or not choice["nextSectionId"]:
                issues.append(f"Empty choice text or target in section {sid}")

    # Compare word counts
    for sid, original_count in txt_word_counts.items():
        parsed_count = id_to_words.get(sid, 0)
        if abs(parsed_count - original_count) > 3:
            issues.append(f"Word count mismatch in section {sid}: TXT={original_count}, JSON={parsed_count}")

    # Detect unreachable
    entry_prefix = "001"
    unreachable = {s.split("-")[0] for s in ids} - {c.split("-")[0] for c in reachable} - {entry_prefix}
    if unreachable:
        issues.append(f"Unreachable sections: {', '.join(sorted(unreachable))}")

    # Detect broken references
    mapped_ids = {s["id"] for s in json_data["sections"]}
    for section in json_data["sections"]:
        for choice in section["choices"]:
            if choice["nextSectionId"] not in mapped_ids:
                issues.append(f"Choice in section {section['id']} points to unknown section ID: {choice['nextSectionId']}")

    # Write to validation log
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'w', encoding='utf-8') as _: pass  # ensure file exists

    with open(LOG_PATH, 'a', encoding='utf-8') as log:
        log.write(f"\n--- Validation Run: {datetime.now()} ---\n")
        log.write(f"File: {output_path}\n")
        if issues:
            log.write("Validation Issues:\n")
            for issue in issues:
                log.write(f"  - {issue}\n")
        else:
            log.write("Validation passed with no issues.\n")

def parse_story_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    title_match = re.search(r'^\+{3}(.*?)\+{3}', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Untitled"

    desc_match = re.search(r'<\+\+DESCRIPTION\+\+>(.*?)---', content, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else ""

    sections_raw = list(re.finditer(r'\+{2}(\d+)\+{2}\n(.*?)(?=\n---|\Z)', content, re.DOTALL))

    structured_sections = []
    txt_word_counts = {}

    for section in sections_raw:
        section_id = section.group(1).strip()
        padded_id = section_id.zfill(3)  # Pad to match ID mapping keys
        body = section.group(2).strip()
        lines = body.split('\n')
        content_lines = []
        choices = []

        for line in lines:
            choice_match = re.match(r'\*\s*(.*?):\s*go to\s*\+{2}(\d+)\+{2}', line.strip(), re.IGNORECASE)
            if choice_match:
                choices.append({
                    "text": choice_match.group(1).strip(),
                    "nextSectionId": choice_match.group(2).strip()
                })
            else:
                content_lines.append(line)

        section_text = '\n'.join(content_lines).strip()
        txt_word_counts[padded_id] = len(section_text.split())

        structured_sections.append({
            "id": section_id,
            "text": section_text,
            "choices": choices
        })

    return {
        "title": title,
        "description": description,
        "sections": structured_sections
    }, title, content, txt_word_counts

USED_IDS_FILE = "used_section_ids.txt"

def load_used_ids():
    if os.path.exists(USED_IDS_FILE):
        with open(USED_IDS_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_new_ids(new_ids):
    with open(USED_IDS_FILE, 'a', encoding='utf-8') as f:
        for new_id in new_ids:
            f.write(f"{new_id}\n")

def generate_unique_id(original_id, used_ids):
    padded = original_id.zfill(3)
    charset = string.ascii_uppercase + string.digits

    while True:
        suffix = ''.join(random.choices(charset, k=4))
        candidate = f"{padded}-{suffix}"
        if candidate not in used_ids:
            used_ids.add(candidate)
            return candidate

def convert_and_save_json(input_path, output_path):
    json_data, story_title, raw_text, txt_word_counts = parse_story_txt(input_path)
    folder = os.path.dirname(output_path)

    used_ids = load_used_ids()
    mapping = {}
    new_ids_used = set()

    # Step 1: Generate new ID mapping
    for section in json_data["sections"]:
        original_id = section["id"]
        padded = original_id.zfill(3)
        new_id = generate_unique_id(padded, used_ids)
        mapping[padded] = new_id
        new_ids_used.add(new_id)

    # Step 2: Apply mapping
    for section in json_data["sections"]:
        padded = section["id"].zfill(3)
        section["id"] = mapping[padded]
        for choice in section.get("choices", []):
            target = choice["nextSectionId"].zfill(3)
            if target in mapping:
                choice["nextSectionId"] = mapping[target]

    # Step 3: Save
    analyze_text(raw_text, story_title, folder)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # Step 4: Validate and record
    validate_story_json(json_data, txt_word_counts, output_path)
    save_new_ids(new_ids_used)

    # Step 5: Persist newly used IDs globally
    save_new_ids(new_ids_used)

def launch_gui():
    def select_file():
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            file_var.set(file_path)
            try:
                data, title, _, _ = parse_story_txt(file_path)
                title_var.set(title)
                default_output = os.path.splitext(os.path.basename(file_path))[0] + ".json"
                output_var.set(os.path.join(os.path.dirname(file_path), default_output))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to parse story: {e}")

    spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    spinner_index = [0]  # Mutable for closure
    spinner_running = [False]
    
    def start_spinner():
        spinner_running[0] = True
        animate_spinner()

    def animate_spinner():
        if spinner_running[0]:
            frame = spinner_frames[spinner_index[0] % len(spinner_frames)]
            status_var.set(f"Running analysis... {frame}")
            spinner_index[0] += 1
            root.after(100, animate_spinner)  # update every 100ms

    def stop_spinner(message="Done."):
        spinner_running[0] = False
        status_var.set(message)

    def run_conversion():
        def task():
            try:
                convert_and_save_json(input_path, output_path)
                stop_spinner("Analysis and conversion complete.")
                messagebox.showinfo("Success", f"Story converted and validated.\nJSON: {output_path}")
            except Exception as e:
                stop_spinner("Error during conversion.")
                messagebox.showerror("Error", f"Conversion failed: {e}")

        input_path = file_var.get()
        output_path = output_var.get()
        if not input_path or not output_path:
            messagebox.showwarning("Missing Info", "Please select a file and output path.")
            return

        start_spinner()
        threading.Thread(target=task, daemon=True).start()

    
    root = Tk()
    root.title("CYOA Story Converter")

    Label(root, text="Selected File:").grid(row=0, column=0, sticky='e')
    file_var = StringVar()
    Entry(root, textvariable=file_var, width=50).grid(row=0, column=1)
    Button(root, text="Browse", command=select_file).grid(row=0, column=2)

    Label(root, text="Detected Title:").grid(row=1, column=0, sticky='e')
    title_var = StringVar()
    Entry(root, textvariable=title_var, width=50).grid(row=1, column=1)

    Label(root, text="Output File:").grid(row=2, column=0, sticky='e')
    output_var = StringVar()
    Entry(root, textvariable=output_var, width=50).grid(row=2, column=1)

    Button(root, text="Convert to JSON", command=run_conversion).grid(row=3, column=1, pady=10)

    status_var = StringVar()
    status_label = Label(root, textvariable=status_var, fg="blue")
    status_label.grid(row=4, column=1, pady=5)

    root.mainloop()

# Run the GUI

if __name__ == "__main__":
    try:
        launch_gui()
    except Exception as e:
        import traceback
        print("An error occurred during execution:")
        traceback.print_exc()
        input("\nPress Enter to close...")
