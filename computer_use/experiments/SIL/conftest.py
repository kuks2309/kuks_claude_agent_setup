import os
import sys

# 번들 루트(computer_use/)를 import 경로에 추가 → `import computer_action` 가능.
BUNDLE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BUNDLE_ROOT)
