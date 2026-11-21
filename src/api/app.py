"""Flask API 薄层：路由 -> src.api.PredictorService。"""
from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, jsonify, make_response, request
from flask_cors import CORS

from src.config import ROOT
from src.api.predictor import PredictorService, STRUCTURE_PARAM_MAP

app = Flask(__name__)
CORS(app)
service: PredictorService | None = None


def get_service() -> PredictorService:
    global service
    if service is None:
        service = PredictorService()
    return service


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(dict(status="healthy", initialized=service is not None))


@app.route("/api/structure-defaults", methods=["GET"])
def structure_defaults():
    s = get_service()
    labels = {
        "cubicity_b": "立方度偏差 b 轴", "cubicity_c": "立方度偏差 c 轴",
        "cubicity_alpha": "立方度偏差 α", "cubicity_beta": "立方度偏差 β",
        "cubicity_gamma": "立方度偏差 γ", "octahedral_factor": "八面体因子",
        "tolerance_factor": "容忍因子", "bartel_tolerance": "Bartel 容忍因子",
    }
    return jsonify(dict(fields=[
        dict(param=p, label=labels[p], column=c, default=float(s.defaults.get(c, 0.0)))
        for p, c in STRUCTURE_PARAM_MAP.items()],
        note="有 DFT 结构描述子时填入真值；留空用训练集均值（模型对此敏感，见 SHAP）"))


@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        return jsonify(get_service().predict_one(request.get_json() or {}))
    except Exception as e:
        return jsonify(dict(error=str(e))), 400


@app.route("/api/predict/batch", methods=["POST"])
def batch_predict():
    structs = (request.get_json() or {}).get("structures", [])
    if not structs:
        return jsonify(dict(error="No structures provided")), 400
    s = get_service()
    results = []
    for st in structs:
        try:
            results.append(s.predict_one(st))
        except Exception as e:
            results.append(dict(input=st, error=str(e)))
    return jsonify(dict(results=results, total=len(results),
                        success=sum(1 for r in results if "error" not in r)))


@app.route("/api/elements", methods=["GET"])
def elements():
    from src.data.preprocessor import A_SITES, B_SITES, HALOGENS
    return jsonify(dict(A_sites=A_SITES, B_sites=B_SITES, halogens=HALOGENS))


@app.route("/api/metrics", methods=["GET"])
def metrics():
    result: dict = dict(basis="HSErel_SOC = PBE + Δ-learning；口径见 docs/acceptance.md")
    p = ROOT / "experiments" / "results" / "v3_C1-delta-rf.json"
    result["offline_full"] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    return jsonify(result)


if __name__ == "__main__":
    get_service()
    app.run(host="0.0.0.0", port=5000, debug=True)
