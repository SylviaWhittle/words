"""Script to help manually sort through nouns, verbs, adjectives etc."""

from typing import Literal
from datetime import datetime
import re
import random
from pathlib import Path
import nltk
from nltk.corpus import wordnet as wn


def get_definitions(word):
    """Get definitions of a word from WordNet."""
    synsets = wn.synsets(word)
    if not synsets:
        return "No definitions found."

    definitions = []
    for syn in synsets:
        pos = syn.pos()  # Part of speech (n = noun, v = verb, etc.)
        definition = syn.definition()
        definitions.append(f"[{pos}] {definition}")
    return definitions


def remove_word_from_file(word, file_path):
    """Remove a word from a file."""
    with open(file_path, "r") as f:
        words = [line.strip() for line in f.readlines()]
    if word in words:
        words.remove(word)
        with open(file_path, "w") as f:
            for w in words:
                f.write(w + "\n")


def accept_reject_words(unseen_words_file, accepted_words_file, rejected_words_file) -> None:
    """Iteratively ask the user to accept or reject words."""
    # iterate through unseen words
    while True:
        # get the first word from the unseen words file
        with open(unseen_words_file, "r") as unseen_file:
            unseen_words = [line.strip() for line in unseen_file.readlines()]
        if not unseen_words:
            print("No more unseen words to process.")
            return
        word = unseen_words[0]
        definitions = get_definitions(word)
        print(f"\nWord: {word}")
        if isinstance(definitions, list):
            for definition in definitions:
                print(definition)
        else:
            print(definitions)
        user_input = input("Accept this word? (y/n) (q to quit) ").strip().lower()
        if user_input == "y":
            # add the word to the accepted words file
            with open(accepted_words_file, "a") as accepted_file:
                accepted_file.write(word + "\n")
            # remove the word from the unseen words file
            remove_word_from_file(word, unseen_words_file)
            # continue to the next word
            continue
        elif user_input == "n":
            # add the word to the rejected words file
            with open(rejected_words_file, "a") as rejected_file:
                rejected_file.write(word + "\n")
            # remove the word from the unseen words file
            remove_word_from_file(word, unseen_words_file)
            # continue to the next word
            continue
        elif user_input == "q":
            print("Exiting accept/reject mode.")
            return
        else:
            print("Invalid input. Please enter 'y' or 'n' or 'q' to quit this mode.")


def exclude_words_by_pattern(unseen_words_file, rejected_words_file) -> None:
    """Exclude words from the unseen words file based on a regex pattern."""
    pattern = input("Enter the pattern to exclude (e.g., 'ing' to exclude words ending with 'ing'): ").strip()
    print(f"Excluding words containing the pattern '{pattern}' from {unseen_words_file}...")
    with open(unseen_words_file, "r") as unseen_file:
        unseen_words = [line.strip() for line in unseen_file.readlines()]
    # filter out words that contain the pattern by finding words that match the regex pattern
    excluded_words = [w for w in unseen_words if re.search(pattern, w)]
    num_excluded = len(excluded_words)
    print(f"Found {num_excluded} words containing the pattern '{pattern}'.")
    print("Random sample of 50 excluded words:")
    random_sample = random.sample(excluded_words, min(50, num_excluded))
    for word in random_sample:
        print(f"  {word}")
    print(f"Are you sure you want to exclude these {num_excluded} words? (y/n)")
    confirmation = input().strip().lower()
    if confirmation != "y":
        print("Exclusion cancelled.")
        return
    # write the excluded words to the rejected words file
    with open(rejected_words_file, "a") as rejected_file:
        for excluded_word in excluded_words:
            rejected_file.write(excluded_word + "\n")
    # write the remaining words back to the unseen words file
    remaining_words = [w for w in unseen_words if not re.search(pattern, w)]
    with open(unseen_words_file, "w") as unseen_file:
        for remaining_word in remaining_words:
            unseen_file.write(remaining_word + "\n")
    print(f"Excluded {num_excluded} words containing the pattern '{pattern}'.")
    print(f"Remaining words in {unseen_words_file}: {len(remaining_words)}")
    return


class WordSifter:
    """Class to handle sifting through word lists and saving words of interest."""

    def __init__(self, word_type: Literal["nouns", "adjectives", "verbs"], data_dir: Path, backup_dir: Path):
        self.word_type = word_type
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = data_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir = backup_dir

        self.file_unseen = data_dir / f"unseen_{word_type}.txt"
        self.file_accepted = data_dir / f"accepted_{word_type}.txt"
        self.file_rejected = data_dir / f"rejected_{word_type}.txt"

        self._ensure_files_exist()

    def _ensure_files_exist(self):
        if not self.file_unseen.exists():
            nltk.download("wordnet")
            word_type_map = {"nouns": "n", "verbs": "v", "adjectives": "a", "adverbs": "r"}
            words = set(
                lemma.name() for synset in wn.all_synsets(word_type_map[self.word_type]) for lemma in synset.lemmas()
            )
            self.file_unseen.write_text("\n".join(sorted(words)) + "\n")
            self.file_accepted.touch()
            self.file_rejected.touch()

    def get_current_word(self) -> tuple[str, list[str], dict[str, int]]:
        """Get the current word to process.

        It will be the first line of the unseen words file
        """
        # Read the first line without loading the entire file into memory
        print(f"Loading word from {self.file_unseen}")
        with self.file_unseen.open("r") as f:
            # Load the first line
            word = f.readline().strip()
        print(f"found word: [{word}]")
        assert word, "First line of unseen words file is empty."

        print(f"getting definitions for [{word}]")
        definitions = get_definitions(word)
        stats = self.get_stats()
        print(f"Returning word: [{word}], definitions: [{definitions}], stats: [{stats}]")
        return word, definitions, stats

    def get_stats(self) -> dict:
        """Get stats about the current state of the word lists."""
        number_unseen = len(self.file_unseen.read_text().splitlines())
        number_accepted = len(self.file_accepted.read_text().splitlines())
        number_rejected = len(self.file_rejected.read_text().splitlines())
        return {
            "number_unseen": number_unseen,
            "number_accepted": number_accepted,
            "number_rejected": number_rejected,
            "number_total": number_unseen + number_accepted + number_rejected,
            "percentage_completed": (
                round(
                    (number_accepted + number_rejected) / (number_unseen + number_accepted + number_rejected) * 100, 2
                )
                if (number_unseen + number_accepted + number_rejected) > 0
                else 0
            ),
        }

    def remove_word_from_file(self, word: str, file_path: Path) -> None:
        """Remove a word from a file."""
        with open(file_path, "r") as f:
            words = [line.strip() for line in f.readlines()]
        if word in words:
            words.remove(word)
            with open(file_path, "w") as f:
                for w in words:
                    f.write(w + "\n")

    def process_action(self, word: str, action: Literal["accept", "reject"]) -> None:
        """Process an action from a given word."""
        if action == "accept":
            with self.file_accepted.open("a") as f:
                f.write(word + "\n")
        elif action == "reject":
            with self.file_rejected.open("a") as f:
                f.write(word + "\n")
        else:
            raise ValueError(f"Invalid action: {action}")

        self.remove_word_from_file(word, self.file_unseen)

    def exclude_words_by_pattern(self, pattern: str) -> int:
        """Exclude words from the unseen words file based on a regex pattern."""
        unseen_words = self.file_unseen.read_text().splitlines()
        excluded_words = [w for w in unseen_words if re.search(pattern, w)]
        num_excluded = len(excluded_words)

        # Write the excluded words to the rejected words file
        with self.file_rejected.open("a") as f:
            for excluded_word in excluded_words:
                f.write(excluded_word + "\n")

        # Write the remaining words back to the unseen words file
        remaining_words = [w for w in unseen_words if not re.search(pattern, w)]
        self.file_unseen.write_text("\n".join(remaining_words) + "\n")

        return num_excluded

    def backup_state(self) -> Path:
        """Save a backup of the current state of the word lists."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_subdir = self.backup_dir / f"backup_{self.word_type}_{timestamp}"
        backup_subdir.mkdir(parents=True, exist_ok=True)

        for file in [self.file_unseen, self.file_accepted, self.file_rejected]:
            backup_file = backup_subdir / file.name
            with open(file, "r") as source_file:
                with open(backup_file, "w") as destination_file:
                    destination_file.write(source_file.read())

        return backup_subdir


def main():
    """Main function for sorting through word lists."""

    word_type = "adjectives"
    data_dir = Path("/Users/sylvi/src/words/data")
    backup_dir = Path("/Users/sylvi/src/words/backups")
    if not data_dir.exists():
        data_dir.mkdir()
    unseen_words_file = data_dir / f"unseen_{word_type}.txt"
    rejected_words_file = data_dir / f"rejected_{word_type}.txt"
    accepted_words_file = data_dir / f"accepted_{word_type}.txt"

    if not unseen_words_file.exists():
        print(f"No existing word list found, downloading {word_type} from WordNet...")
        nltk.download("wordnet")
        if word_type == "nouns":
            wordnet_word_type = "n"
        elif word_type == "verbs":
            wordnet_word_type = "v"
        elif word_type == "adjectives":
            wordnet_word_type = "a"
        elif word_type == "adverbs":
            wordnet_word_type = "r"
        else:
            raise ValueError(f"Unsupported word type: {word_type}")
        all_nouns = set(lemma.name() for synset in wn.all_synsets(wordnet_word_type) for lemma in synset.lemmas())
        print(len(all_nouns))
        # save the nouns to a file
        with open(unseen_words_file, "w") as f:
            for noun in sorted(all_nouns):
                f.write(noun + "\n")
        # create empty accepted and rejected files
        with open(accepted_words_file, "w") as f:
            pass
        with open(rejected_words_file, "w") as f:
            pass
    else:
        print("Files already exist, using existing data.")

    # iteratively read the unseen words file, get definitions, and ask the user to accept or reject each word
    print(f"Reading unseen words from {unseen_words_file}")
    with open(unseen_words_file, "r") as f:
        unseen_words = [line.strip() for line in f.readlines()]

    while True:
        num_unseen = len(unseen_words)
        with open(accepted_words_file, "r") as f:
            accepted_words = [line.strip() for line in f.readlines()]
        with open(rejected_words_file, "r") as f:
            rejected_words = [line.strip() for line in f.readlines()]
        num_accepted = len(accepted_words)
        num_rejected = len(rejected_words)
        percentage_completed = (num_accepted + num_rejected) / (num_unseen + num_accepted + num_rejected) * 100
        print(
            f"Number of {word_type} remaining: {num_unseen} / {num_unseen + num_accepted + num_rejected} (Accepted: {num_accepted}, Rejected: {num_rejected}) - {percentage_completed:.2f}% completed"
        )
        print("Select function:")
        print("1. Accept/Reject words")
        print("2. Exclude words by pattern")
        print("3. Exit")
        print("4. Save a backup of the state")
        choice = input("Enter your choice (1/2/3/4): ").strip()
        if choice == "1":
            accept_reject_words(unseen_words_file, accepted_words_file, rejected_words_file)
        elif choice == "2":
            exclude_words_by_pattern(unseen_words_file, rejected_words_file)
        elif choice == "3":
            print("Exiting the program.")
            exit(0)
        elif choice == "4":
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_subdir = backup_dir / f"backup_{word_type}_{timestamp}"
            backup_subdir.mkdir(parents=True, exist_ok=True)
            for file in [unseen_words_file, accepted_words_file, rejected_words_file]:
                backup_file = backup_subdir / file.name
                with open(file, "r") as source_file:
                    with open(backup_file, "w") as destination_file:
                        destination_file.write(source_file.read())
            print(f"Backup saved to {backup_subdir}")
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
