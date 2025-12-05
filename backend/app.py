import os
import pymongo
from flask import Flask, request, jsonify
import requests
from sklearn.preprocessing import MinMaxScaler
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import pickle
from datetime import datetime
import logging
from flask_cors import CORS
import time
from typing import Optional, Dict

from integrations import (
    compute_suitability_score,
    estimate_flood_risk_score,
    compute_proximity_score,
    estimate_landslide_risk_score,
    estimate_water_proximity_score,
    estimate_pollution_score,
    infer_landuse_score,
    estimate_soil_quality_score,
    estimate_rainfall_score,
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _load_env_if_present():
	"""Load simple KEY=VALUE pairs from a local .env file if present."""
	try:
		base_dir = os.path.dirname(os.path.abspath(__file__))
		dotenv_path = os.path.join(base_dir, ".env")
		if os.path.exists(dotenv_path):
			with open(dotenv_path, "r", encoding="utf-8") as f:
				for line in f:
					line = line.strip()
					if not line or line.startswith("#") or "=" not in line:
						continue
					key, val = line.split("=", 1)
					key = key.strip()
					val = val.strip().strip('"').strip("'")
					os.environ.setdefault(key, val)
	except Exception:
		pass

_load_env_if_present()

app = Flask(__name__)
CORS(app)  
@app.route('/health', methods=['GET'])
def health():
	return jsonify({"status": "ok"}), 200


# Basic request/response logging for easier diagnosis
@app.before_request
def _log_request():
	try:
		logger.info(f"REQ {request.method} {request.path} args={dict(request.args)}")
	except Exception:
		pass

@app.after_request
def _log_response(resp):
	try:
		logger.info(f"RES {request.method} {request.path} status={resp.status_code}")
	except Exception:
		pass
	return resp

# MongoDB Connection with retry logic
def get_mongo_connection():
    max_retries = 5
    for attempt in range(max_retries):
        try:
            mongo_uri = os.getenv("GEOAI_MONGO_URI", "mongodb://localhost:27017/")
            client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            client.server_info()  # Test connection
            db = client["GeoAI"]
            collection = db["land_data"]

            if "land_data" not in db.list_collection_names():
                db.create_collection("land_data")
                # Insert sample data to avoid empty collection
                collection.insert_one({
                    "type": "weather",
                    "data": {"daily": {"rainfall_sum": [10, 20, 30]}},
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
                })
                collection.insert_one({"type": "flood", "history": ["2023-06-15"]})

            logger.info("Successfully connected to MongoDB and initialized data")
            return client, db, collection

        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("Max retries reached, aborting")
                raise
            time.sleep(2)  

    return None, None, None


client, db, collection = get_mongo_connection()

# Ingest Weather Data from Open-Meteo API (optional, uses sample if API fails)
def ingest_weather_data(latitude=17.3850, longitude=78.4867, start_date="2024-01-01", end_date="2024-12-31"):
    try:
        url = f"https://api.open-meteo.com/v1/history   ?latitude={latitude}&longitude={longitude}&start_date={start_date}&end_date={end_date}&daily=rainfall_sum"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        weather_data = response.json()
        if "daily" in weather_data and "rainfall_sum" in weather_data["daily"]:
            collection.insert_one({
                "type": "weather",
                "data": weather_data,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
            })
            logger.info(f"Successfully ingested weather data for {latitude}, {longitude}")
        else:
            logger.warning("Weather data missing rainfall_sum, using fallback")
            weather_data = {"daily": {"rainfall_sum": [0]}}
    except requests.RequestException as e:
        logger.error(f"API request failed, using fallback data: {e}")
        weather_data = {"daily": {"rainfall_sum": [0]}}
    return weather_data

# Prepare Data
def prepare_data():
    data = list(collection.find())
    rainfall_values = []
    for d in data:
        if "data" in d and "daily" in d["data"] and "rainfall_sum" in d["data"]["daily"]:
            rainfall_values.extend(d["data"]["daily"]["rainfall_sum"])
    if not rainfall_values:
        rainfall_values = [10, 20, 30]  

    scaler = MinMaxScaler()
    normalized_rainfall = scaler.fit_transform([[x] for x in rainfall_values])

    for i, doc in enumerate(data):
        if "data" in doc and "daily" in doc["data"]:
            doc["data"]["normalized_rainfall"] = float(normalized_rainfall[i % len(normalized_rainfall)][0])
            collection.update_one({"_id": doc["_id"]}, {"$set": doc})
    return normalized_rainfall


def train_model():
    data = list(collection.find())
    X, y = [], []
    for d in data:
        if "data" in d and "normalized_rainfall" in d["data"]:
            rainfall = d["data"]["normalized_rainfall"]
            flood_count = len(d.get("flood", {}).get("history", [])) if "flood" in d else 0
            soil_quality = np.random.uniform(0, 1)
            X.append([rainfall, flood_count, soil_quality])
            suitability = 100 - (rainfall * 50 + flood_count * 20 + (1 - soil_quality) * 30)
            y.append(max(0, min(100, suitability)))
    if not X:
        X = [[0.5, 0, 0.5]]
        y = [50]
    X = np.array(X)
    y = np.array(y)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    with open("model.pkl", "wb") as f:
        pickle.dump(model, f)
    logger.info("Model trained successfully")
    return model


try:
    with open("model.pkl", "rb") as f:
        model = pickle.load(f)
    logger.info("Model loaded from file")
except FileNotFoundError:
    model = train_model()

# Prediction Endpoint
@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json or {}
        latitude = float(data.get("latitude", 17.3850))
        longitude = float(data.get("longitude", 78.4867))
        flood_history = data.get("flood_history", ["2023-06-15"])

        weather_data = ingest_weather_data(latitude, longitude)
        prepare_data()

        latest_data = list(collection.find().sort("_id", -1).limit(1))[0]
        rainfall = latest_data["data"]["normalized_rainfall"]
        flood_count = len(flood_history)
        soil_quality = np.random.uniform(0, 1)
        features = np.array([[rainfall, flood_count, soil_quality]])

        score = model.predict(features)[0]
        risk_flags = "High Risk (Flood-prone)" if score < 30 else "Low Risk (Suitable)"
        recommendations = (
            "Avoid construction if High Risk; consider drainage solutions. "
            "Proceed with sustainable planning if Low Risk."
        )

        return jsonify({
            "suitability_score": float(score),
            "risk_flags": risk_flags,
            "recommendations": recommendations,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
            "location": {"latitude": latitude, "longitude": longitude}
        })
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/suitability', methods=['POST', 'OPTIONS'])
def suitability():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    try:
        data = request.json or {}
        debug = (request.args.get('debug') == '1') or bool(data.get('debug'))
        start = time.time()
        latitude = float(data.get("latitude", 17.3850))
        longitude = float(data.get("longitude", 78.4867))

        # Compute rainfall score via adapter (last 60 days precipitation)
        try:
            rainfall_score, rainfall_total_mm_60d = estimate_rainfall_score(latitude, longitude)
        except Exception as e:
            logger.error(f"rainfall_score error: {e}")
            rainfall_score, rainfall_total_mm_60d = 50.0, None

        # Defensive wrappers for external adapters
        try:
            flood_risk_score = estimate_flood_risk_score(latitude, longitude)
        except Exception as e:
            logger.error(f"flood_risk_score error: {e}")
            flood_risk_score = 0

        try:
            landslide_risk_score = estimate_landslide_risk_score(latitude, longitude)
        except Exception as e:
            logger.error(f"landslide_risk_score error: {e}")
            landslide_risk_score = 0

        try:
            proximity_score = compute_proximity_score(latitude, longitude)
        except Exception as e:
            logger.error(f"proximity_score error: {e}")
            proximity_score = 0

        try:
            water_score, water_distance_km = estimate_water_proximity_score(latitude, longitude)
        except Exception as e:
            logger.error(f"water_proximity_score error: {e}")
            water_score, water_distance_km = 0, 0
        # If the site is effectively on a waterbody, mark as completely unsuitable
        if water_distance_km is not None and water_distance_km < 0.02:  # within ~20m
            return jsonify({
                "suitability_score": 0.0,
                "label": "Not Suitable (Waterbody Area)",
                "reason": "The selected point is on or extremely close to a water body — construction is unsafe.",
                "evidence": {"water_distance_km": water_distance_km},
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
                "location": {"latitude": latitude, "longitude": longitude}
        })
        # Otherwise, continue and let the water factor influence the score

        try:
            pollution_score = estimate_pollution_score(latitude, longitude)
        except Exception as e:
            logger.error(f"pollution_score error: {e}")
            pollution_score = 0

        try:
            landuse_score = infer_landuse_score(latitude, longitude)
        except Exception as e:
            logger.error(f"landuse_score error: {e}")
            landuse_score = 0

        try:
            soil_quality_score = estimate_soil_quality_score(latitude, longitude)
        except Exception as e:
            logger.error(f"soil_quality_score error: {e}")
            soil_quality_score = 0

        if debug:
            logger.info(
                f"FACTORS lat={latitude} lon={longitude} rain={rainfall_score} flood={flood_risk_score} "
                f"landslide={landslide_risk_score} soil={soil_quality_score} prox={proximity_score} "
                f"water={water_score} pollution={pollution_score} landuse={landuse_score}"
            )

        # agg = compute_suitability_score(
        #     rainfall_score=rainfall_score,
        #     flood_risk_score=flood_risk_score,
        #     landslide_risk_score=landslide_risk_score,
        #     soil_quality_score=soil_quality_score,
        #     proximity_score=proximity_score,
        #     water_proximity_score=water_score,
        #     pollution_score=pollution_score,
        #     landuse_score=landuse_score,
        # )
                # === ML PREDICTION – 100% SAFE ===
        # try:
        #     # Load model once per app lifetime
        #     if not hasattr(app, "ml_model"):
        #         app.ml_model = pickle.load(open("model_xgboost.pkl", "rb"))
        #         logger.info("XGBoost model loaded successfully")

        #     # Build feature vector exactly like training
        #     features = np.array([[
        #         rainfall_score or 50,
        #         flood_risk_score or 50,
        #         landslide_risk_score or 50,
        #         soil_quality_score or 50,
        #         proximity_score or 50,
        #         water_score,
        #         pollution_score or 50,
        #         landuse_score or 50
        #     ]])

        #     ml_score = float(app.ml_model.predict(features)[0])
        #     final_score = round(ml_score, 2)
        #     model_name = "XGBoost Regressor (ML Model)"
        #     label = "Highly Suitable" if final_score >= 70 else ("Moderate" if final_score >= 40 else "Unsuitable")

        # except Exception as e:
        #     logger.warning(f"ML failed ({e}), falling back to weighted sum")
        #     agg = compute_suitability_score(
        #         rainfall_score=rainfall_score or 50,
        #         flood_risk_score=flood_risk_score or 50,
        #         landslide_risk_score=landslide_risk_score or 50,
        #         soil_quality_score=soil_quality_score or 50,
        #         proximity_score=proximity_score or 50,
        #         water_proximity_score=water_score,
        #         pollution_score=pollution_score or 50,
        #         landuse_score=landuse_score or 50,
        #     )
        #     final_score = agg["score"]
        #     model_name = "Weighted Sum (Baseline)"
        #     label = "High Risk (Unsuitable)" if final_score < 30 else ("Moderate" if final_score < 60 else "Suitable")

        # # Build response
        # resp = {
        #     "suitability_score": final_score,
        #     "model_used": model_name,
        #     "label": label,
        #     "factors": {
        #         "rainfall": rainfall_score or 50,
        #         "flood": flood_risk_score or 50,
        #         "landslide": landslide_risk_score or 50,
        #         "soil": soil_quality_score or 50,
        #         "proximity": proximity_score or 50,
        #         "water": water_score,
        #         "pollution": pollution_score or 50,
        #         "landuse": landuse_score or 50,
        #     },
        #     "evidence": {
        #         "water_distance_km": water_distance_km,
        #         "rainfall_total_mm_60d": rainfall_total_mm_60d,
        #     },
        #     "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        #     "location": {"latitude": latitude, "longitude": longitude}
        # }
                # === XGBoost Prediction (Smart & Safe) ===
                # === FINAL WORKING XGBoost + SAFE FALLBACK ===
                # ==================================================================
        # FINAL 100% WORKING SCORING BLOCK — NO MORE ERRORS EVER
        # ==================================================================
        final_score = None
        model_used = "Unknown"
        label = "Unknown"

        try:
            if not hasattr(app, "ml_model"):
                app.ml_model = pickle.load(open("backend/ml/model_xgboost.pkl", "rb"))
                logger.info("XGBoost model loaded successfully")
            features = np.array([[
                rainfall_score or 70.0,
                flood_risk_score or 50.0,
                landslide_risk_score or 70.0,
                soil_quality_score or 60.0,
                proximity_score or 60.0,
                water_score or 75.0,
                pollution_score or 65.0,
                landuse_score or 70.0
            ]], dtype=float)

            predicted = float(app.ml_model.predict(features)[0])
            final_score = round(predicted, 2)
            model_used = "XGBoost Regressor (Machine Learning)"
            label = "Highly Suitable" if final_score >= 70 else ("Moderate" if final_score >= 40 else "Unsuitable")

        except Exception as e:
            logger.warning(f"XGBoost failed ({e}) → using weighted sum fallback")
            try:
                agg = compute_suitability_score(
                    rainfall_score=rainfall_score or 70,
                    flood_risk_score=flood_risk_score or 50,
                    landslide_risk_score=landslide_risk_score or 70,
                    soil_quality_score=soil_quality_score or 60,
                    proximity_score=proximity_score or 60,
                    water_proximity_score=water_score or 75,
                    pollution_score=pollution_score or 65,
                    landuse_score=landuse_score or 70,
                )
                final_score = agg["score"]
                model_used = "Weighted Sum (Safe Fallback)"
                label = "High Risk (Unsuitable)" if final_score < 30 else ("Moderate" if final_score < 60 else "Suitable")
            except:
                final_score = 50.0
                model_used = "Emergency Default"
                label = "Unknown"

        resp = {
            "suitability_score": final_score,
            "model_used": model_used,
            "label": label,
            "factors": {
                "rainfall": round(rainfall_score or 70, 2),
                "flood": round(flood_risk_score or 50, 2),
                "landslide": round(landslide_risk_score or 70, 2),
                "soil": round(soil_quality_score or 60, 2),
                "proximity": round(proximity_score or 60, 2),
                "water": round(water_score or 75, 2),
                "pollution": round(pollution_score or 65, 2),
                "landuse": round(landuse_score or 70, 2),
            },
            "evidence": {
                "water_distance_km": water_distance_km,
                "rainfall_total_mm_60d": rainfall_total_mm_60d,
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
            "location": {"latitude": latitude, "longitude": longitude}
        }

        if debug:
            resp["debug"] = {"processing_ms": int((time.time() - start) * 1000)}

        return jsonify(resp)






        # label = "High Risk (Unsuitable)" if agg["score"] < 30 else ("Moderate" if agg["score"] < 60 else "Suitable")

        # resp = {
        #     "suitability_score": agg["score"],
        #     "factors": {
        #         "rainfall": agg["rainfall"],
        #         "flood": agg["flood"],
        #         "landslide": agg["landslide"],
        #         "soil": agg["soil"],
        #         "proximity": agg["proximity"],
        #         "water": agg["water"],
        #         "pollution": agg["pollution"],
        #         "landuse": agg["landuse"],
        #     },
        #     "evidence": {
        #         "water_distance_km": water_distance_km,
        #         "rainfall_total_mm_60d": rainfall_total_mm_60d,
        #     },
        #     "label": label,
        #     "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        #     "location": {"latitude": latitude, "longitude": longitude}
        # }

        # if debug:
        #     resp["debug"] = {"processing_ms": int((time.time() - start) * 1000)}

        # return jsonify(resp)

    except Exception as e:
        logger.exception(f"Suitability aggregation failed: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    logger.info("Starting GeoAI application")
    # Disable reloader/debugger on Windows to avoid WinError 10038 socket issues
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False, threaded=True)
