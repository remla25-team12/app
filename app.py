from flask import Flask, render_template, request
import os
import requests

app = Flask(__name__)
MODEL_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:5001/predict")  # example fallback

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    review = request.form["review"]
    try:
        response = requests.post(MODEL_URL, json={"text": review})
        prediction = response.json().get("label", "Unknown")
    except Exception as e:
        prediction = f"Error contacting model service: {e}"
    return render_template("result.html", review=review, sentiment=prediction)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

