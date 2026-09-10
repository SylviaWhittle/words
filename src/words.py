"""Script to help manually sort through nouns, verbs, adjectives etc."""

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


def main():
    """Main function for sorting through word lists."""

    word_type = "nouns"
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
            backup_subdir = backup_dir / timestamp
            backup_subdir.mkdir(parents=True, exist_ok=True)
            for file in [unseen_words_file, accepted_words_file, rejected_words_file]:
                backup_file = backup_subdir / file.name
                with open(file, "r") as source_file:
                    with open(backup_file, "w") as destination_file:
                        destination_file.write(source_file.read())
            print(f"Backup saved to {backup_subdir}")
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
