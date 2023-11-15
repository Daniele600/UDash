import os
import jinja2

if "FILES_UPLOAD_PATH" in os.environ:
    FILES_UPLOAD_PATH = os.environ["FILES_UPLOAD_PATH"]
else:
    FILES_UPLOAD_PATH = "upload"

FILES_UPLOAD_ALLOWED_EXT = ("json")