import os

if "FILES_UPLOAD_PATH" in os.environ:
    FILES_UPLOAD_PATH = os.environ["FILES_UPLOAD_PATH"]
else:
    FILES_UPLOAD_PATH = "upload"