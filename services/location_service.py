import requests
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class LocationService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.opencage_url = "https://api.opencagedata.com/geocode/v1/json"
        
    def search_location(self, query: str) -> List[Dict]:
        """
        Search locations using OpenCage (if key available) or Nominatim
        """
        if self.api_key:
            return self._search_opencage(query)
        else:
            return self._search_nominatim(query)

    def _search_opencage(self, query: str) -> List[Dict]:
        try:
            params = {
                'q': query,
                'key': self.api_key,
                'limit': 5,
                'language': 'tr',
                'no_annotations': 1
            }
            
            response = requests.get(self.opencage_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for res in data.get('results', []):
                    # Standardize for both JS expectations (some use lat/lon, some latitude/longitude)
                    results.append({
                        'name': res.get('formatted', ''),
                        'display_name': res.get('formatted', ''),
                        'lat': res.get('geometry', {}).get('lat'),
                        'lon': res.get('geometry', {}).get('lng'),
                        'latitude': res.get('geometry', {}).get('lat'),
                        'longitude': res.get('geometry', {}).get('lng'),
                        'country': res.get('components', {}).get('country', ''),
                        'type': res.get('components', {}).get('_type', 'location')
                    })
                return results
            else:
                logger.error(f"OpenCage search failed: {response.status_code}")
                # Fallback to Nominatim if OpenCage fails
                return self._search_nominatim(query)
        except Exception as e:
            logger.error(f"OpenCage error: {str(e)}")
            return self._search_nominatim(query)

    def _search_nominatim(self, query: str) -> List[Dict]:
        try:
            params = {
                'q': query,
                'format': 'json',
                'limit': 5,
                'accept-language': 'tr',
                'addressdetails': 1
            }
            
            headers = {
                'User-Agent': 'ORBIS-AstroApp/1.0',
                'Accept-Language': 'tr'
            }
            
            response = requests.get(
                self.nominatim_url,
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                formatted_results = []
                
                for location in results:
                    address = location.get('address', {})
                    lat = float(location.get('lat', 0))
                    lon = float(location.get('lon', 0))
                    country = address.get('country', '')
                    display_name = location.get('display_name', '')
                    
                    formatted_results.append({
                        'name': display_name.split(',')[0],
                        'display_name': display_name,
                        'lat': lat,
                        'lon': lon,
                        'latitude': lat,
                        'longitude': lon,
                        'country': country,
                        'type': location.get('type', '')
                    })
                
                return formatted_results
            return []
        except Exception as e:
            logger.error(f"Nominatim error: {str(e)}")
            return []
