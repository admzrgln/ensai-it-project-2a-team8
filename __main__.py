from dotenv import load_dotenv
load_dotenv()  # Charge les variables du fichier .env

from backend.src.Controller.API import run_app

if __name__ == "__main__":
    run_app()
