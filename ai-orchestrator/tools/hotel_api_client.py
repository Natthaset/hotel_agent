import logging
from typing import Dict, Any, Optional
import httpx
from config import settings

logger = logging.getLogger("ai_orchestrator.tools")

class HotelApiClient:
    def __init__(self):
        self.base_url = settings.dotnet_api_url.rstrip("/")

    async def get_room_availability(
        self,
        check_in: Optional[str] = None,
        check_out: Optional[str] = None,
        room_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calls GET /api/v1/rooms/availability?checkIn=...&checkOut=...&roomType=...
        """
        params = {}
        if check_in:
            params["checkIn"] = check_in
        if check_out:
            params["checkOut"] = check_out
        if room_type:
            params["roomType"] = room_type

        url = f"{self.base_url}/api/v1/rooms/availability"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info("Calling .NET API: %s with params %s", url, params)
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "rooms": data, "count": len(data)}
                else:
                    error_detail = "Failed to query rooms."
                    try:
                        err_json = response.json()
                        error_detail = err_json.get("detail", err_json.get("title", str(response.text)))
                    except Exception:
                        error_detail = response.text
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": error_detail
                    }
        except Exception as ex:
            logger.error("Exception connecting to .NET API at %s: %s", url, ex)
            return {
                "success": False,
                "status_code": 503,
                "error": "The reservation system service is temporarily unreachable. Please try again shortly."
            }

    async def create_booking(
        self,
        customer_name: str,
        check_in_date: str,
        check_out_date: str,
        room_id: int,
        pax: int = 2
    ) -> Dict[str, Any]:
        """
        Calls POST /api/v1/bookings with JSON payload.
        Handles 400 Bad Request gracefully so the LLM can apologize and provide clear alternatives.
        """
        payload = {
            "customerName": customer_name,
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
            "roomId": room_id,
            "pax": pax
        }

        url = f"{self.base_url}/api/v1/bookings"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.info("Calling .NET API: %s with payload %s", url, payload)
                response = await client.post(url, json=payload)

                if response.status_code in (200, 201):
                    return {"success": True, "booking": response.json()}
                elif response.status_code == 400:
                    # Business validation error (e.g., date in past, room unavailable, over capacity)
                    try:
                        err_json = response.json()
                        error_msg = err_json.get("detail") or err_json.get("title") or "Invalid reservation details."
                    except Exception:
                        error_msg = response.text
                    logger.warning(".NET API rejected booking (400): %s", error_msg)
                    return {
                        "success": False,
                        "status_code": 400,
                        "error": error_msg
                    }
                else:
                    logger.error(".NET API returned error status %d: %s", response.status_code, response.text)
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": "Unable to complete reservation due to a backend system error."
                    }
        except Exception as ex:
            logger.error("Exception during create_booking HTTP call: %s", ex)
            return {
                "success": False,
                "status_code": 503,
                "error": "The reservation booking service is momentarily offline."
            }

hotel_api = HotelApiClient()
