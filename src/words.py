"""Script to help manually sort through nouns, verbs, adjectives etc."""

import random
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import nltk
from loguru import logger
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
        words = [line.strip() for line in f]
    if word in words:
        words.remove(word)
        with open(file_path, "w") as f:
            f.writelines(w + "\n" for w in words)


def accept_reject_words(
    unseen_words_file, accepted_words_file, rejected_words_file
) -> None:
    """Iteratively ask the user to accept or reject words."""
    # iterate through unseen words
    while True:
        # get the first word from the unseen words file
        with open(unseen_words_file, "r") as unseen_file:
            unseen_words = sorted([line.strip() for line in unseen_file], key=len)
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
    pattern = input(
        "Enter the pattern to exclude (e.g., 'ing' to exclude words ending with 'ing'): "
    ).strip()
    print(
        f"Excluding words containing the pattern '{pattern}' from {unseen_words_file}..."
    )
    with open(unseen_words_file, "r") as unseen_file:
        unseen_words = [line.strip() for line in unseen_file]
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
        rejected_file.writelines(
            excluded_word + "\n" for excluded_word in excluded_words
        )
    # write the remaining words back to the unseen words file
    remaining_words = [w for w in unseen_words if not re.search(pattern, w)]
    with open(unseen_words_file, "w") as unseen_file:
        unseen_file.writelines(
            remaining_word + "\n" for remaining_word in remaining_words
        )
    print(f"Excluded {num_excluded} words containing the pattern '{pattern}'.")
    print(f"Remaining words in {unseen_words_file}: {len(remaining_words)}")
    return


class WordSifter:
    """Class to handle sifting through word lists and saving words of interest."""

    def __init__(
        self,
        word_type: Literal["nouns", "adjectives", "verbs"],
        file_sort_type: Literal["alphabetical", "length"],
        data_dir: Path,
        backup_dir: Path,
    ):

        # Ensure nltk wordnet is downloaded - on nixos / devenv this needs checking each time
        print("Checking if nltk wordnet is present")
        try:
            nltk.data.find("corpora/wordnet")
        except LookupError:
            nltk.download("wordnet", quiet=True)
        self.word_type = word_type
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = data_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir = backup_dir

        self.file_unseen = data_dir / f"unseen_{word_type}.txt"
        self.file_accepted = data_dir / f"accepted_{word_type}.txt"
        self.file_rejected = data_dir / f"rejected_{word_type}.txt"
        self.history: list[tuple[str, Literal["accept", "reject"]]] = []
        self.file_sort_type: Literal["alphabetical", "length"] = file_sort_type

        print("WordSifter constructed, checking and sorting files.")

        self._ensure_files_exist()
        self.sort_unseen_file()

    def _ensure_files_exist(self):
        if not self.file_unseen.exists():
            nltk.download("wordnet")
            word_type_map = {
                "nouns": "n",
                "verbs": "v",
                "adjectives": "a",
                "adverbs": "r",
            }
            words = {
                lemma.name()
                for synset in wn.all_synsets(word_type_map[self.word_type])
                for lemma in synset.lemmas()
            }
            self.file_unseen.write_text("\n".join(sorted(words)) + "\n")
            self.file_accepted.touch()
            self.file_rejected.touch()

    def load_words_from_file(self) -> list[str]:
        """Load all the words from the file"""
        words = [
            line.strip()
            for line in self.file_unseen.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        logger.debug(f"loading words : got {len(words)} from file {self.file_unseen}")
        return words

    def sort_unseen_file(self) -> None:
        """Sort the current unseen words file."""

        # Load the words
        words = self.load_words_from_file()
        logger.debug(f"sorting : loaded {len(words)} from file.")
        if self.file_sort_type == "alphabetical":
            words = sorted(words)
        elif self.file_sort_type == "length":
            # use a tuple key so sorted twice, first on length then alphabetised
            words = sorted(words, key=lambda w: (len(w), w))
        else:
            raise ValueError(f"Bad sort type: {self.file_sort_type}")
        # Replace the file contents
        logger.debug(f"sorting : sorted words length: {len(words)}")
        self.write_words_to_file(words=words, file_path=self.file_unseen)
        with self.file_unseen.open(mode="r", encoding="utf-8") as f:
            lines = f.readlines()
            for i in range(3):
                line = lines[i]
                logger.debug(f"sorting : sorted, line {i}: {line}")

    def get_current_word(self) -> tuple[str, list[str], dict[str, int]]:
        """
        Get the current word to process.

        It will be the first line of the unseen words file
        """
        # Read the first line without loading the entire file into memory
        logger.debug(f"Loading word from {self.file_unseen}")
        words = self.load_words_from_file()
        word = words[0]
        logger.debug(f"found word: [{word}]")
        assert word, "First line of unseen words file is empty."

        print(f"getting definitions for [{word}]")
        definitions = get_definitions(word)
        stats = self.get_stats()
        logger.debug(
            f"Returning word: [{word}], definitions: [{definitions}], stats: [{stats}]"
        )
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
                    (number_accepted + number_rejected)
                    / (number_unseen + number_accepted + number_rejected)
                    * 100,
                    2,
                )
                if (number_unseen + number_accepted + number_rejected) > 0
                else 0
            ),
        }

    def remove_word_from_file(self, word: str, file_path: Path) -> None:
        """Remove a word from a file."""
        with open(file_path, "r") as f:
            words = [line.strip() for line in f]
        if word in words:
            words.remove(word)
            with open(file_path, "w") as f:
                f.writelines(w + "\n" for w in words)

    def add_word_to_file(self, word: str, file_path: Path) -> None:
        """Append a word to a file."""
        with file_path.open("a") as f:
            f.write(word + "\n")
        with file_path.open("r") as f:
            lines = f.readlines()
            logger.debug(f"last lines of file {file_path}")
            for i in range(3):
                line = lines[(len(lines) - 1) - i]
                logger.debug(f"\n{line}")

    def write_words_to_file(self, words: list[str], file_path: Path) -> None:
        """Overwrite a file with a word list"""
        contents = "\n".join(words) + ("\n" if words else "")
        file_path.write_text(contents, encoding="utf-8")

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

        self.history.append((word, action))

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
        timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H-%M-%S")
        backup_subdir = self.backup_dir / f"backup_{self.word_type}_{timestamp}"
        backup_subdir.mkdir(parents=True, exist_ok=True)

        for file in [self.file_unseen, self.file_accepted, self.file_rejected]:
            backup_file = backup_subdir / file.name
            with (
                file.open(mode="r", encoding="utf-8") as source_file,
                backup_file.open(mode="w", encoding="utf-8") as destination_file,
            ):
                destination_file.write(source_file.read())

        return backup_subdir

    def undo(self) -> str:
        """Undo the last decision from the history"""
        logger.debug(f"undo action invoked, history: {self.history}")
        if len(self.history) > 0:
            last_word, status = self.history.pop()
            if status == "accept":
                file_to_delete_from = self.file_accepted
            elif status == "reject":
                file_to_delete_from = self.file_rejected
            else:
                raise ValueError(
                    f"invalid accept state when trying to undo an action: {status}"
                )

            logger.debug(f"removing word from {file_to_delete_from}: {last_word}")
            self.remove_word_from_file(last_word, file_to_delete_from)
            logger.debug(f"adding word to {self.file_unseen}: {last_word}")
            self.add_word_to_file(last_word, self.file_unseen)
            logger.debug("undo: sorting unseen file")
            # Because we have edited the unseen file, we need to re-sort it
            self.sort_unseen_file()

            # Check that the undone word is in the unseen file

            lines = self.load_words_from_file()
            if last_word not in lines:
                logger.warning(
                    f"undo : last word [{last_word}] not in file [{self.file_unseen}]"
                )
                raise ValueError()

            return f"undid action [{status}] for word [{last_word}]"
        else:
            logger.debug("no history to undo")
            return "no history to undo"


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
        all_words = {
            lemma.name()
            for synset in wn.all_synsets(wordnet_word_type)
            for lemma in synset.lemmas()
        }
        print(len(all_words))
        # save the nouns to a file
        with open(unseen_words_file, "w") as f:
            f.writelines(word + "\n" for word in sorted(all_words))
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
        unseen_words = [line.strip() for line in f]

    while True:
        num_unseen = len(unseen_words)
        with open(accepted_words_file, "r") as f:
            accepted_words = [line.strip() for line in f]
        with open(rejected_words_file, "r") as f:
            rejected_words = [line.strip() for line in f]
        num_accepted = len(accepted_words)
        num_rejected = len(rejected_words)
        percentage_completed = (
            (num_accepted + num_rejected)
            / (num_unseen + num_accepted + num_rejected)
            * 100
        )
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
            accept_reject_words(
                unseen_words_file, accepted_words_file, rejected_words_file
            )
        elif choice == "2":
            exclude_words_by_pattern(unseen_words_file, rejected_words_file)
        elif choice == "3":
            print("Exiting the program.")
            sys.exit(0)
        elif choice == "4":
            timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%d_%H-%M-%S")
            backup_subdir = backup_dir / f"backup_{word_type}_{timestamp}"
            backup_subdir.mkdir(parents=True, exist_ok=True)
            for file in [unseen_words_file, accepted_words_file, rejected_words_file]:
                backup_file = backup_subdir / file.name
                with (
                    file.open(mode="r", encoding="utf-8") as source_file,
                    backup_file.open(mode="w", encoding="utf-8") as destination_file,
                ):
                    destination_file.write(source_file.read())
            print(f"Backup saved to {backup_subdir}")
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    main()
