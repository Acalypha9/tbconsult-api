import httpx
from fastapi import APIRouter, HTTPException, Query
from app.core.config import settings

router = APIRouter()

@router.get("/route", summary="Get driving route between two points")
async def get_route(
    origin: str = Query(..., description="Latitude,Longitude of origin"),
    destination: str = Query(..., description="Latitude,Longitude of destination")
):
    origin = origin.strip().replace(" ", "")
    destination = destination.strip().replace(" ", "")
    
    if not settings.MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="Maps API Key not configured on the backend.")
        
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "key": settings.MAPS_API_KEY
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)
        
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error fetching directions from Google")
        
    data = response.json()
    if data.get("status") != "OK":
        error_msg = data.get("error_message", f"Directions API status: {data.get('status')}")
        raise HTTPException(status_code=400, detail=error_msg)
        
    return data
