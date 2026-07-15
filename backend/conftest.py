import os
import sys

# Cho phép `import app...` khi chạy pytest từ thư mục backend/
sys.path.insert(0, os.path.dirname(__file__))
