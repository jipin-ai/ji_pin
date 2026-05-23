# AI Security Gateway - Playwright screenshot tool
# Usage: python screenshot.py [dev_server_url]

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

PAGES = [
    {"name": "login", "path": "/login", "desc": "登录页"},
    {"name": "dashboard", "path": "/dashboard", "desc": "仪表盘", "auth": True},
    {"name": "nodes", "path": "/nodes", "desc": "节点管理", "auth": True},
    {"name": "tasks", "path": "/tasks", "desc": "任务管理", "auth": True},
    {"name": "audit", "path": "/audit", "desc": "审计日志", "auth": True},
    {"name": "settings", "path": "/settings", "desc": "系统设置", "auth": True},
]

async def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
    screenshot_dir = Path(__file__).parent / "screenshots"
    screenshot_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        
        for page_conf in PAGES:
            page = await context.new_page()
            url = f"{base_url}{page_conf['path']}"
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=15000)
                
                if page_conf.get("auth"):
                    # Check if redirected to login
                    if "/login" in page.url:
                        print(f"  ⚠ {page_conf['name']}: redirected to login (auth required)")
                
                filename = f"{timestamp}_{page_conf['name']}.png"
                filepath = screenshot_dir / filename
                await page.screenshot(path=str(filepath), full_page=True)
                print(f"  ✓ {page_conf['name']}: {page_conf['desc']} → {filename}")
                
            except Exception as e:
                print(f"  ✗ {page_conf['name']}: {e}")
            finally:
                await page.close()
        
        await browser.close()
    
    print(f"\nScreenshots saved to {screenshot_dir}/")

if __name__ == "__main__":
    asyncio.run(main())
