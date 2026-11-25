from dotenv import load_dotenv

# Load the .env variables BEFORE importing the API: the controllers read JWT_SECRET
# and OMDB_API_KEY as soon as they are imported.
load_dotenv()

from backend.src.Controller.API import run_app  # noqa: E402

if __name__ == "__main__":
    run_app()
