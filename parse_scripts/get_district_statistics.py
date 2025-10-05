import json
import geopandas as gpd
from shapely.geometry import Point, Polygon, shape
from collections import defaultdict
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_objects_data(file_path):
    """Загружает данные об объектах из JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Загружено {len(data)} объектов")
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки файла объектов: {e}")
        raise


def remove_duplicate_objects_by_coordinates(objects):
    """Удаляет дубликаты объектов только по координатам (latitude и longitude)"""
    logger.info("Удаление дубликатов объектов по координатам...")

    seen_coordinates = {}
    unique_objects = []
    duplicates_count = 0

    for obj in objects:
        if not isinstance(obj, dict):
            continue

        coords = obj.get('coordinates', {})

        # Проверяем валидность координат
        if not is_valid_coordinates(coords):
            unique_objects.append(obj)  # Сохраняем объекты с невалидными координатами
            continue

        try:
            lon = float(coords['lon'])
            lat = float(coords['lat'])

            # Создаем ключ для сравнения (только координаты)
            coord_key = (lon, lat)

            # Если объект с такими координатами уже встречался, пропускаем его
            if coord_key not in seen_coordinates:
                seen_coordinates[coord_key] = True
                unique_objects.append(obj)
            else:
                duplicates_count += 1
                logger.debug(f"Найден дубликат по координатам: {obj.get('name', 'Без названия')} - ({lon}, {lat})")

        except (ValueError, TypeError) as e:
            logger.warning(f"Ошибка обработки координат объекта {obj.get('name', 'Без названия')}: {e}")
            unique_objects.append(obj)

    logger.info(f"Удалено дубликатов по координатам: {duplicates_count}")
    logger.info(f"Осталось уникальных объектов: {len(unique_objects)}")

    return unique_objects


def update_original_file(objects, file_path):
    """Обновляет исходный файл, удаляя дубликаты"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(objects, f, ensure_ascii=False, indent=2)
        logger.info(f"Исходный файл {file_path} обновлен. Удалены дубликаты по координатам.")
    except Exception as e:
        logger.error(f"Ошибка обновления файла: {e}")
        raise


def load_parks_data(file_path):
    """Загружает данные о парках из JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Загружено {len(data)} парков")
        return data
    except Exception as e:
        logger.error(f"Ошибка загрузки файла парков: {e}")
        raise


def load_districts_data(file_path):
    """Загружает данные о районах из GeoJSON файла"""
    try:
        gdf = gpd.read_file(file_path)
        logger.info(f"Загружено {len(gdf)} районов")
        return gdf
    except Exception as e:
        logger.error(f"Ошибка загрузки файла районов: {e}")
        raise


def is_valid_coordinates(coords):
    """Проверяет валидность координат"""
    if not coords:
        return False
    if 'lon' not in coords or 'lat' not in coords:
        return False
    if coords['lon'] is None or coords['lat'] is None:
        return False
    try:
        float(coords['lon'])
        float(coords['lat'])
        return True
    except (TypeError, ValueError):
        return False


def is_valid_park_coordinates(coords):
    """Проверяет валидность координат парка"""
    if not coords:
        return False
    if not isinstance(coords, list) or len(coords) == 0:
        return False

    try:
        if isinstance(coords[0], list) and len(coords[0]) > 0:
            first_point = coords[0][0]
            if isinstance(first_point, list) and len(first_point) == 2:
                float(first_point[0])
                float(first_point[1])
                return True

        if isinstance(coords[0], list) and len(coords[0]) == 2:
            float(coords[0][0])
            float(coords[0][1])
            return True

    except (TypeError, ValueError, IndexError):
        return False

    return False


def create_park_polygon(coords):
    """Создает полигон парка из координат"""
    try:
        logger.debug(
            f"Структура координат парка: {type(coords)}, длина: {len(coords) if hasattr(coords, '__len__') else 'N/A'}")

        if isinstance(coords, list) and len(coords) > 0:
            if isinstance(coords[0], list) and len(coords[0]) > 0 and isinstance(coords[0][0], list):
                polygon_coords = [(point[0], point[1]) for point in coords[0] if
                                  isinstance(point, list) and len(point) == 2]
            elif isinstance(coords[0], list) and len(coords[0]) == 2:
                polygon_coords = [(point[0], point[1]) for point in coords if
                                  isinstance(point, list) and len(point) == 2]
            else:
                logger.warning(f"Неизвестная структура координат: {type(coords[0])}")
                return None

            if len(polygon_coords) >= 3:
                return Polygon(polygon_coords)
            else:
                logger.warning(f"Недостаточно точек для создания полигона: {len(polygon_coords)}")
                return None

    except Exception as e:
        logger.warning(f"Ошибка создания полигона парка: {e}")
        logger.warning(f"Координаты: {coords[:5] if hasattr(coords, '__len__') else coords}")
        return None


def assign_objects_to_districts(objects, parks, districts_gdf):
    """Сопоставляет объекты и парки с районами и подсчитывает категории"""

    district_stats = defaultdict(lambda: defaultdict(int))
    no_district_objects = []
    invalid_coordinates_objects = []

    # Обрабатываем обычные объекты
    logger.info("Обработка обычных объектов...")
    for i, obj in enumerate(objects):
        if i % 1000 == 0:
            logger.info(f"Обработано обычных объектов: {i}/{len(objects)}")

        if not isinstance(obj, dict):
            continue

        if not is_valid_coordinates(obj.get('coordinates')):
            invalid_coordinates_objects.append({
                'name': obj.get('name', 'Без названия'),
                'id': obj.get('id', 'Неизвестно'),
                'category': obj.get('category', 'Неизвестно'),
                'coordinates': obj.get('coordinates'),
                'type': 'object'
            })
            continue

        try:
            lon = float(obj['coordinates']['lon'])
            lat = float(obj['coordinates']['lat'])
            point = Point(lon, lat)

            found_district = None
            for idx, district in districts_gdf.iterrows():
                try:
                    if point.within(district.geometry):
                        found_district = district['NAME']
                        break
                except Exception as e:
                    continue

            if found_district:
                category = obj.get('category', 'без категории')
                district_stats[found_district][category] += 1
            else:
                no_district_objects.append({
                    'name': obj.get('name', 'Без названия'),
                    'id': obj.get('id', 'Неизвестно'),
                    'category': obj.get('category', 'Неизвестно'),
                    'coordinates': obj['coordinates'],
                    'type': 'object'
                })

        except Exception as e:
            logger.error(f"Ошибка обработки объекта {obj.get('id', 'Неизвестно')}: {e}")

    # Обрабатываем парки
    logger.info("Обработка парков...")
    successful_parks = 0
    failed_parks = 0

    for i, park in enumerate(parks):
        if i % 100 == 0:
            logger.info(f"Обработано парков: {i}/{len(parks)}")

        if not isinstance(park, dict):
            failed_parks += 1
            continue

        park_name = park.get('name', f'Парк {i}')
        park_coords = park.get('coordinates')

        if not is_valid_park_coordinates(park_coords):
            invalid_coordinates_objects.append({
                'name': park_name,
                'id': f'park_{i}',
                'category': 'парки',
                'coordinates': park_coords,
                'type': 'park'
            })
            failed_parks += 1
            continue

        try:
            park_polygon = create_park_polygon(park_coords)
            if not park_polygon:
                failed_parks += 1
                continue

            park_centroid = park_polygon.centroid

            found_district = None
            for idx, district in districts_gdf.iterrows():
                try:
                    if park_centroid.within(district.geometry):
                        found_district = district['NAME']
                        break
                except Exception as e:
                    continue

            if found_district:
                district_stats[found_district]['парки'] += 1
                successful_parks += 1
            else:
                no_district_objects.append({
                    'name': park_name,
                    'id': f'park_{i}',
                    'category': 'парки',
                    'coordinates': {'centroid': [park_centroid.x, park_centroid.y]},
                    'type': 'park'
                })
                failed_parks += 1

        except Exception as e:
            logger.error(f"Ошибка обработки парка {park_name}: {e}")
            failed_parks += 1

    logger.info(f"Обработка парков завершена. Успешно: {successful_parks}, Не удалось: {failed_parks}")
    logger.info(f"Объектов с невалидными координатами: {len(invalid_coordinates_objects)}")

    return district_stats, no_district_objects, invalid_coordinates_objects


def print_statistics(district_stats, no_district_objects, invalid_coordinates_objects):
    """Выводит статистику в удобном формате"""

    print("\n" + "=" * 80)
    print("СТАТИСТИКА ОБЪЕКТОВ И ПАРКОВ ПО РАЙОНАМ")
    print("=" * 80)

    all_categories = set()
    for district_categories in district_stats.values():
        all_categories.update(district_categories.keys())

    all_categories = sorted(list(all_categories))

    if district_stats and all_categories:
        header = f"{'Район':<25} " + " ".join([f"{cat[:15]:<15}" for cat in all_categories]) + " Всего"
        print(header)
        print("-" * len(header))

        total_by_district = {}
        for district in sorted(district_stats.keys()):
            row = f"{district:<25}"
            district_total = 0
            for category in all_categories:
                count = district_stats[district].get(category, 0)
                district_total += count
                row += f"{count:<15}"
            row += f"{district_total:<15}"
            total_by_district[district] = district_total
            print(row)

    print("\n" + "=" * 80)
    print("ОБЩАЯ СТАТИСТИКА:")

    total_with_district = sum(sum(categories.values()) for categories in district_stats.values())

    objects_with_district = 0
    parks_with_district = 0
    for categories in district_stats.values():
        for category, count in categories.items():
            if category == 'парки':
                parks_with_district += count
            else:
                objects_with_district += count

    objects_no_district = [obj for obj in no_district_objects if obj.get('type') != 'park']
    parks_no_district = [obj for obj in no_district_objects if obj.get('type') == 'park']

    total_objects = objects_with_district + len(objects_no_district)
    total_parks = parks_with_district + len(parks_no_district)

    print(f"Всего объектов: {total_objects}")
    print(f"  - с определённым районом: {objects_with_district}")
    print(f"  - без определённого района: {len(objects_no_district)}")

    print(f"Всего парков: {total_parks}")
    print(f"  - с определённым районом: {parks_with_district}")
    print(f"  - без определённого района: {len(parks_no_district)}")

    print(f"Записей с невалидными координатами: {len(invalid_coordinates_objects)}")
    print(f"Районов с объектами/парками: {len(district_stats)}")

    if district_stats:
        print("\nРАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ:")
        category_totals = defaultdict(int)
        for district_categories in district_stats.values():
            for category, count in district_categories.items():
                category_totals[category] += count

        for category, count in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category}: {count}")

    if parks_no_district:
        print(f"\nПЕРВЫЕ 10 ПАРКОВ БЕЗ ОПРЕДЕЛЁННОГО РАЙОНА:")
        for obj in parks_no_district[:10]:
            print(f"  - {obj['name']}")
            if 'centroid' in obj['coordinates']:
                print(f"    Центроид: {obj['coordinates']['centroid']}")

    if objects_no_district:
        print(f"\nПЕРВЫЕ 5 ОБЪЕКТОВ БЕЗ ОПРЕДЕЛЁННОГО РАЙОНА:")
        for obj in objects_no_district[:5]:
            print(f"  - {obj['name']} ({obj['category']})")

    if invalid_coordinates_objects:
        print(f"\nПЕРВЫЕ 5 ЗАПИСЕЙ С НЕВАЛИДНЫМИ КООРДИНАТАМИ:")
        for obj in invalid_coordinates_objects[:5]:
            obj_type = obj.get('type', 'object')
            print(f"  - {obj['name']} ({obj['category']}) - {obj_type}")


def save_results_to_json(district_stats, output_file='district_statistics.json'):
    """Сохраняет результаты в JSON файл"""
    try:
        result = {
            'district_statistics': {
                district: dict(categories)
                for district, categories in district_stats.items()
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\nРезультаты сохранены в файл: {output_file}")
    except Exception as e:
        logger.error(f"Ошибка сохранения результатов: {e}")


def main():
    # Пути к файлам
    objects_file = '/content/szao_moscow_objects.json'  # Файл с объектами
    parks_file = '/content/parks.json'  # Файл с парками
    districts_file = '/content/mo.geojson'  # Файл с районами

    try:
        # Загрузка данных об объектах
        logger.info("Загрузка данных об объектах...")
        objects = load_objects_data(objects_file)

        # Удаление дубликатов по координатам
        logger.info("Удаление дубликатов по координатам...")
        unique_objects = remove_duplicate_objects_by_coordinates(objects)

        # Обновление исходного файла
        update_original_file(unique_objects, objects_file)

        # Теперь используем очищенные данные для дальнейшей обработки
        logger.info("Загрузка данных о парках...")
        parks = load_parks_data(parks_file)

        logger.info("Загрузка данных о районах...")
        districts_gdf = load_districts_data(districts_file)

        # Обработка данных (используем уже очищенные объекты)
        logger.info("Сопоставление объектов и парков с районами...")
        district_stats, no_district_objects, invalid_coordinates_objects = assign_objects_to_districts(
            unique_objects, parks, districts_gdf
        )

        # Вывод результатов
        print_statistics(district_stats, no_district_objects, invalid_coordinates_objects)

        # Сохранение результатов
        save_results_to_json(district_stats)

    except FileNotFoundError as e:
        logger.error(f"Файл не найден: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Неверный формат JSON файла: {e}")
    except Exception as e:
        logger.error(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    main()