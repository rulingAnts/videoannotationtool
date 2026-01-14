import os
import sys


def main():
    try:
        import webview
    except Exception:
        print("pywebview not installed. Please install 'pywebview'.")
        return
    # Accept a path or URL argument
    target = sys.argv[1] if len(sys.argv) > 1 else None
    frag = sys.argv[2] if len(sys.argv) > 2 else None
    if not target:
        target = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "index.html"))
    # Normalize to URL with support for anchor fragments
    if os.path.exists(target):
        # Ensure file URL format works across platforms
        url = "file://" + os.path.abspath(target)
        if frag:
            url = url + "#" + frag
    else:
        # If target is already a URL, optionally append fragment
        url = target + ("#" + frag if frag else "")
    title = "Getting Started"
    # Create window sized for comfortable reading
    window = webview.create_window(title, url=url, width=980, height=640, resizable=True)
    try:
        webview.start()
    except Exception:
        # As a fallback, try a smaller window or default start
        try:
            window = webview.create_window(title, url=url)
            webview.start()
        except Exception:
            print("Unable to start pywebview.")


if __name__ == "__main__":
    main()
