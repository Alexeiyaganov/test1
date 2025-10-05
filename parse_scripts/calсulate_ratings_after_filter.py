import json
import pandas as pd


def calculate_district_rating(value):
    try:
        with open('/content/district_statistics.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print("Ошибка: Файл district_statistics.json не найден")
        return {}
    except json.JSONDecodeError:
        print("Ошибка: Неверный формат JSON файла")
        return {}

    if 'district_statistics' in data:
        districts_data = data['district_statistics']
    else:
        districts_data = data

    if value < 0.5:
        categories = ['детские сады', 'детские поликлиники', 'детские больницы', 'парки']
    else:
        sample_district = next(iter(districts_data.values()))
        categories = [key for key in sample_district.keys() if
                      key != 'название' and isinstance(sample_district[key], (int, float))]

    ratings = {}

    for district_name, district_data in districts_data.items():
        total_score = 0
        valid_categories = 0

        for category in categories:
            if category in district_data and isinstance(district_data[category], (int, float)):
                total_score += district_data[category]
                valid_categories += 1

        ratings[district_name] = round(total_score / valid_categories, 1) if valid_categories > 0 else 0.0

    return ratings


if __name__ == "__main__":
    test_value_1 = 0.3
    test_value_2 = 0.8

    ratings_1 = calculate_district_rating(test_value_1)
    ratings_2 = calculate_district_rating(test_value_2)

    result = {
        "rating_for_0.3": ratings_1,
        "rating_for_0.8": ratings_2
    }

    with open('district_ratings_after_filter.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)