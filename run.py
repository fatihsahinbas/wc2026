from flask import redirect, url_for
from app import create_app

app = create_app()

@app.route("/")
def index():
    return redirect(url_for("matches.index"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)