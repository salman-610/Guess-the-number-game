Guess the Number Game

A fun number-guessing web game built using Python, Flask, HTML, CSS, and MySQL.

Features

- Guess a randomly generated number between 1 and 99.
- Get hints to help find the correct number.
- Maximum of 8 attempts per game.
- Save game results to a MySQL database.
- Track player statistics and personal best scores.
- View a leaderboard of top players.
- Review recent game history.
- Play again with a new game.

Technologies Used

- Python — application logic
- Flask — web framework
- MySQL — database
- HTML and CSS — user interface
- JavaScript — interactive elements

Project Structure


guess_the_number_game/
├── main.py
├── db.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   └── index.html
└── static/
    └── style.css


Setup Instructions

1. Clone the repository


git clone YOUR_GITHUB_REPOSITORY_URL
cd guess_the_number_game


2. Create and activate a virtual environment


python -m venv .venv


On Windows:


.venv\Scripts\activate


3. Install dependencies


python -m pip install -r requirements.txt


4. Configure environment variables

Create a `.env` file in the project root using `.env.example` as a template. Fill in your own MySQL credentials and Flask secret key. Do not upload `.env` to GitHub.

5. Configure MySQL

Create the database and required tables using your project's database schema. Make sure the database name matches the `DB_NAME` setting in `.env`.

6. Run the application


python main.py


Open the local URL shown in your terminal, usually `http://127.0.0.1:5000/`.

Security

Never upload database passwords, private secret keys, or your `.env` file to GitHub.

Author

Salman A
