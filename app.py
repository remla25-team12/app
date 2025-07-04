from flask import Flask, render_template, request, redirect, url_for, Response
import os
import requests
from lib_version.version_util import VersionUtil
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CollectorRegistry
import psutil
from flasgger import Swagger
import re 

# Set version from version.txt
try:
    with open("/app/version.txt") as f:
        full_version = f.read().strip()
        
        # Match pre-release first
        pre_match = re.match(r'^(\d+)\.(\d+)\.(\d+)-pre\.', full_version)
        if pre_match:
            major = int(pre_match.group(1))
            minor = int(pre_match.group(2))
            patch = int(pre_match.group(3))
            # Subtract 1 patch for stable version
            stable_patch = patch - 1 if patch > 0 else 0
            stable_version = f"{major}.{minor}.{stable_patch}"
            VersionUtil.set_version(stable_version)
        else:
            # Fallback: normal X.Y.Z
            match = re.match(r'^(\d+\.\d+\.\d+)', full_version)
            if match:
                VersionUtil.set_version(match.group(1))
            else:
                VersionUtil.set_version("dev")
except FileNotFoundError:
    VersionUtil.set_version("dev")
    
app = Flask(__name__)
swagger = Swagger(app)

MODEL_URL = os.getenv("MODEL_SERVICE_URL", "http://localhost:5001/predict")
NEW_DATA_URL = os.getenv("NEW_DATA_URL", "http://localhost:5001/new_data")
VERSION_URL = os.getenv("VERSION_URL", "http://localhost:5001/version")

registry = CollectorRegistry()

# Define the monitoring metrics
# Counter metrics
'''
total_reviews_submitted is labeled with app_version to keep track of the usage of the application per version.
'''
total_reviews_submitted = Counter('reviews_submitted', 'Total number of restaurant reviews submitted', ['app_version'], registry=registry)
total_correct_predictions = Counter('correct_predictions', 'Total number of correct restaurant sentiment predictions', registry=registry)
total_incorrect_predictions = Counter('incorrect_predictions', 'Total number of incorrect restaurant sentiment predictions', registry=registry)
# Add this at the top near other counters
profile_clicks = Counter(
    'profile_clicks', 
    'Number of clicks to each team member’s LinkedIn profile', 
    ['member_name','app_version'], 
    registry=registry
)

# Histogram metrics
'''
all_review_length_histogram is labeled with app version to see the distribution of all submitted review lengths per app version. 
review_length_per_feedback_histogram is labeled with prediction_outcome to see the distribution of review lengths for correct and incorrect predictions.
'''
all_review_length_histogram = Histogram('all_review_length_histogram', 'Distribution of all submitted restaurant review lengths (in characters)', ['app_version'], buckets=(50, 100, 200, 500, float('inf')), registry=registry)
review_length_per_feedback_histogram = Histogram('review_length_per_feedback_histogram', 'Distribution of restaurant review lengths for given feedback', ['prediction_outcome'], buckets=(50, 100, 200, 500, float('inf')), registry=registry)

# Gauge metrics
'''
current_percentage_of_correct_predictions_gauge is labeled with model_version. This allows us to keep track of the correct and incorrect predictions for each model version.
'''
current_percentage_of_correct_predictions_gauge = Gauge('current_percentage_of_correct_predictions_gauge', 'Current percentage of correct restaurant sentiment predictions', ['model_version'], registry=registry)
cpu_usage_percent_gauge = Gauge('cpu_usage_percent_gauge', 'Percentage of CPU usage', registry=registry)
memory_usage_percent_gauge = Gauge('memory_usage_percent_gauge', 'Percentage of memory usage', registry=registry)

def get_counter_value(counter):
    '''
    Method for extracting the value of a counter metric
    '''
    return list(counter.collect())[0].samples[0].value

def get_model_version():
    try:
        response = requests.get(VERSION_URL)  # replace with actual model version endpoint
        if response.status_code == 200:
            return response.json().get("version", "unknown")
        else:
            return "unavailable"
    except Exception:
        return "unavailable"
    
def get_process_metrics():
    try:
        process = psutil.Process(os.getpid())
        cpu_usage_percent_gauge.set(process.cpu_percent())

        memory_info = process.memory_info()
        total_memory = psutil.virtual_memory().total
        memory_percent = (memory_info.rss / total_memory) * 100
        memory_usage_percent_gauge.set(memory_percent)
    except Exception as e:
        print(f"Error getting process metrics: {e}")
    
@app.route("/")
def index():
    """
    Render the main page with app and model version
    ---
    summary: Render the main UI showing app and model version
    responses:
      200:
        description: Main HTML page with version info
    """
    app_version = VersionUtil.get_version()
    model_version = get_model_version()
    return render_template("index.html", app_version=app_version, model_version=model_version)

@app.route("/predict", methods=["POST"])
def predict():
    """
    Submit a restaurant review for sentiment prediction
    ---
    summary: Predict sentiment based on submitted review text
    consumes:
      - application/x-www-form-urlencoded
    parameters:
      - in: formData
        name: review
        type: string
        required: true
        description: The restaurant review text
    responses:
      200:
        description: HTML page rendered with sentiment prediction
      500:
        description: Model service is unreachable or errored
    """
    app_version = VersionUtil.get_version()
    review = request.form["review"]
    all_review_length_histogram.labels(app_version).observe(len(review)) # Observe the length of the submitted review for the histogram
    total_reviews_submitted.labels(app_version).inc() # Increment the total reviews submitted for the counter
    try:
        response = requests.post(MODEL_URL, json={"text": review})
        prediction = response.json().get("prediction", "Unknown")
    except Exception as e:
        prediction = f"Error contacting model service: {e}"
    return render_template("result.html", review=review, sentiment=prediction)

@app.route("/feedback", methods=["POST"])
def feedback():
    """
    Submit feedback on the predicted sentiment
    ---
    summary: Submit feedback indicating if the sentiment prediction was correct
    consumes:
      - application/x-www-form-urlencoded
    parameters:
      - in: formData
        name: review
        type: string
        required: true
        description: The original review text
      - in: formData
        name: predicted_sentiment
        type: string
        required: true
        description: The predicted sentiment (0 or 1)
      - in: formData
        name: feedback
        type: string
        required: true
        description: Feedback label ('correct' or 'incorrect')
    responses:
      200:
        description: HTML thank-you page after successful feedback
      400:
        description: Invalid predicted sentiment format
      500:
        description: Error when submitting feedback to the model service
    """
    model_version = get_model_version()
    review = request.form.get("review")
    predicted_sentiment = request.form.get("predicted_sentiment")
    feedback_value = request.form.get("feedback")  # "correct" or "incorrect"

    review_length_per_feedback_histogram.labels(feedback_value).observe(len(review))

    try:
        predicted_sentiment_int = int(predicted_sentiment)
        if predicted_sentiment_int not in [0, 1]:
            raise ValueError
    except ValueError:
        return "Invalid predicted sentiment value", 400

    corrected_sentiment = predicted_sentiment_int

    # Incorrect prediction
    if feedback_value == "incorrect":
        corrected_sentiment = 1 - predicted_sentiment_int  # flip 0<->1
        total_incorrect_predictions.inc()

    # Correct prediction
    else:
        total_correct_predictions.inc()

    total_predictions = get_counter_value(total_correct_predictions) + get_counter_value(total_incorrect_predictions)
    if total_predictions > 0:
        percentage_correct = (get_counter_value(total_correct_predictions) / total_predictions) * 100
        current_percentage_of_correct_predictions_gauge.labels(model_version).set(percentage_correct)
    else:
        current_percentage_of_correct_predictions_gauge.labels(model_version).set(0)

    try:
        response = requests.post(NEW_DATA_URL, json={
            "text": review,
            "sentiment": corrected_sentiment
        })
        response.raise_for_status()
    except Exception as e:
        return f"Failed to send feedback to model-service: {e}", 500

    return render_template("thanks.html")

@app.route('/metrics')
def metrics():
    """
    Expose application metrics for Prometheus
    ---
    summary: Expose Prometheus metrics for scraping
    responses:
      200:
        description: Prometheus metrics in plain text format
    """
    get_process_metrics()
    return Response(generate_latest(registry), mimetype='text/plain')


@app.route('/click/<member_name>')
def track_click(member_name):
    """
    Track LinkedIn profile click for a team member
    ---
    summary: Increment click count and redirect to member's LinkedIn profile
    parameters:
      - in: path
        name: member_name
        type: string
        required: true
        description: Lowercase name of the team member
    responses:
      302:
        description: Redirect to the LinkedIn profile
      404:
        description: Member not found
    """
    member_links = {
        "selin": "https://www.linkedin.com/in/selinceydeli/?originalSubdomain=nl",
        "mees": "https://www.linkedin.com/in/mees-c-169901291/",
        "philippe": "https://www.linkedin.com/in/philippe-henryy/?originalSubdomain=nl",
        "ayush": "https://www.linkedin.com/in/ayush-kuruvilla/?originalSubdomain=in",
        "peter": "https://www.linkedin.com/in/peter-huang-66a7451b6/",
    }
    app_version = VersionUtil.get_version()
    url = member_links.get(member_name.lower())
    if url:
        profile_clicks.labels(member_name.lower(), app_version).inc()
        return redirect(url)
    else:
        return "Unknown member", 404


@app.route("/people")
def people():
    """
    Render the team members page
    ---
    summary: Display the people/team page
    responses:
      200:
        description: HTML page rendered with team member links
    """
    return render_template("people.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000) 

