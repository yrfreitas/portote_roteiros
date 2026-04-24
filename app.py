import os
from flask import Flask, render_template
from database import init_db
from routes.fichas import fichas_bp
from routes.servicos import servicos_bp
from routes.cepcheck import cepcheck_bp

app = Flask(__name__)

app.register_blueprint(fichas_bp, url_prefix="/api")
app.register_blueprint(servicos_bp, url_prefix="/api")
app.register_blueprint(cepcheck_bp, url_prefix="/api")


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    init_db()
    print("\n" + "=" * 45)
    print("  Portotec — Sistema de Roteiros")
    print("  Acesse: http://localhost:5000")
    print("=" * 45 + "\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)