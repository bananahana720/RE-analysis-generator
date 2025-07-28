"""Setup Ollama for LLM processing."""

import subprocess
import sys
import requests


def check_ollama_service():
    """Check if Ollama service is running."""
    try:
        response = requests.get("http://localhost:11434/api/version", timeout=5)
        if response.status_code == 200:
            print(f"[OK] Ollama service is running (version: {response.json()['version']})")
            return True
    except requests.exceptions.RequestException:
        pass
    
    print("[ERROR] Ollama service is not running")
    print("   Please run 'ollama serve' in a separate terminal")
    return False


def check_model_available(model_name="llama3.2:latest"):
    """Check if model is available."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            for model in models:
                if model_name in model.get("name", ""):
                    print(f"[OK] Model {model_name} is available")
                    return True
    except requests.exceptions.RequestException:
        pass
    
    print(f"[INFO] Model {model_name} not found")
    return False


def pull_model(model_name="llama3.2:latest"):
    """Pull model if not available."""
    if check_model_available(model_name):
        return True
    
    print(f"[DOWNLOAD] Pulling {model_name}... This may take several minutes.")
    try:
        # Use subprocess to show progress
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=False,  # Show output to user
            text=True
        )
        if result.returncode == 0:
            print(f"[OK] Successfully pulled {model_name}")
            return True
        else:
            print(f"[ERROR] Failed to pull {model_name}")
            return False
    except Exception as e:
        print(f"[ERROR] Error pulling model: {e}")
        return False


def main():
    """Main setup function."""
    print("Setting up Ollama for LLM processing\n")
    
    # Check service
    if not check_ollama_service():
        sys.exit(1)
    
    # Check/pull model
    if not pull_model("llama3.2:latest"):
        sys.exit(1)
    
    print("\n[SUCCESS] Ollama setup complete!")
    print("   - Service is running")
    print("   - llama3.2:latest model is available")
    print("\nNext steps:")
    print("   1. Keep 'ollama serve' running")
    print("   2. Run the LLM processing tests")


if __name__ == "__main__":
    main()