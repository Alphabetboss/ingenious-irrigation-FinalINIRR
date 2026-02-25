from flask import Blueprint, render_template, request, jsonify
from garden_utils import analyze_zone

tech_bp = Blueprint("tech", __name__)

@tech_bp.get("/tech")
def tech_page():
    return render_template("tech.html")

@tech_bp.post("/tech/diagnose")
def diagnose_zone():
    data = request.get_json()
    zone_id = data.get("zone_id")
    result = analyze_zone(zone_id)
    return jsonify(result)

@tech_bp.post("/tech/avatar-trigger")
def trigger_avatar():
    action = request.get_json().get("action")

    # Simulated response — wire this to your animation logic
    response = {
        "action": action,
        "status": "triggered",
        "message": f"Avatar will now perform: {action}"
    }

    return jsonify(response)
