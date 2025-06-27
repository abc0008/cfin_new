from app.main import app
import json

print("All routes in the application:")
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"  {route.methods if hasattr(route, 'methods') else 'WS'} {route.path}")
        
print("\nWebSocket routes specifically:")
ws_routes = [r for r in app.routes if hasattr(r, 'endpoint') and hasattr(r.endpoint, '__name__') and 'websocket' in r.endpoint.__name__.lower()]
for route in ws_routes:
    print(f"  {route.path} -> {route.endpoint.__name__}")