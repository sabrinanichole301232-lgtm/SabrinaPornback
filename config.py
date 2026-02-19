import os

class Config:
    SECRET_KEY = 'sabrinaporn-secret-key-2024'
    ADMIN_PASSWORD = 'kennyray'
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}