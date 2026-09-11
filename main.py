"""
Root ASGI application entrypoint.
Allows 'uvicorn main:app' to run from the repository root directory as well as from backend/.
"""
import os
import sys

# Ensure root directory is in sys.path
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
