"""Legacy Streamlit entry point. Run from the repository root: `streamlit run app.py`.

The Streamlit UI lives in `streamlit_app/` and is being replaced by the React app in `web/`
backed by the FastAPI server in `api/`; the shared core lives in `geo_draw/`.
"""

from streamlit_app.app import main

main()
