import os

TEMP_FILE_DIR = "temp"
FACE_DETECTIONS_RESULTS_DIR = "face-detections"
AWS_DEFAULT_REGION = 'us-east-1'
AWS_ACCESS_KEY_ID = 'abc'
AWS_SECRET_ACCESS_KEY = 'iiFkbDhZ2bMwr2ikJy/QVAE7dckrn/gD5P6n3JTp'
APP_ROOT = os.path.dirname(os.path.abspath(__file__)) 
EMBEDDDING_ROOT = os.path.join('application', 'controllers', 'bot', 'static')
EMBEDDED_DB_FOLDER = os.path.join(APP_ROOT, EMBEDDDING_ROOT, 'embeddings')
EMBEDDING_PDF_FOLDER = os.path.join(APP_ROOT, EMBEDDDING_ROOT, 'pdfs')
