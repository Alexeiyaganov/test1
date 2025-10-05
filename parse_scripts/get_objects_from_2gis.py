import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional


class BaseDGISCollector:
    """Базовый класс для сбора данных через API 2GIS"""

    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://catalog.api.2gis.com/3.0/items"
        self.headers = {"Authorization": f"Bearer {token}"}

    def _make_api_request(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Выполнение API запроса с обработкой ошибок"""
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"    Ошибка при запросе: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"    Ошибка парсинга JSON: {e}")
            return None


class RegionManager:
    """Класс для управления регионами поиска"""

    def __init__(self):
        self.regions = [
            {"name": "Строгино", "lon": 37.408, "lat": 55.804},
            {"name": "Митино", "lon": 37.360, "lat": 55.845},
            {"name": "Куркино", "lon": 37.402, "lat": 55.883},
            {"name": "Покровское-Стрешнево", "lon": 37.447, "lat": 55.813},
            {"name": "Щукино", "lon": 37.467, "lat": 55.808},
            {"name": "Хорошево-Мневники", "lon": 37.471, "lat": 55.780},
            {"name": "Северное Тушино", "lon": 37.417, "lat": 55.850},
            {"name": "Южное Тушино", "lon": 37.433, "lat": 55.833}
        ]

    def get_regions(self) -> List[Dict[str, Any]]:
        """Получение списка всех регионов"""
        return self.regions

    def get_region_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Получение региона по имени"""
        return next((region for region in self.regions if region["name"] == name), None)


class CategoryManager:
    """Класс для управления категориями поиска"""

    def __init__(self):
        self.categories = {
            "больницы": {"query": "больница взрослая", "use_rubric": False},
            "поликлиники": {"query": "поликлиника взрослая", "use_rubric": False},
            "детские больницы": {"query": "детская больница", "use_rubric": False},
            "детские поликлиники": {"query": "детская поликлиника", "use_rubric": False},
            "школы": {"query": "школа", "use_rubric": False},
            "детские сады": {"query": "детский сад", "use_rubric": False},
            "парки": {"query": "", "use_rubric": True},
            "лес": {"query": "", "use_rubric": True},
            "музыкальные школы": {"query": "музыкальная школа", "use_rubric": False},
            "спортивные секции": {"query": "спортивная секция", "use_rubric": False}
        }

        self.rubric_ids = {
            "парки": "17519,17520",
            "лес": "17521,17522",
            "больницы": "15633,15634",
            "школы": "15652",
            "детские сады": "15658",
            "музыкальные школы": "15713",
            "спортивные секции": "15739,15740"
        }

    def get_categories(self) -> Dict[str, Dict]:
        """Получение всех категорий"""
        return self.categories

    def get_rubric_id(self, category: str) -> str:
        """Получение ID рубрики для категории"""
        return self.rubric_ids.get(category, "")

    def should_use_rubric(self, category: str) -> bool:
        """Проверка, используется ли для категории рубрикатор"""
        return self.categories.get(category, {}).get("use_rubric", False)


class ObjectDataProcessor:
    """Класс для обработки данных объектов"""

    @staticmethod
    def extract_contacts(contacts: Dict) -> Dict:
        """Извлечение контактной информации"""
        result = {}
        if "phones" in contacts and contacts["phones"]:
            result["phones"] = [phone.get("number", "") for phone in contacts["phones"][:3]]
        if "email" in contacts and contacts["email"]:
            result["emails"] = contacts["email"][:2]
        if "websites" in contacts and contacts["websites"]:
            result["websites"] = [site.get("url", "") for site in contacts["websites"][:2]]
        return result

    @staticmethod
    def extract_hours(contacts: Dict) -> str:
        """Извлечение информации о часах работы"""
        if "hours" in contacts and "text" in contacts["hours"]:
            return contacts["hours"]["text"]
        return ""

    @staticmethod
    def get_rubric_name(rubrics: List[Dict]) -> str:
        """Получение названия рубрики"""
        if rubrics:
            return rubrics[0].get("name", "")
        return ""


class ObjectDetailsFetcher(BaseDGISCollector):
    """Класс для получения детальной информации об объектах"""

    def get_object_details(self, object_id: str) -> Dict[str, Any]:
        """Получение детальной информации об объекте включая отзывы"""
        if not object_id:
            return {}

        url = f"https://catalog.api.2gis.com/3.0/items/{object_id}"
        params = {
            "fields": "reviews,rating,reviews_count",
            "key": self.token
        }

        data = self._make_api_request(url, params)
        if not data:
            return {}

        result = data.get("result", {})
        reviews = self._extract_reviews(result)

        return {
            "rating": result.get("rating", {}).get("value"),
            "reviews_count": result.get("reviews_count", 0),
            "reviews": reviews
        }

    def _extract_reviews(self, result: Dict) -> List[Dict]:
        """Извлечение отзывов из данных объекта"""
        reviews = []
        if "reviews" in result and "items" in result["reviews"]:
            for review in result["reviews"]["items"][:3]:
                reviews.append({
                    "text": review.get("text", "")[:200],
                    "rating": review.get("rating"),
                    "author": review.get("author", {}).get("name", ""),
                    "date": review.get("date", "")
                })
        return reviews


class ObjectSearcher(BaseDGISCollector):
    """Класс для поиска объектов по категориям и регионам"""

    def __init__(self, token: str):
        super().__init__(token)
        self.category_manager = CategoryManager()
        self.object_processor = ObjectDataProcessor()
        self.details_fetcher = ObjectDetailsFetcher(token)

    def search_objects(self, category: str, region: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Поиск объектов в конкретном районе
        """
        all_objects = []
        page = 1

        while True:
            params = self._build_search_params(category, region, page)
            if not params:
                break

            data = self._make_api_request(self.base_url, params)
            if not data:
                break

            items = data.get("result", {}).get("items", [])
            if not items:
                break

            # Обработка найденных объектов
            page_objects = self._process_items(items, category, region)
            all_objects.extend(page_objects)

            print(f"    Найдено объектов на странице {page}: {len(items)}")

            # Проверка на последнюю страницу
            if len(items) < 50:
                break

            page += 1
            time.sleep(0.3)

        return all_objects

    def _build_search_params(self, category: str, region: Dict[str, Any], page: int) -> Dict[str, Any]:
        """Построение параметров поиска"""
        base_params = {
            "sort": "relevance",
            "fields": "items.point,items.reviews,items.rating,items.address,items.name,items.rubrics,items.description,items.contacts,items.external_content",
            "location": f"{region['lon']},{region['lat']}",
            "key": self.token,
            "page_size": 50,
            "page": page
        }

        if self.category_manager.should_use_rubric(category):
            rubric_id = self.category_manager.get_rubric_id(category)
            if not rubric_id:
                return {}
            base_params["rubric_id"] = rubric_id
            base_params["radius"] = 5000
        else:
            category_info = self.category_manager.get_categories().get(category, {})
            base_params["q"] = category_info.get("query", "")
            base_params["radius"] = 3000

        return base_params

    def _process_items(self, items: List[Dict], category: str, region: Dict) -> List[Dict]:
        """Обработка найденных объектов"""
        processed_objects = []

        for item in items:
            detailed_info = self.details_fetcher.get_object_details(item.get("id"))

            obj_data = {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "address": item.get("address_name", ""),
                "district": region["name"],
                "coordinates": {
                    "lon": item.get("point", {}).get("lon"),
                    "lat": item.get("point", {}).get("lat")
                },
                "rating": detailed_info.get("rating"),
                "reviews_count": detailed_info.get("reviews_count", 0),
                "reviews_preview": detailed_info.get("reviews", []),
                "category": category,
                "type": self.object_processor.get_rubric_name(item.get("rubrics", [])),
                "description": item.get("description", ""),
                "contacts": self.object_processor.extract_contacts(item.get("contacts", {})),
                "working_hours": self.object_processor.extract_hours(item.get("contacts", {}))
            }
            processed_objects.append(obj_data)

        return processed_objects


class DataCollector:
    """Основной класс для сбора данных"""

    def __init__(self, token: str):
        self.region_manager = RegionManager()
        self.object_searcher = ObjectSearcher(token)
        self.statistics = StatisticsCalculator()

    def collect_all_data(self) -> List[Dict[str, Any]]:
        """
        Сбор данных по всем категориям и районам
        """
        all_objects = []
        categories = self.object_searcher.category_manager.get_categories()

        for category_name in categories.keys():
            print(f"\n🔍 Поиск: {category_name}")
            category_objects = self._collect_category_data(category_name)
            all_objects.extend(category_objects)
            print(f"🎯 Всего по категории '{category_name}': {len(category_objects)} объектов")

        return all_objects

    def _collect_category_data(self, category: str) -> List[Dict[str, Any]]:
        """Сбор данных для конкретной категории"""
        category_objects = []

        for region in self.region_manager.get_regions():
            print(f"  📍 Район: {region['name']}")
            objects = self.object_searcher.search_objects(category, region)
            category_objects.extend(objects)
            print(f"  ✅ В районе {region['name']} найдено: {len(objects)} объектов")
            time.sleep(0.5)

        return category_objects


class StatisticsCalculator:
    """Класс для расчета статистики"""

    def calculate_statistics(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Расчет статистики по собранным данным"""
        categories_stats = {}
        districts_stats = {}
        ratings_stats = {"с рейтингом": 0, "без рейтинга": 0}
        reviews_stats = {"с отзывами": 0, "без отзывов": 0}

        for obj in data:
            cat = obj["category"]
            district = obj["district"]

            # Статистика по категориям и районам
            categories_stats[cat] = categories_stats.get(cat, 0) + 1
            districts_stats[district] = districts_stats.get(district, 0) + 1

            # Статистика по рейтингам
            if obj["rating"] is not None:
                ratings_stats["с рейтингом"] += 1
            else:
                ratings_stats["без рейтинга"] += 1

            # Статистика по отзывам
            if obj["reviews_count"] > 0:
                reviews_stats["с отзывами"] += 1
            else:
                reviews_stats["без отзывов"] += 1

        return {
            "total_objects": len(data),
            "categories": categories_stats,
            "districts": districts_stats,
            "ratings": ratings_stats,
            "reviews": reviews_stats
        }

    def print_statistics(self, data: List[Dict[str, Any]]):
        """Вывод статистики в консоль"""
        stats = self.calculate_statistics(data)

        print("\n📊 СТАТИСТИКА СБОРА ДАННЫХ")
        print("=" * 50)
        print(f"Всего объектов: {stats['total_objects']}")
        print(f"Объектов с рейтингом: {stats['ratings']['с рейтингом']}")
        print(f"Объектов с отзывами: {stats['reviews']['с отзывами']}")

        print("\n📈 По категориям:")
        for cat, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count} объектов")

        print("\n🗺️ По районам:")
        for district, count in sorted(stats['districts'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {district}: {count} объектов")


class JSONDataSaver:
    """Класс для сохранения данных в JSON"""

    @staticmethod
    def save_to_json(data: List[Dict[str, Any]], filename: str = None) -> str:
        """Сохранение данных в JSON файл"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"szao_moscow_objects_full_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 Данные сохранены в JSON: {filename}")
        return filename


class DGISDataCollector:
    """Главный класс приложения"""

    def __init__(self, token: str):
        self.data_collector = DataCollector(token)
        self.json_saver = JSONDataSaver()
        self.statistics_calculator = StatisticsCalculator()

    def run(self):
        """Запуск процесса сбора данных"""
        print("🚀 Запуск сбора данных по Северо-западному округу Москвы")
        print("⏳ Это может занять несколько минут...")
        print(
            "📝 Собираем: больницы, поликлиники, школы, детские сады, парки, лес, музыкальные школы, спортивные секции")

        start_time = time.time()
        data = self.data_collector.collect_all_data()
        end_time = time.time()
        execution_time = end_time - start_time

        print(f"\n✅ Сбор данных завершен за {execution_time:.1f} секунд")

        if data:
            self._process_results(data)
        else:
            print("❌ Не удалось собрать данные. Проверьте токен и подключение к интернету.")

    def _process_results(self, data: List[Dict[str, Any]]):
        """Обработка и сохранение результатов"""
        # Сохранение данных
        json_file = self.json_saver.save_to_json(data)

        # Вывод статистики
        self.statistics_calculator.print_statistics(data)

        # Вывод информации о файле
        print(f"\n📁 Результаты сохранены в файл: {json_file}")

        # Показ примеров объектов
        self._show_examples(data)

    def _show_examples(self, data: List[Dict[str, Any]]):
        """Показать примеры найденных объектов"""
        print(f"\n📋 Примеры найденных объектов:")
        objects_with_reviews = [obj for obj in data if obj['reviews_count'] > 0]
        for i, obj in enumerate(objects_with_reviews[:3]):
            print(f"  {i + 1}. {obj['name']} ({obj['category']})")
            print(f"     Адрес: {obj['address']}")
            print(f"     Рейтинг: {obj['rating'] or 'нет'} | Отзывов: {obj['reviews_count']}")
            if obj['reviews_preview']:
                print(f"     Последний отзыв: {obj['reviews_preview'][0]['text'][:100]}...")


def main():
    """Основная функция приложения"""
    API_TOKEN = "1c4ddd6d-cc51-4d85-83ea-dcb4a7cb96f5"

    collector = DGISDataCollector(API_TOKEN)
    collector.run()


if __name__ == "__main__":
    main()