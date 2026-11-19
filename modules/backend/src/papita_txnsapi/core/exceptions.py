"""Domain-specific HTTP and service exceptions for the API layer.

Reserved for typed exception classes that map model-layer failures to consistent
HTTP responses. No concrete exceptions are defined yet; routers currently raise
``fastapi.HTTPException`` directly.
"""
