"""Webapp frontend for the words project."""

from pathlib import Path
from flask import Flask, render_template, request, jsonify
import argparse
from words import WordSifter


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

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the words webapp.")
    parser.add_argument(
        "--word_type", choices=["nouns", "adjectives", "verbs"], required=True, help="Type of words to filter."
    )
    parser.add_argument("--data_dir", type=str, required=True, help="Directory containing the word data files.")
    parser.add_argument("--backup_dir", type=str, required=True, help="Directory to store backup files.")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the webapp on.")

    args = parser.parse_args()

    # Validate
    dir_data = Path(args.data_dir)
    assert dir_data.exists() and dir_data.is_dir(), f"Data directory {dir_data} does not exist or is not a directory."
    dir_backup = Path(args.backup_dir)
    assert (
        dir_backup.exists() and dir_backup.is_dir()
    ), f"Backup directory {dir_backup} does not exist or is not a directory."

    sifter = WordSifter(word_type=args.word_type, data_dir=dir_data, backup_dir=dir_backup)

    app = create_application(sifter)
    app.run(host="0.0.0.0", port=args.port, debug=False)
