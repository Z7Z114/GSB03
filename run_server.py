#!/usr/bin/env python3
"""
激光测振会议系统 - 服务端启动入口
"""

import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    print("="*70)
    print("LASER VIBROMETRY SPY SYSTEM - API SERVER")
    print("="*70)
    print(f"Server starting on http://{host}:{port}")
    print(f"API Documentation: http://{host}:{port}/docs")
    print(f"Alternative Docs: http://{host}:{port}/redoc")
    print("="*70)
    print()
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        workers=1
    )
