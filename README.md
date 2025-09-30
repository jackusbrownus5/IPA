# IPA Installer Backend for Render

## Deployment

1. Push this repository to GitHub.
2. Create a new web service on Render:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
3. Set `BASE_URL` environment variable to your Render public URL.
4. Open the frontend HTML and point upload URL to `https://<your-render-url>/upload`.
