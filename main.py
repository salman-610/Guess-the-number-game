import os
import random

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session

from db import get_db_connection

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing. "
        "Create a .env file and add your secret key."
    )

MIN_NUMBER = 1
MAX_NUMBER = 99
MAX_ATTEMPTS = 8

HISTORY_LIMIT = 20
LEADERBOARD_LIMIT = 20


def close_database_resources(cursor=None, connection=None):
    """Close database resources safely."""

    if cursor is not None:
        try:
            cursor.close()
        except Exception:
            pass

    if connection is not None:
        try:
            connection.close()
        except Exception:
            pass


def get_game_history():
    """Return recent completed games."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return []

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, player_name, secret_number, attempts,
                   result, played_at
            FROM game_history
            ORDER BY played_at DESC, id DESC
            LIMIT %s
            """,
            (HISTORY_LIMIT,)
        )

        return cursor.fetchall()

    except Exception:
        app.logger.exception("Could not load game history.")
        return []

    finally:
        close_database_resources(cursor, connection)


def get_leaderboard():
    """Return players' best winning scores."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return []

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT player_name, best_attempts,
                   best_secret_number, updated_at
            FROM player_best_scores
            ORDER BY best_attempts ASC,
                     updated_at ASC,
                     player_name ASC
            LIMIT %s
            """,
            (LEADERBOARD_LIMIT,)
        )

        return cursor.fetchall()

    except Exception:
        app.logger.exception("Could not load leaderboard.")
        return []

    finally:
        close_database_resources(cursor, connection)


def get_player_statistics(player_name):
    """Return statistics for a selected leaderboard player."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return None

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                COUNT(*) AS games_played,
                COALESCE(
                    SUM(CASE WHEN result = 'Won' THEN 1 ELSE 0 END),
                    0
                ) AS wins,
                COALESCE(
                    SUM(CASE WHEN result = 'Failed' THEN 1 ELSE 0 END),
                    0
                ) AS failures
            FROM game_history
            WHERE player_name = %s
            """,
            (player_name,)
        )

        statistics = cursor.fetchone()

        cursor.execute(
            """
            SELECT best_attempts, best_secret_number
            FROM player_best_scores
            WHERE player_name = %s
            """,
            (player_name,)
        )

        best_score = cursor.fetchone()

        games_played = statistics["games_played"] if statistics else 0
        wins = statistics["wins"] if statistics else 0
        failures = statistics["failures"] if statistics else 0

        win_rate = (
            round(wins / games_played * 100, 1)
            if games_played
            else 0
        )

        return {
            "player_name": player_name,
            "games_played": games_played,
            "wins": wins,
            "failures": failures,
            "win_rate": win_rate,
            "best_attempts": (
                best_score["best_attempts"] if best_score else None
            ),
            "best_secret_number": (
                best_score["best_secret_number"] if best_score else None
            ),
        }

    except Exception:
        app.logger.exception("Could not load player statistics.")
        return None

    finally:
        close_database_resources(cursor, connection)


def save_game_result(player_name, secret_number, attempts, result):
    """Save a completed game and update a winning score."""

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        if connection is None:
            return False

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            INSERT INTO game_history
                (player_name, secret_number, attempts, result)
            VALUES (%s, %s, %s, %s)
            """,
            (player_name, secret_number, attempts, result)
        )

        if result == "Won":
            cursor.execute(
                """
                SELECT best_attempts
                FROM player_best_scores
                WHERE player_name = %s
                """,
                (player_name,)
            )

            existing_score = cursor.fetchone()

            if (
                existing_score is None
                or attempts < existing_score["best_attempts"]
            ):
                cursor.execute(
                    """
                    INSERT INTO player_best_scores
                        (player_name, best_attempts,
                         best_secret_number, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE
                        best_attempts = VALUES(best_attempts),
                        best_secret_number = VALUES(best_secret_number),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (player_name, attempts, secret_number)
                )

        connection.commit()
        return True

    except Exception:
        app.logger.exception("Could not save game result.")

        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass

        return False

    finally:
        close_database_resources(cursor, connection)


@app.route("/")
def index():
    """Display the game, leaderboard and game history."""

    leaderboard = get_leaderboard()
    history = get_game_history()

    selected_player = request.args.get("player", "").strip()
    player_stats = None

    if selected_player:
        leaderboard_names = {
            player["player_name"] for player in leaderboard
        }

        if selected_player in leaderboard_names:
            player_stats = get_player_statistics(selected_player)

    attempts = session.get("attempts", 0)

    return render_template(
        "index.html",
        player_name=session.get("player_name"),
        secret_number=session.get("secret_number"),
        attempts=attempts,
        attempts_left=max(0, MAX_ATTEMPTS - attempts),
        max_attempts=MAX_ATTEMPTS,
        min_number=MIN_NUMBER,
        max_number=MAX_NUMBER,
        game_started=session.get("game_started", False),
        game_over=session.get("game_over", False),
        result=session.get("result"),
        message=session.pop("message", None),
        message_type=session.pop("message_type", "info"),
        history=history,
        leaderboard=leaderboard,
        player_stats=player_stats,
        selected_player=selected_player,
        history_error=None,
        leaderboard_error=None,
    )


@app.route("/start", methods=["POST"])
def start_game():
    """Start a game for the entered player name."""

    player_name = request.form.get("player_name", "").strip()

    if not player_name:
        session["message"] = "Please enter your player name."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    if len(player_name) > 100:
        session["message"] = "Player name must be 100 characters or fewer."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    session.clear()

    session["player_name"] = player_name
    session["secret_number"] = random.randint(MIN_NUMBER, MAX_NUMBER)
    session["attempts"] = 0
    session["game_started"] = True
    session["game_over"] = False
    session["result"] = None
    session["message"] = f"Good luck, {player_name}! Guess the number."
    session["message_type"] = "success"

    return redirect(url_for("index"))


@app.route("/guess", methods=["POST"])
def guess():
    """Check the guess and update the current game."""

    if not session.get("game_started") or session.get("game_over"):
        session["message"] = "Please start a new game first."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    guess_value = request.form.get("guess", "").strip()

    try:
        guessed_number = int(guess_value)
    except (ValueError, TypeError):
        session["message"] = "Enter a valid whole number."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    if not MIN_NUMBER <= guessed_number <= MAX_NUMBER:
        session["message"] = (
            f"Your guess must be between {MIN_NUMBER} and {MAX_NUMBER}."
        )
        session["message_type"] = "error"
        return redirect(url_for("index"))

    secret_number = session.get("secret_number")
    attempts = session.get("attempts", 0)

    if (
        not isinstance(secret_number, int)
        or not isinstance(attempts, int)
        or not 0 <= attempts < MAX_ATTEMPTS
    ):
        session.clear()
        session["message"] = "Your game session expired. Please start again."
        session["message_type"] = "error"
        return redirect(url_for("index"))

    attempts += 1
    session["attempts"] = attempts

    if guessed_number == secret_number:
        session["game_over"] = True
        session["result"] = "Won"

        saved = save_game_result(
            session["player_name"],
            secret_number,
            attempts,
            "Won"
        )

        session["message"] = (
            f"Congratulations! You guessed the number in "
            f"{attempts} attempt(s)!"
        )

        if not saved:
            session["message"] += (
                " However, your result could not be saved to the database."
            )

        session["message_type"] = "success"

    elif attempts >= MAX_ATTEMPTS:
        session["game_over"] = True
        session["result"] = "Failed"

        saved = save_game_result(
            session["player_name"],
            secret_number,
            attempts,
            "Failed"
        )

        session["message"] = (
            f"Game over! The correct number was {secret_number}."
        )

        if not saved:
            session["message"] += (
                " Your result could not be saved to the database."
            )

        session["message_type"] = "error"

    elif guessed_number < secret_number:
        session["message"] = (
            f"Too low! Try a higher number. "
            f"You have {MAX_ATTEMPTS - attempts} attempt(s) left."
        )
        session["message_type"] = "info"

    else:
        session["message"] = (
            f"Too high! Try a lower number. "
            f"You have {MAX_ATTEMPTS - attempts} attempt(s) left."
        )
        session["message_type"] = "info"

    return redirect(url_for("index"))


@app.route("/new-game", methods=["GET", "POST"])
def new_game():
    """Clear the current game and return home."""

    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    debug_enabled = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_enabled)
