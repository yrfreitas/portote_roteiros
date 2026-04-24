import os
from flask import Flask, render_template
from flask_cors import CORS
from database import init_db
from routes.fichas import fichas_bp
from routes.servicos import servicos_bp
from routes.tecnicos import tecnicos_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(fichas_bp, url_prefix="/api")
app.register_blueprint(servicos_bp, url_prefix="/api")
app.register_blueprint(tecnicos_bp, url_prefix="/api")

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)