from flask import Flask, render_template, request, redirect, url_for
import os
import requests
from lib_version.version_util import VersionUtil

app = Flask(__name__)
MODEL_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:5001/predict")
NEW_DATA_URL = os.getenv("NEW_DATA_URL", "http://localhost:5001/new_data")
VERSION_URL = os.getenv("VERSION_URL", "http://localhost:5001/version")

def get_model_version():
    try:
        response = requests.get(VERSION_URL)  # replace with actual model version endpoint
        if response.status_code == 200:
            return response.json().get("version", "unknown")
        else:
            return "unavailable"
    except Exception:
        return "unavailable"
    
@app.route("/")
def index():
    app_version = VersionUtil.get_version()
    model_version = get_model_version()
    return render_template("index.html", app_version=app_version, model_version=model_version)

@app.route("/predict", methods=["POST"])
def predict():
    review = request.form["review"]
    try:
        response = requests.post(MODEL_URL, json={"text": review})
        prediction = response.json().get("prediction", "Unknown")
    except Exception as e:
        prediction = f"Error contacting model service: {e}"
    return render_template("result.html", review=review, sentiment=prediction)

@app.route("/feedback", methods=["POST"])
def feedback():
    review = request.form.get("review")
    predicted_sentiment = request.form.get("predicted_sentiment")
    feedback_value = request.form.get("feedback")  # "correct" or "incorrect"

    try:
        predicted_sentiment_int = int(predicted_sentiment)
        if predicted_sentiment_int not in [0, 1]:
            raise ValueError
    except ValueError:
        return "Invalid predicted sentiment value", 400

    corrected_sentiment = predicted_sentiment_int
    if feedback_value == "incorrect":
        corrected_sentiment = 1 - predicted_sentiment_int  # flip 0<->1


    try:
        response = requests.post(NEW_DATA_URL, json={
            "text": review,
            "sentiment": corrected_sentiment
        })
        response.raise_for_status()
    except Exception as e:
        return f"Failed to send feedback to model-service: {e}", 500

    return render_template("thanks.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

