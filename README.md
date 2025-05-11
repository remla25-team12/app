# App Repository

A Flask web application that allows users to submit restaurant reviews, receive sentiment predictions, and optionally provide feedback to improve the underlying model.

## Overview

The application provides three main routes:

- `/` — Submit a review and view the model version.
- `/predict` — Get sentiment prediction for submitted text.
- `/feedback` — Submit corrected sentiment if prediction is incorrect.

It communicates with a separate model service via HTTP.

## Project Structure

<pre>
app/
├── static/css/           # CSS stylesheets
│   ├── index.css
│   ├── result.css
│   └── thanks.css
├── templates/            # HTML templates
│   ├── index.html
│   ├── result.html
│   └── thanks.html
├── app.py                # Flask application entry point
├── Dockerfile            # Docker build configuration
├── requirements.txt      # Python dependencies
├── pyproject.toml        # App version metadata
</pre>

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

Clone the repository and install dependencies:

```bash
git clone <repo-url>
cd app
pip install -r requirements.txt
```
Then Run the Flask app:
```
python app.py

Visit http://localhost:5000 in your browser.
```

## Usage
### Environment Variables

The application supports the following environment variables:

    MODEL_SERVICE_URL – URL of the prediction endpoint (default: http://localhost:5001/predict)

    NEW_DATA_URL – URL to submit feedback (default: http://localhost:5001/new_data)

    VERSION_URL – URL to retrieve model version (default: http://localhost:5001/version)

These can be set via a .env file or through Docker configuration.
## Run with Docker

To build and run the app using Docker:

```
docker build -t sentiment-app .
docker run -p 8080:5000 sentiment-app
```

Then access the app at: http://localhost:8080