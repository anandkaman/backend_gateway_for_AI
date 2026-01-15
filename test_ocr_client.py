#!/usr/bin/env python3
"""
DeepSeek-OCR Client Test
Tests OCR functionality with real images
"""

import requests
import base64
import sys
import json
from pathlib import Path

def test_ocr(image_path: str, description: str = ""):
    """Test OCR with an image"""
    print(f"\n{'='*60}")
    print(f"Testing: {description or image_path}")
    print(f"{'='*60}")
    
    # Check if image exists
    if not Path(image_path).exists():
        print(f"❌ Image not found: {image_path}")
        return False
    
    # Read and encode image
    print(f"📄 Reading image: {Path(image_path).name}")
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    image_size = Path(image_path).stat().st_size
    print(f"📊 Image size: {image_size:,} bytes")
    
    # Send OCR request
    print("🚀 Sending OCR request to DeepSeek-OCR...")
    
    try:
        response = requests.post(
            "http://localhost:8001/v1/chat/completions",
            json={
                "model": "deepseek-ai/DeepSeek-OCR",
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_data}"}
                        },
                        {"type": "text", "text": "Free OCR."}
                    ]
                }],
                "max_tokens": 2048,
                "temperature": 0.0
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            ocr_text = result['choices'][0]['message']['content']
            tokens_used = result['usage']['total_tokens']
            
            print(f"\n✅ OCR SUCCESS!")
            print(f"\n{'─'*60}")
            print("📝 Extracted Text:")
            print(f"{'─'*60}")
            
            # Show first 500 characters
            if len(ocr_text) > 500:
                print(ocr_text[:500])
                print(f"\n... (truncated, total length: {len(ocr_text)} characters)")
            else:
                print(ocr_text)
            
            print(f"{'─'*60}")
            print(f"📊 Tokens used: {tokens_used}")
            print(f"{'='*60}\n")
            
            return True
        else:
            print(f"\n❌ OCR failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out (>60s)")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    print("🤖 DeepSeek-OCR Client Test")
    print("="*60)
    
    # Check if DeepSeek-OCR is running
    print("\n1️⃣  Checking DeepSeek-OCR status...")
    try:
        health = requests.get("http://localhost:8001/health", timeout=5)
        if health.status_code == 200:
            print("✅ DeepSeek-OCR is running on port 8001")
        else:
            print(f"⚠️  Unexpected health status: {health.status_code}")
    except:
        print("❌ DeepSeek-OCR is not running!")
        print("   Start it with: cd /root/server_ai && source deepseek_ocr_env/bin/activate && vllm serve deepseek-ai/DeepSeek-OCR --port 8001")
        sys.exit(1)
    
    # Test images
    test_images = [
        {
            "path": "/root/.gemini/antigravity/brain/543289b4-50a8-49f3-81bf-254d6312db37/uploaded_image_1768480120475.png",
            "description": "Kannada Legal Document (Previous)"
        },
        {
            "path": "/root/.gemini/antigravity/brain/543289b4-50a8-49f3-81bf-254d6312db37/uploaded_image_1768498204034.png",
            "description": "New Uploaded Image"
        }
    ]
    
    results = []
    for img in test_images:
        if Path(img["path"]).exists():
            success = test_ocr(img["path"], img["description"])
            results.append({"image": img["description"], "success": success})
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{status} - {result['image']}")
    
    print("\n" + "="*60)
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    print(f"Results: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
