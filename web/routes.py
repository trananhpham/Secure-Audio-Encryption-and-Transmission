import io
import json
import shutil
import uuid
import wave
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, send_file, send_from_directory

from src.config import Config
from src.exceptions import SecureAudioError
from web.services import TransferService
from web.web_utils import validate_and_save_upload

web_bp = Blueprint("web", __name__)


@web_bp.route("/")
def index():
    return render_template("index.html")


@web_bp.route("/transfer/<audio_id>")
def transfer(audio_id):
    return render_template("transfer.html", audio_id=audio_id)


@web_bp.route("/result/<audio_id>")
def result(audio_id):
    return render_template("result.html", audio_id=audio_id)


@web_bp.route("/hacker-result/<audio_id>")
def hacker_result(audio_id):
    return render_template("hacker_result.html", audio_id=audio_id)


@web_bp.route("/logs/<audio_id>")
def logs(audio_id):
    return render_template("logs.html", audio_id=audio_id)


@web_bp.route("/benchmark")
def benchmark():
    return render_template("benchmark.html")


@web_bp.route("/api/validate", methods=["POST"])
def api_validate():
    files = [request.files[f"file{i}"] for i in range(1, 6) if f"file{i}" in request.files]
    if len(files) != 5:
        return jsonify({"error": "Không có đủ 5 file được gửi lên."}), 400

    audio_id = str(uuid.uuid4())
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]) / audio_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    try:
        format_ext, _ = validate_and_save_upload(files, upload_dir)
        return jsonify({
            "message": "Kiểm tra thành công 5 đoạn âm thanh.",
            "format": format_ext,
            "audio_id": audio_id,
        })
    except SecureAudioError as e:
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
        return jsonify({"error": f"Lỗi không xác định: {str(e)}"}), 500


@web_bp.route("/api/send", methods=["POST"])
def api_send():
    data = request.json or {}
    audio_id = data.get("audio_id")
    format_ext = data.get("format")

    if not audio_id or not format_ext:
        return jsonify({"error": "Thiếu audio_id hoặc format."}), 400

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]) / audio_id
    if not upload_dir.exists():
        return jsonify({"error": "Thư mục upload không tồn tại hoặc đã bị xóa."}), 404

    TransferService.async_send(upload_dir, audio_id, format_ext, "alice", "bob")
    return jsonify({"message": "Bắt đầu mã hóa và gửi.", "audio_id": audio_id})


@web_bp.route("/api/transfer/<audio_id>/status", methods=["GET"])
def api_status(audio_id):
    return jsonify(TransferService.get_state(audio_id))


@web_bp.route("/api/transfer/<audio_id>/manifest", methods=["GET"])
def api_manifest(audio_id):
    manifest_path = Config.OUTPUT_DIR / "channel" / audio_id / "manifest.json"
    if not manifest_path.exists():
        return jsonify({"error": "Manifest không tồn tại."}), 404

    with open(manifest_path, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@web_bp.route("/api/transfer/<audio_id>/receive", methods=["POST"])
def api_receive(audio_id):
    channel_dir = Config.OUTPUT_DIR / "channel" / audio_id
    if not channel_dir.exists():
        return jsonify({"error": "Kênh truyền không tồn tại."}), 404

    TransferService.async_receive(audio_id)
    return jsonify({"message": "Bắt đầu giải mã và ghép nối.", "audio_id": audio_id})


@web_bp.route("/api/transfer/<audio_id>/logs", methods=["GET"])
def api_logs(audio_id):
    return jsonify({"logs": TransferService.get_logs(audio_id)})


@web_bp.route("/api/benchmark", methods=["POST"])
def api_benchmark():
    try:
        from src.benchmark import Benchmark

        mp3_dir = Path("sample_data/mp3")
        wav_dir = Path("sample_data/wav")
        if not mp3_dir.exists() or not wav_dir.exists():
            return jsonify({"error": "Thiếu dữ liệu mẫu để chạy benchmark."}), 400

        bench = Benchmark(mp3_dir, wav_dir, Config.OUTPUT_DIR, iterations=1)
        bench.run_all()

        bench_json = Config.OUTPUT_DIR / "benchmark" / "benchmark_results.json"
        if bench_json.exists():
            with open(bench_json, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))
        return jsonify({"error": "Không tìm thấy kết quả benchmark."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@web_bp.route("/download/audio/<audio_id>", methods=["GET"])
def download_audio(audio_id):
    state = TransferService.get_state(audio_id)
    filename = state.get("output_file")

    if not filename:
        for ext in ["mp3", "wav"]:
            path = Config.OUTPUT_DIR / "receiver" / f"reconstructed.{ext}"
            if path.exists():
                filename = path.name
                break

    if not filename:
        return "File not found", 404

    return send_from_directory(Config.OUTPUT_DIR / "receiver", filename, as_attachment=False)


@web_bp.route("/download/manifest/<audio_id>", methods=["GET"])
def download_manifest(audio_id):
    channel_dir = Config.OUTPUT_DIR / "channel" / audio_id
    if not (channel_dir / "manifest.json").exists():
        return "File not found", 404
    return send_from_directory(channel_dir, "manifest.json", as_attachment=True)


@web_bp.route("/health")
def health():
    return jsonify({"status": "ok"})


@web_bp.route("/api/transfer/<audio_id>/entropy", methods=["GET"])
def api_entropy(audio_id):
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"]) / audio_id
    channel_dir = Config.OUTPUT_DIR / "channel" / audio_id

    if not upload_dir.exists() or not channel_dir.exists():
        return jsonify({"error": "Dữ liệu không tồn tại."}), 404

    from src.crypto.hashing import Hashing

    pt_files = sorted([f for f in upload_dir.glob("*.*") if f.is_file()])
    if not pt_files:
        return jsonify({"error": "Không tìm thấy file gốc."}), 404

    with open(pt_files[0], "rb") as f:
        pt_entropy = Hashing.calculate_entropy(f.read())

    ct_files = sorted(channel_dir.glob("*_stego.wav"))
    if not ct_files:
        ct_files = sorted(channel_dir.glob("*.enc"))
    if not ct_files:
        return jsonify({"error": "Không tìm thấy file mã hóa."}), 404

    with open(ct_files[0], "rb") as f:
        ct_entropy = Hashing.calculate_entropy(f.read())

    return jsonify({
        "segment": pt_files[0].name,
        "plaintext_entropy": round(pt_entropy, 4),
        "ciphertext_entropy": round(ct_entropy, 4),
    })


@web_bp.route("/api/simulate/<action>", methods=["POST"])
def api_simulate(action):
    data = request.json or {}
    audio_id = data.get("audio_id")
    if not audio_id:
        return jsonify({"error": "Thiếu audio_id."}), 400

    channel_dir = Config.OUTPUT_DIR / "channel" / audio_id
    if not channel_dir.exists():
        return jsonify({"error": "Channel không tồn tại."}), 404

    from src.cli import simulate_duplicate, simulate_missing, simulate_reorder, simulate_replay, simulate_tampering

    try:
        if action == "missing":
            simulate_missing(channel_dir, segment=data.get("segment", "at3"))
        elif action == "tampering":
            simulate_tampering(channel_dir, segment=data.get("segment", "at2"))
        elif action == "reorder":
            simulate_reorder(channel_dir, order=data.get("order", "at1,at3,at2,at4,at5"))
        elif action == "duplicate":
            simulate_duplicate(channel_dir, segment=data.get("segment", "at3"))
        elif action == "replay":
            simulate_replay(channel_dir)
        else:
            return jsonify({"error": "Action không hợp lệ."}), 400

        return jsonify({"message": f"Mô phỏng {action} thành công."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@web_bp.route("/api/transfer/<audio_id>/hacker_file", methods=["GET"])
def get_hacker_file(audio_id):
    channel_dir = Config.OUTPUT_DIR / "channel" / audio_id
    if not channel_dir.exists():
        return "Channel not found", 404

    order_path = channel_dir / "received_order.json"
    if order_path.exists():
        with open(order_path, "r", encoding="utf-8") as f:
            order = json.load(f)
        enc_files = [channel_dir / name for name in order if (channel_dir / name).exists()]
    else:
        enc_files = sorted(channel_dir.glob("*_stego.wav"))
        if not enc_files:
            enc_files = sorted([f for f in channel_dir.glob("*.enc") if not f.name.endswith("noise.wav")])

    if not enc_files:
        return "File not found", 404

    if enc_files[0].name.endswith("_stego.wav"):
        return send_file(enc_files[0], as_attachment=False, mimetype="audio/wav", download_name="stolen_data.wav")

    encrypted_bytes = b""
    for enc_file in enc_files:
        with open(enc_file, "rb") as f:
            encrypted_bytes += f.read()

    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(1)
        wav_file.setframerate(16000)
        wav_file.writeframes(encrypted_bytes)

    wav_io.seek(0)
    return send_file(wav_io, as_attachment=False, mimetype="audio/wav", download_name="stolen_data.wav")
