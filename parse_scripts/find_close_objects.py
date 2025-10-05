import json
import math
from typing import List, Dict, Any


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points in meters using Haversine formula
    """
    # Check if all coordinates are valid numbers
    if None in [lat1, lon1, lat2, lon2]:
        return float('inf')  # Return large distance for invalid coordinates

    R = 6371000  # Earth radius in meters

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_category_mapping() -> Dict[str, str]:
    """
    Map object categories to output field names
    """
    return {
        'детские сады': 'nearest_kindergartens',
        'больницы': 'nearest_child_hospitals',
        'парки': 'nearest_parks',
        'школы': 'nearest_schools',
        'поликлиники': 'nearest_clinics',
        'детские больницы': 'nearest_child_hospitals',
        'детские поликлиники': 'nearest_child_clinics',
        'музыкальные школы': 'nearest_music_schools'
    }


def find_nearest_objects(apartment_lat: float, apartment_lon: float,
                         objects: List[Dict], category_mapping: Dict[str, str], limit: int = 5) -> Dict[
    str, List[Dict]]:
    """
    Find nearest objects for each category
    """
    result = {}

    for category, output_field in category_mapping.items():
        # Filter objects by category
        category_objects = [obj for obj in objects if obj.get('category') == category]

        # Calculate distances and sort
        objects_with_distances = []
        for obj in category_objects:
            # Check if coordinates exist and are valid
            if ('coordinates' in obj and obj['coordinates'] and
                    obj['coordinates'].get('lat') is not None and
                    obj['coordinates'].get('lon') is not None):

                obj_lat = obj['coordinates']['lat']
                obj_lon = obj['coordinates']['lon']
                distance = calculate_distance(apartment_lat, apartment_lon, obj_lat, obj_lon)

                # Only add if distance is finite (valid coordinates)
                if distance != float('inf'):
                    objects_with_distances.append({
                        'name': obj.get('name', ''),
                        'address': obj.get('address', ''),
                        'coordinates': [
                            [obj_lon, obj_lat]  # Note: longitude first, then latitude
                        ],
                        'distance': round(distance, 1)
                    })

        # Sort by distance and take nearest ones
        objects_with_distances.sort(key=lambda x: x['distance'])
        result[output_field] = objects_with_distances[:limit]

    return result


def main():
    # Load objects data
    with open('/content/szao_moscow_objects_new.json', 'r', encoding='utf-8') as f:
        objects_data = json.load(f)

    # Load apartments data
    with open('/content/cian_north_west.json', 'r', encoding='utf-8') as f:
        apartments_data = json.load(f)

    # Get available categories from objects data
    available_categories = set(obj.get('category') for obj in objects_data)
    print(f"Available categories in objects data: {available_categories}")

    # Count objects with missing coordinates
    objects_with_coords = [obj for obj in objects_data if
                           obj.get('coordinates') and
                           obj['coordinates'].get('lat') is not None and
                           obj['coordinates'].get('lon') is not None]

    print(f"Total objects: {len(objects_data)}")
    print(f"Objects with valid coordinates: {len(objects_with_coords)}")
    print(f"Objects without coordinates: {len(objects_data) - len(objects_with_coords)}")

    # Define category mapping
    category_mapping = get_category_mapping()

    # Use only categories that exist in the data
    existing_categories = {cat: mapping for cat, mapping in category_mapping.items()
                           if cat in available_categories}

    print(f"Processing with categories: {list(existing_categories.keys())}")

    # Process each apartment
    processed_count = 0
    for i, apartment in enumerate(apartments_data):
        lat = apartment.get('latitude')
        lon = apartment.get('longitude')

        # Skip apartments with invalid coordinates
        if lat is None or lon is None:
            print(f"Skipping apartment {apartment.get('id')} - missing coordinates")
            continue

        # Find nearest objects
        nearest_objects = find_nearest_objects(lat, lon, objects_data, existing_categories)

        # Add to apartment data
        apartment['nearest_objects'] = {
            'coordinates': {
                'lat': lat,
                'lon': lon
            },
            **nearest_objects
        }
        processed_count += 1

        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} apartments")

    # Save result
    with open('cian_north_west_with_objects.json', 'w', encoding='utf-8') as f:
        json.dump(apartments_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully processed {processed_count} out of {len(apartments_data)} apartments")
    print("Result saved to cian_north_west_with_objects.json")


if __name__ == "__main__":
    main()