from flask import Flask, render_template, request, redirect, url_for
import os
from PIL import Image
from datetime import datetime
import ffmpeg
import logging

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
NO_DATE_FOLDER = 'uploads/no_date'
IMAGES_FOLDER = 'uploads/images'
VIDEOS_FOLDER = 'uploads/videos'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['NO_DATE_FOLDER'] = NO_DATE_FOLDER
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
app.config['VIDEOS_FOLDER'] = VIDEOS_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'heif', 'hevc'}

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[
    logging.FileHandler("uploads.log"),  # 将日志记录到 uploads.log 文件
    logging.StreamHandler()  # 同时输出到控制台
])

# 检查文件类型
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_image_date(image_path):
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                if tag == 36867:
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S').date()
    except Exception as e:
        print(f"Error reading image EXIF: {e}")
    return None

def get_video_date(video_path):
    try:
        probe = ffmpeg.probe(video_path, v='error', select_streams='v:0', show_entries='stream=tags')
        if 'tags' in probe['streams'][0]:
            creation_time = probe['streams'][0]['tags'].get('creation_time')
            if creation_time:
                return datetime.fromisoformat(creation_time).date()
    except Exception as e:
        print(f"Error reading video metadata: {e}")
    return None

def get_file_date(file_path):
    if file_path.lower().endswith(('jpg', 'jpeg', 'png', 'gif', 'heif')):
        return get_image_date(file_path)
    elif file_path.lower().endswith(('mp4', 'avi', 'mov', 'hevc')):
        return get_video_date(file_path)
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist('file')
    if not files:
        return 'No file part'

    uploaded_files = []
    user_ip = request.remote_addr  # 获取用户的 IP 地址

    for file in files:
        if file.filename == '':
            continue

        if file and allowed_file(file.filename):
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # 创建目标文件夹（如果不存在的话）
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            file.save(file_path)

            capture_date = get_file_date(file_path)

            if capture_date:
                date_folder = capture_date.strftime('%Y-%m-%d')
            else:
                date_folder = 'no_date'

            if filename.lower().endswith(('jpg', 'jpeg', 'png', 'gif', 'heif')):
                category_folder = os.path.join(app.config['IMAGES_FOLDER'], date_folder)
            elif filename.lower().endswith(('mp4', 'avi', 'mov', 'hevc')):
                category_folder = os.path.join(app.config['VIDEOS_FOLDER'], date_folder)
            else:
                continue

            # 创建目标分类文件夹（如果不存在的话）
            os.makedirs(category_folder, exist_ok=True)

            new_file_path = os.path.join(category_folder, filename)
            os.rename(file_path, new_file_path)
            uploaded_files.append(filename)

            # 记录上传文件的 IP 地址
            logging.info(f"User IP: {user_ip}, Uploaded File: {filename}")

    if uploaded_files:
        # 上传成功，带上一个成功标识
        return redirect(url_for('index', upload_success='true'))
    else:
        return 'No valid files uploaded'

if __name__ == '__main__':
    for folder in [UPLOAD_FOLDER, NO_DATE_FOLDER, IMAGES_FOLDER, VIDEOS_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    app.run(debug=True, host='0.0.0.0', port=5000)
