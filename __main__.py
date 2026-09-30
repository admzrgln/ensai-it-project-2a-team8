from dotenv import load_dotenv
load_dotenv()  # Charge les variables du fichier .env

from backend.src.App.API import run_app

if __name__ == "__main__":
    app = run_app()
