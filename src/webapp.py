"""Webapp frontend for the words project."""

import argparse
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from loguru import logger

from words import WordSifter


def set_up_logger() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
    )
    logger.add("logs/webapp.log", rotation="10 MB", retention="30 days", level="DEBUG")


def create_application(sifter: WordSifter) -> Flask:

    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/display_word", methods=["GET"])
    def display_word():
        word, definitions, stats = sifter.get_current_word()
        return jsonify({"word": word, "definitions": definitions, "stats": stats})

    @app.route("/api/decide_word", methods=["POST"])
    def handle_decision():
        decision = request.json
        sifter.process_action(decision["word"], decision["action"])
        return jsonify({"status": "success"})

    @app.route("/api/backup", methods=["POST"])
    def backup():
        sifter.backup_state()
        return jsonify({"success": True})

    @app.route("/api/undo", methods=["GET"])
    def undo():
        result_string = sifter.undo()
        return jsonify({"success": True, "result": result_string})

    return app


if __name__ == "__main__":
    set_up_logger()
    parser = argparse.ArgumentParser(description="Run the words webapp.")
    parser.add_argument(
        "--word_type",
        choices=["nouns", "adjectives", "verbs"],
        required=True,
        help="Type of words to filter.",
    )
    parser.add_argument(
        "--data_dir",
        type=str,
        required=True,
        help="Directory containing the word data files.",
    )
    parser.add_argument(
        "--backup_dir", type=str, required=True, help="Directory to store backup files."
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to run the webapp on."
    )
    parser.add_argument(
        "--file_sort_type",
        type=str,
        required=True,
        help="How to sort the words, [alphabetic], or [length]",
    )

    args = parser.parse_args()

    # Validate
    dir_data = Path(args.data_dir)
    assert dir_data.exists() and dir_data.is_dir(), (
        f"Data directory {dir_data} does not exist or is not a directory."
    )
    dir_backup = Path(args.backup_dir)
    assert dir_backup.exists() and dir_backup.is_dir(), (
        f"Backup directory {dir_backup} does not exist or is not a directory."
    )

    sifter = WordSifter(
        word_type=args.word_type,
        data_dir=dir_data,
        backup_dir=dir_backup,
        file_sort_type=args.file_sort_type,
    )

    app = create_application(sifter)
    app.run(host="0.0.0.0", port=args.port, debug=False)
