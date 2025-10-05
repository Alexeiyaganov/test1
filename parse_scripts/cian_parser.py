import requests
import json
import time
from datetime import datetime


class CianNorthWestRentParser:
    def __init__(self):
        self.session = requests.Session()
        self.set_headers()
        self.results = []

    def set_headers(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Content-Type': 'application/json',
            'Origin': 'https://www.cian.ru',
            'Referer': 'https://www.cian.ru/',
        }
        self.session.headers.update(self.headers)

    def search_offers(self, page=1):
        """Поиск объявлений через API"""
        url = "https://api.cian.ru/search-offers/v2/search-offers-desktop/"

        payload = {
            "jsonQuery": {
                "_type": "flatrent",
                "engine_version": {"type": "term", "value": 2},
                "region": {"type": "terms", "value": [1]},  # Москва
                "district": {"type": "terms", "value": [1]},  # Северо-Западный округ
                "room": {"type": "terms", "value": [1, 2, 3, 4, 5, 6, 0]},  # Все типы квартир включая студии
                "page": {"type": "term", "value": page}
            }
        }

        try:
            response = self.session.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Ошибка на странице {page}: {e}")
        return None

    def parse_offer(self, offer):
        """Парсинг одного объявления"""
        try:
            result = {}

            # Основная информация
            result['id'] = offer.get('id')
            result['title'] = offer.get('title', '')
            result['url'] = f"https://www.cian.ru/rent/flat/{offer.get('id')}/"

            # Цена
            price_data = offer.get('price', {})
            if price_data:
                result['price'] = price_data.get('total', {}).get('value')
            if not result.get('price'):
                result['price'] = offer.get('bargainTerms', {}).get('priceRur')

            # Площадь
            area = offer.get('totalArea')
            if area:
                if isinstance(area, str):
                    import re
                    match = re.search(r'(\d+\.?\d*)', area)
                    if match:
                        result['area'] = float(match.group(1))
                else:
                    result['area'] = area

            # Комнаты
            result['rooms'] = offer.get('roomsCount')
            if result['rooms'] == 0:
                result['room_type'] = 'студия'
            else:
                result['room_type'] = f'{result["rooms"]}-комнатная'

            # Этажи
            result['floor'] = offer.get('floorNumber')
            result['total_floors'] = offer.get('building', {}).get('floorsCount')

            # Адрес и геолокация
            geo = offer.get('geo', {})
            result['address'] = geo.get('userInput', '')
            result['latitude'] = geo.get('coordinates', {}).get('lat')
            result['longitude'] = geo.get('coordinates', {}).get('lng')

            # Метро
            undergrounds = geo.get('undergrounds', [])
            if undergrounds:
                metro = undergrounds[0]
                result['metro'] = metro.get('name')
                result['metro_time'] = metro.get('time')
                result['metro_line'] = metro.get('lineName')
                result['metro_color'] = metro.get('hexColor')

            # Дом
            building = offer.get('building', {})
            result['building_type'] = building.get('buildingType')
            result['build_year'] = building.get('buildYear')

            # Условия аренды
            bargain = offer.get('bargainTerms', {})
            result['deposit'] = bargain.get('deposit')
            result['agent_fee'] = bargain.get('clientFee')
            result['commission'] = bargain.get('commission')

            # Контакты
            result['is_by_homeowner'] = offer.get('isByHomeowner', False)
            result['agency_name'] = offer.get('agency', {}).get('name')

            # Описание
            result['description'] = offer.get('description', '')[:500]  # Ограничиваем длину

            # Дата публикации
            result['creation_date'] = offer.get('creationDate')

            # Дата парсинга
            result['parsed_at'] = datetime.now().isoformat()

            return result

        except Exception as e:
            print(f"Ошибка парсинга объявления {offer.get('id')}: {e}")
            return None

    def extract_offers(self, data):
        """Извлечение объявлений из ответа"""
        if not data:
            return []

        # Пробуем разные пути в JSON
        paths = [
            ['data', 'offersSerialized'],
            ['offers'],
            ['data', 'offers'],
        ]

        for path in paths:
            try:
                current = data
                for key in path:
                    current = current[key]
                if isinstance(current, list):
                    return current
            except:
                continue
        return []

    def collect_all_offers(self):
        """Сбор всех объявлений"""
        print("🚀 Начинаем сбор объявлений...")

        page = 1
        total_offers = 0

        while True:
            print(f"📄 Страница {page}...")

            data = self.search_offers(page)
            if not data:
                print("❌ Не удалось получить данные")
                break

            offers = self.extract_offers(data)
            if not offers:
                print("📭 Объявления закончились")
                break

            # Парсим объявления со страницы
            page_offers = []
            for offer in offers:
                parsed = self.parse_offer(offer)
                if parsed:
                    page_offers.append(parsed)

            self.results.extend(page_offers)
            total_offers += len(page_offers)

            print(f"✅ Страница {page}: {len(page_offers)} объявлений")

            # Проверяем, есть ли еще страницы
            if len(offers) < 28:  # Обычно на странице 28 объявлений
                print("🎯 Последняя страница достигнута")
                break

            page += 1
            time.sleep(1)  # Пауза между запросами

            # Защита от бесконечного цикла
            if page > 50:
                print("⚠️ Достигнут лимит страниц")
                break

        print(f"🎉 Сбор завершен! Всего собрано: {total_offers} объявлений")

    def save_to_json(self):
        """Сохранение в JSON файл"""
        if not self.results:
            print("❌ Нет данных для сохранения")
            return None

        filename = f'cian_north_west_rent_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

        # Сортируем по цене (от большей к меньшей)
        sorted_results = sorted(self.results, key=lambda x: x.get('price', 0), reverse=True)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(sorted_results, f, ensure_ascii=False, indent=2)

        print(f"💾 Данные сохранены в: {filename}")
        return filename

    def show_summary(self):
        """Показ сводной информации"""
        if not self.results:
            return

        print(f"\n📊 СВОДКА ПО СЕВЕРО-ЗАПАДНОМУ ОКРУГУ:")
        print(f"Всего объявлений: {len(self.results)}")

        # Статистика по ценам
        prices = [o['price'] for o in self.results if o.get('price')]
        if prices:
            print(f"💰 Цены: {min(prices):,} - {max(prices):,} ₽")
            print(f"📈 Средняя цена: {sum(prices) / len(prices):,.0f} ₽")

        # Статистика по комнатам
        rooms_stats = {}
        for offer in self.results:
            rooms = offer.get('rooms', 0)
            rooms_stats[rooms] = rooms_stats.get(rooms, 0) + 1

        print("🏠 Распределение по комнатам:")
        for rooms in sorted(rooms_stats.keys()):
            count = rooms_stats[rooms]
            name = "Студия" if rooms == 0 else f"{rooms}-к"
            print(f"   {name}: {count} объяв.")

        # Топ станций метро
        metro_stats = {}
        for offer in self.results:
            metro = offer.get('metro')
            if metro:
                metro_stats[metro] = metro_stats.get(metro, 0) + 1

        if metro_stats:
            print("🚇 Топ станций метро:")
            for metro, count in sorted(metro_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   {metro}: {count}")


def main():
    print("=" * 60)
    print("🏠 ПАРСЕР ЦИАН - АРЕНДА КВАРТИР")
    print("📍 СЕВЕРО-ЗАПАДНЫЙ ОКРУГ МОСКВЫ")
    print("=" * 60)

    parser = CianNorthWestRentParser()

    # Собираем все объявления
    parser.collect_all_offers()

    if parser.results:
        # Показываем сводку
        parser.show_summary()

        # Сохраняем в JSON
        filename = parser.save_to_json()

        print(f"\n✅ Готово! Файл: {filename}")
        print(f"📁 Количество объявлений: {len(parser.results)}")

    else:
        print("❌ Не удалось собрать объявления")


if __name__ == "__main__":
    main()