import time
from fastapi import Request

@app.middleware("http")
async def log_slow_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    if duration > 30:
        print(f"SLOW REQUEST {request.url.path}: {duration}s")
    return response
