# Pure AI Backend Entrypoint
from server import app

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 5050))
    print("\n" + "="*65)
    print(">> CAMPUS-EYE // Multi-Modal AI Surveillance Backend")
    print(">> Face Recognition • ID Card • Haircut Length • Shoes Detection")
    print(f">> Server listening on: http://127.0.0.1:{port}")
    print("="*65 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
