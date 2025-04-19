# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
import os
import datetime

app = Flask(__name__)
CORS(app)

app.config['JWT_SECRET_KEY'] = 'super-secret-key-change-this'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)
jwt = JWTManager(app)

users = {}

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if username in users:
        return jsonify({"msg": "Username already exists"}), 409

    users[username] = password
    access_token = create_access_token(identity=username)
    return jsonify({
        "msg": "User registered successfully",
        "access_token": access_token
    }), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if username not in users or users[username] != password:
        return jsonify({"msg": "Bad username or password"}), 401

    token = create_access_token(identity=username)
    return jsonify(access_token=token), 200

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return "Welcome to MediVault Backend"

@app.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    current_user = get_jwt_identity()
    file = request.files['file']

    user_folder = os.path.join(UPLOAD_FOLDER, current_user)
    os.makedirs(user_folder, exist_ok=True)

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    cleanfilename = secure_filename(file.filename)
    filename = f"{current_user}_{cleanfilename}"
    filepath = os.path.join(user_folder, filename)
    file.save(filepath)
    size = os.path.getsize(filepath)
    upload_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify({
        'message': f"File uploaded by {current_user}",
        'filename': filename,
        'size': size,
        'upload_time': upload_time
    }), 201

@app.route('/files', methods=['GET'])
@jwt_required()
def list_files():
    current_user = get_jwt_identity()
    user_folder = os.path.join(UPLOAD_FOLDER, current_user)

    if not os.path.exists(user_folder):
        return jsonify({"files": []}), 200
    
    files = []
    for filename in os.listdir(user_folder):
        path = os.path.join(user_folder, filename)
        if os.path.isfile(path):
            if filename.startswith(current_user + "_"):
                size = os.path.getsize(path)
                upload_time = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
                files.append({
                    'name': filename.split('_', 1)[1],
                    'size': size,
                    'upload_time': upload_time
                })
    return jsonify(files), 200

@app.route('/download/<filename>', methods=['GET'])
@jwt_required()
def download_file(filename):
    current_user = get_jwt_identity()
    user_folder = os.path.join(UPLOAD_FOLDER, current_user)

    try:
        normalized_filename = filename.replace(' ', '_')
        return send_from_directory(user_folder, f"{current_user}_{normalized_filename}", as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

@app.route('/delete/<filename>', methods=['DELETE'])
@jwt_required()
def delete_file(filename):
    current_user = get_jwt_identity()
    user_folder = os.path.join(UPLOAD_FOLDER, current_user)
    
    try:
        normalized_filename = filename.replace(' ', '_')
        filepath = os.path.join(user_folder, f"{current_user}_{normalized_filename}")
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({'message': 'File deleted'}), 200
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/uploads/<filename>')
@jwt_required()
def uploaded_file(filename):
    current_user = get_jwt_identity()
    user_folder = os.path.join(UPLOAD_FOLDER, current_user)

    normalized_filename = filename.replace(' ', '_')
    return send_from_directory(user_folder, f"{current_user}_{normalized_filename}")

if __name__ == '__main__':
    app.run(debug=True)