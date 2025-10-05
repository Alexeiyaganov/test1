import json
from shapely.geometry import Polygon, Point


# Функция для вычисления центроида полигона
def calculate_centroid(coordinates):
    if not coordinates or len(coordinates) < 3:
        return None

    try:
        polygon = Polygon(coordinates)
        centroid = polygon.centroid
        return {
            "lon": centroid.x,
            "lat": centroid.y
        }
    except Exception as e:
        print(f"Ошибка при вычислении центроида: {e}")
        return None


# Чтение данных из файлов
with open('/content/szao_moscow_objects.json', 'r', encoding='utf-8') as f:
    szao_objects = json.load(f)

with open('parks.json', 'r', encoding='utf-8') as f:
    parks_data = json.load(f)

# Преобразование парков в нужный формат
parks_formatted = []
for park in parks_data:
    if park.get('coordinates') and len(park['coordinates']) > 0:
        centroid = calculate_centroid(park['coordinates'])
        if centroid:
            park_object = {
                "id": f"park_{len(parks_formatted) + 1}",
                "name": park.get('name', 'Парк'),
                "address": park.get('address'),
                "district": None,  # Можно добавить логику для определения района
                "coordinates": centroid,
                "rating": None,
                "reviews_count": 0,
                "reviews_preview": [],
                "category": "парки",
                "type": "Парки",
                "description": "",
                "contacts": {},
                "working_hours": ""
            }
            parks_formatted.append(park_object)

# Объединение данных
combined_data = szao_objects + parks_formatted

# Сохранение результата
with open('/content/parks.json', 'w', encoding='utf-8') as f:
    json.dump(combined_data, f, ensure_ascii=False, indent=2)

print(f"Добавлено {len(parks_formatted)} парков в файл")
print(f"Общее количество объектов: {len(combined_data)}")