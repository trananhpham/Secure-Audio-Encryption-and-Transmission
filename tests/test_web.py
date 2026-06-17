import pytest
from app import create_app
import io

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    # Giới hạn kích thước nhỏ gọn cho test
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024
    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Secure Audio Transfer" in response.data

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {"status": "ok"}

def test_validate_missing_files(client):
    response = client.post('/api/validate', data={})
    assert response.status_code == 400

def test_validate_invalid_extensions(client):
    data = {
        'file1': (io.BytesIO(b"fake audio data"), 'at1.txt'),
        'file2': (io.BytesIO(b"fake audio data"), 'at2.mp3'),
        'file3': (io.BytesIO(b"fake audio data"), 'at3.mp3'),
        'file4': (io.BytesIO(b"fake audio data"), 'at4.mp3'),
        'file5': (io.BytesIO(b"fake audio data"), 'at5.mp3')
    }
    response = client.post('/api/validate', data=data, content_type='multipart/form-data')
    assert response.status_code == 400

def test_validate_success(client):
    # Tạo 5 file giả
    data = {
        'file1': (io.BytesIO(b"data1"), 'anyname1.mp3'),
        'file2': (io.BytesIO(b"data2"), 'anyname2.mp3'),
        'file3': (io.BytesIO(b"data3"), 'anyname3.mp3'),
        'file4': (io.BytesIO(b"data4"), 'anyname4.mp3'),
        'file5': (io.BytesIO(b"data5"), 'anyname5.mp3')
    }
    response = client.post('/api/validate', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    assert "audio_id" in response.json
    assert response.json["format"] == "mp3"

def test_api_send_missing_data(client):
    response = client.post('/api/send', json={})
    assert response.status_code == 400
    assert "audio_id" in response.json["error"]

def test_api_status_not_found(client):
    response = client.get('/api/transfer/invalid_id/status')
    assert response.status_code == 200
    assert response.json["status"] == "pending"
