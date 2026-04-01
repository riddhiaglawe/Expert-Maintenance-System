from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import datetime
import io
import random

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

app = Flask(__name__, template_folder='Templates', static_folder='Static')
app.secret_key = "secretkey"


# -----------------------
# DATABASE SETUP
# -----------------------

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        temperature INTEGER,
        vibration TEXT,
        oil TEXT,
        battery TEXT,
        noise TEXT,
        result TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()


# -----------------------
# EXPERT SYSTEM
# -----------------------

def maintenance_expert_system(data):

    temperature = int(data["temperature"])
    vibration = data["vibration"]
    oil = data["oil"]
    battery = data["battery"]
    noise = data["noise"]

    suggestions = []
    reasoning = []
    states = []

    states.append("Initial Motor State")

    # Temperature rule
    if temperature > 85:
        reasoning.append(f"Rule: IF Temperature > 85 → TRUE ({temperature})")
        states.append("Temperature > 85")
    else:
        reasoning.append(f"Rule: IF Temperature > 85 → FALSE ({temperature})")
        states.append("Temperature Normal")

    # Oil rule
    if oil == "Low":
        suggestions.append("🛢 Refill Lubrication Immediately")
        reasoning.append("Rule: IF Oil Level = Low → TRUE")
        states.append("Oil Level Low")
    else:
        reasoning.append("Rule: IF Oil Level = Low → FALSE")
        states.append("Oil Level Normal")

    # Battery rule
    if battery == "Low":
        suggestions.append("🔋 Replace Battery")
        reasoning.append("Rule: IF Battery Status = Low → TRUE")
        states.append("Battery Low")
    else:
        reasoning.append("Rule: IF Battery Status = Low → FALSE")
        states.append("Battery Normal")

    # Vibration + Noise rule
    if vibration == "High" and noise == "High":
        suggestions.append("🔧 Shaft Misalignment Suspected")
        reasoning.append("Rule: IF Vibration = High AND Noise = High → TRUE")
        states.append("High Vibration + Noise")

    else:
        reasoning.append("Rule: IF Vibration = High AND Noise = High → FALSE")

    # Bearing wear rule
    if temperature > 85 and vibration == "High":
        suggestions.append("⚠ Bearing Wear Suspected")
        states.append("Bearing Wear Detected")

    # Critical overheating
    if temperature > 90:
        suggestions.append("🔥 Critical Overheating! Shut Down Motor")
        states.append("Critical Overheating State")

    if not suggestions:
        suggestions.append("✅ Motor Operating Normally")
        states.append("Normal Operating State")
        reasoning.append("All conditions normal")

    return suggestions, reasoning, states


# -----------------------
# LOGIN PAGE
# -----------------------

@app.route("/", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "1234":
            session["user"] = username
            return redirect("/dashboard")

        else:
            return render_template("login.html", error="Invalid Credentials")

    return render_template("login.html")


# -----------------------
# DASHBOARD
# -----------------------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    return render_template("dashboard.html")


# -----------------------
# LOGOUT
# -----------------------

@app.route("/logout")
def logout():

    session.pop("user",None)
    return redirect("/")


# -----------------------
# MOTOR CHECK
# -----------------------

@app.route("/check", methods=["GET","POST"])
def check():

    if "user" not in session:
        return redirect("/")

    result = None
    reasoning = []
    states = []
    formdata = {}

    if request.method == "POST":

        formdata = request.form
        result, reasoning, states = maintenance_expert_system(formdata)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("""
        INSERT INTO logs(temperature,vibration,oil,battery,noise,result,timestamp)
        VALUES(?,?,?,?,?,?,?)
        """,(
            formdata["temperature"],
            formdata["vibration"],
            formdata["oil"],
            formdata["battery"],
            formdata["noise"],
            ", ".join(result),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

    return render_template(
        "index.html",
        result=result,
        reasoning=reasoning,
        states=states,
        formdata=formdata
    )


# -----------------------
# SENSOR SIMULATION
# -----------------------

@app.route("/simulate")
def simulate():

    data = {
        "temperature": random.randint(60,100),
        "vibration": random.choice(["Low","Medium","High"]),
        "oil": random.choice(["Normal","Low"]),
        "battery": random.choice(["Normal","Low"]),
        "noise": random.choice(["Low","High"])
    }

    return render_template("simulate.html", data=data)


# -----------------------
# PDF REPORT
# -----------------------

@app.route("/download")
def download():

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 1")
    record = c.fetchone()

    conn.close()

    if not record:
        return "No report available."

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer,pagesize=letter)
    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("Industrial Motor Maintenance Report",styles["Heading1"]))
    elements.append(Spacer(1,20))

    elements.append(Paragraph(f"Temperature: {record[1]} °C",styles["Normal"]))
    elements.append(Paragraph(f"Vibration: {record[2]}",styles["Normal"]))
    elements.append(Paragraph(f"Oil Level: {record[3]}",styles["Normal"]))
    elements.append(Paragraph(f"Battery Status: {record[4]}",styles["Normal"]))
    elements.append(Paragraph(f"Noise Level: {record[5]}",styles["Normal"]))

    elements.append(Spacer(1,20))
    elements.append(Paragraph("Maintenance Suggestions:",styles["Heading2"]))
    elements.append(Paragraph(record[6],styles["Normal"]))

    doc.build(elements)

    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="Motor_Report.pdf")


# -----------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)