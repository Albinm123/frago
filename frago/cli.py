import argparse
from frago import __version__

def main():
    parser = argparse.ArgumentParser(description="Frago CLI")
    parser.add_argument('--version', action='version', version=f"frago {__version__}")
    args = parser.parse_args()
