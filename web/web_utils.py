import os
from werkzeug.utils import secure_filename
from src.exceptions import SecureAudioError

ALLOWED_EXTENSIONS = {'mp3', 'wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_and_save_upload(files, upload_dir):
    """
    Validates uploaded files and saves them to upload_dir.
    Returns (format_ext, saved_paths)
    """
    if len(files) != 5:
        raise SecureAudioError("Vui lòng tải lên chính xác 5 đoạn âm thanh.")

    format_ext = None
    saved_paths = []

    # Check mapping
    for i in range(1, 6):
        expected_name = f"at{i}"
        file_obj = files[i-1]

        if not allowed_file(file_obj.filename):
            raise SecureAudioError(f"Định dạng không được hỗ trợ cho {file_obj.filename}")

        ext = file_obj.filename.rsplit('.', 1)[1].lower()
        if format_ext is None:
            format_ext = ext
        elif ext != format_ext:
            raise SecureAudioError("Không cho phép trộn file MP3 và WAV.")

        filename = secure_filename(file_obj.filename)
        # Force format atX.ext to prevent any weird traversal or renaming
        filename = f"{expected_name}.{ext}"
        filepath = os.path.join(upload_dir, filename)
        file_obj.save(filepath)
        saved_paths.append(filepath)

    return format_ext, saved_paths
