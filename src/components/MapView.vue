<script setup>
//
// MapView.vue — главный экран карты (2ГИС MapGL)
// Что реализовано:
// 1) Инициализация карты 2ГИС и ограничение области Москвой
// 2) Переключатель «районы»: загрузка mo.geojson и отрисовка полигонов районов
// 3) Построение «тепловых облаков» по квартирам (из appartments.json),
//    динамический размер облака (выпуклая оболочка + сглаживание), раскраска green/orange/red
// 4) Клик по району → фильтрация квартир в районе → тепловая карта по ним
// 5) Клик по облаку → зум к кластеру, показ точек квартир и визуализация ближайших объектов
//    (детсад/детская поликлиника/парк) с линиями от квартир
//
// Важные сущности:
// - heatClusters: кластера квартир для теплокарты (центр, список квартир, цвет)
// - districtPolygons: полигоны районов
// - facilityMarkers/facilityLines: маркеры объектов и линии до них
// - cachedApartments/cachedDistricts: кэш загруженных данных
//
import { onMounted, onBeforeUnmount, ref, watch, defineExpose, defineEmits } from 'vue'
import { load } from '@2gis/mapgl'

const mapContainerRef = ref(null)
const emit = defineEmits(['district-selected', 'cluster-selected'])
const props = defineProps({
  points: { type: Array, default: () => [] }, // [{ latitude, longitude }]
})

// SVG-иконка «квартира» с синим фоном (на основе присланного SVG)
const APARTMENT_ICON =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<?xml version="1.0" encoding="utf-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="-9.22 0 122.88 122.88" width="64" height="64">
      <rect x="-9.22" y="0" width="122.88" height="122.88" rx="16" fill="#1D4ED8"/>
      <path fill="#000000" d="M3.55,119.32H0v3.56H92.49v-3.56h-2v-17a1.22,1.22,0,0,0-1.22-1.22H75.54a1.22,1.22,0,0,0-1.22,1.22v17H48.47V95.23a1.63,1.63,0,0,0-1.63-1.62H19.94a1.63,1.63,0,0,0-1.63,1.62v24.09H0V2.6A2.79,2.79,0,0,1,.82.85h0a2.84,2.84,0,0,1,2-.84H63.93a2.82,2.82,0,0,1,2,.84l.13.13a2.83,2.83,0,0,1,.72,1.89V34.57H102a2.39,2.39,0,0,1,1.69.7h0a2.36,2.36,0,0,1,.7,1.68v84.29a1.63,1.63,0,0,1-1.63,1.63H92.49v-3.56H101V38H66.79v81.34H63.23V3.56H3.55V119.32Zm84.54,0H76.76V103.5H88.09v15.82ZM85.45,45h8.81c.07,0,.13.1.13.22v5.71c0,.1-.06.21-.13.21H85.45c-.07,0-.13-.09-.13-.21V45.22c0-.12.06-.22.13-.22Zm0,39.6h8.81c.07,0,.13.1.13.21v5.71c0,.11-.06.22-.13.22H85.45c-.07,0-.13-.1-.13-.22V84.81c0-.11.06-.21.13-.21Zm-14.85,0h8.8c.08,0,.14.1.14.21v5.71c0,.11-.06.22-.14.22H70.6c-.08,0-.14-.1-.14-.22V84.81c0-.11.06-.21.14-.21ZM85.45,71.4h8.81c.07,0,.13.1.13.22v5.71c0,.11-.06.22-.13.22H85.45c-.07,0-.13-.1-.13-.22V71.62c0-.13.06-.22.13-.22Zm0-13.2h8.81c.07,0,.13.1.13.22v5.71c0,.11-.06.22-.13.22H85.45c-.07,0-.13-.1-.13-.22V58.42c0-.12.06-.22.13-.22ZM70.6,45h8.8c.08,0,.14.1.14.22v5.71c0,.1-.06.21-.14.21H70.6c-.08,0-.14-.09-.14-.21V45.22c0-.12.06-.22.14-.22Zm0,26.4h8.8c.08,0,.14.1.14.22v5.71c0,.11-.06.22-.14.22H70.6c-.08,0-.14-.1-.14-.22V71.62c0-.13.06-.22.14-.22Zm0-13.2h8.8c.08,0,.14.1.14.22v5.71c0,.11-.06.22-.14.22H70.6c-.08,0-.14-.1-.14-.22V58.42c0-.12.06-.22.14-.22ZM45.21,119.32H21.57V96.86H45.21v22.46ZM12.13,12.52h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H12.13a.28.28,0,0,1-.27-.27V12.79a.28.28,0,0,1,.27-.27Zm32.94,0h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H45.07a.28.28,0,0,1-.27-.27V12.79a.28.28,0,0,1,.27-.27Zm-16.47,0h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H28.6a.28.28,0,0,1-.27-.27V12.79a.28.28,0,0,1,.27-.27ZM12.13,33.28h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H12.13a.28.28,0,0,1-.27-.27V33.55a.28.28,0,0,1,.27-.27Zm32.94,0h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H45.07a.28.28,0,0,1-.27-.27V33.55a.28.28,0,0,1,.27-.27Zm-16.47,0h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H28.6a.28.28,0,0,1-.27-.27V33.55a.28.28,0,0,1,.27-.27ZM12.13,74.8h9.58a.27.27,0,0,1,.27.27v9.58a.27.27,0,0,1-.27.27H12.13a.27.27,0,0,1-.27-.27V75.07a.27.27,0,0,1,.27-.27Zm32.94,0h9.58a.27.27,0,0,1,.27.27v9.58a.27.27,0,0,1-.27.27H45.07a.27.27,0,0,1-.27-.27V75.07a.27.27,0,0,1,.27-.27Zm-16.47,0h9.58a.27.27,0,0,1,.27.27v9.58a.27.27,0,0,1-.27.27H28.6a.27.27,0,0,1-.27-.27V75.07a.27.27,0,0,1,.27-.27ZM12.13,54h9.58a.27.27,0,0,1,.27.27V63.9a.28.28,0,0,1-.27.27H12.13a.28.28,0,0,1-.27-.27V54.31a.27.27,0,0,1,.27-.27Zm32.94,0h9.58a.27.27,0,0,1,.27.27V63.9a.28.28,0,0,1-.27.27H45.07a.28.28,0,0,1-.27-.27V54.31a.27.27,0,0,1,.27-.27ZM28.6,54h9.58a.27.27,0,0,1,.27.27V63.9a.28.28,0,0,1-.27.27H28.6a.28.28,0,0,1-.27-.27V54.31A.27.27,0,0,1,28.6,54Z"/>
    </svg>`
  )

// HTML-обёртка маркера квартиры (крупный круг + SVG-«квартира»)
function createApartmentMarkerHtml() {
  return `
    <div class="apartment-marker">
      <svg class="apartment-marker__icon" viewBox="-9.22 0 122.88 122.88" xmlns="http://www.w3.org/2000/svg">
        <path fill="currentColor" d="M3.55,119.32H0v3.56H92.49v-3.56h-2v-17a1.22,1.22,0,0,0-1.22-1.22H75.54a1.22,1.22,0,0,0-1.22,1.22v17H48.47V95.23a1.63,1.63,0,0,0-1.63-1.62H19.94a1.63,1.63,0,0,0-1.63,1.62v24.09H0V2.6A2.79,2.79,0,0,1,.82.85h0a2.84,2.84,0,0,1,2-.84H63.93a2.82,2.82,0,0,1,2,.84l.13.13a2.83,2.83,0,0,1,.72,1.89V34.57H102a2.39,2.39,0,0,1,1.69.7h0a2.36,2.36,0,0,1,.7,1.68v84.29a1.63,1.63,0,0,1-1.63,1.63H92.49v-3.56H101В38H66.79v81.34H63.23В3.56H3.55В119.32Zm84.54,0H76.76В103.5H88.09в15.82ZM85.45,45h8.81c.07,0,.13.1.13.22v5.71c0,.1-.06.21-.13.21H85.45c-.07,0-.13-.09-.13-.21В45.22c0-.12.06-.22.13-.22Zm0,39.6h8.81c.07,0,.13.1.13.21v5.71c0,.11-.06.22-.13.22H85.45c-.07,0-.13-.1-.13-.22В84.81c0-.11.06-.21.13-.21Zm-14.85,0h8.8c.08,0,.14.1.14.21v5.71c0,.11-.06.22-.14.22H70.6c-.08,0-.14-.1-.14-.22В84.81c0-.11.06-.21.14-.21ZM85.45,71.4h8.81c.07,0,.13.1.13.22v5.71c0,.11-.06.22-.13.22H85.45c-.07,0-.13-.1-.13-.22В71.62c0-.13.06-.22.13-.22Zm0-13.2h8.81c.07,0,.13.1.13.22v5.71c0,.11-.06.22-.13.22H85.45c-.07,0-.13-.1-.13-.22В58.42c0-.12.06-.22.13-.22ZM70.6,45h8.8c.08,0,.14.1.14.22v5.71c0,.1-.06.21-.14.21H70.6c-.08,0-.14-.09-.14-.21В45.22c0-.12.06-.22.14-.22Zm0,26.4h8.8c.08,0,.14.1.14.22v5.71c0,.11-.06.22-.14.22H70.6c-.08,0-.14-.1-.14-.22В71.62c0-.13.06-.22.14-.22Zm0-13.2h8.8c.08,0,.14.1.14.22v5.71c0,.11-.06.22-.14.22H70.6c-.08,0-.14-.1-.14-.22В58.42c0-.12.06-.22.14-.22ZM45.21,119.32H21.57В96.86H45.21в22.46ZM12.13,12.52h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H12.13a.28.28,0,0,1-.27-.27В12.79a.28.28,0,0,1,.27-.27Zm32.94,0h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H45.07a.28.28,0,0,1-.27-.27В12.79a.28.28,0,0,1,.27-.27Zm-16.47,0h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H28.6a.28.28,0,0,1-.27-.27В12.79a.28.28,0,0,1,.27-.27ZM12.13,33.28h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H12.13a.28.28,0,0,1-.27-.27В33.55a.28.28,0,0,1,.27-.27Zm32.94,0h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H45.07a.28.28,0,0,1-.27-.27В33.55a.28.28,0,0,1,.27-.27Zm-16.47,0h9.58a.28.28,0,0,1,.27.27v9.59a.28.28,0,0,1-.27.27H28.6a.28.28,0,0,1-.27-.27В33.55a.28.28,0,0,1,.27-.27ZM12.13,74.8h9.58a.27.27,0,0,1,.27.27v9.58a.27.27,0,0,1-.27.27H12.13a.27.27,0,0,1-.27-.27В75.07a.27.27,0,0,1,.27-.27Zm32.94,0h9.58a.27.27,0,0,1,.27.27v9.58a.27.27,0,0,1-.27.27H45.07a.27.27,0,0,1-.27-.27В75.07a.27.27,0,0,1,.27-.27Zm-16.47,0h9.58a.27.27,0,0,1,.27.27v9.58a.27.27,0,0,1-.27.27H28.6a.27.27,0,0,1-.27-.27В75.07a.27.27,0,0,1,.27-.27ZM12.13,54h9.58a.27.27,0,0,1,.27.27В63.9a.28.28,0,0,1-.27.27H12.13a.28.28,0,0,1-.27-.27В54.31a.27.27,0,0,1,.27-.27Zm32.94,0h9.58a.27.27,0,0,1,.27.27В63.9a.28.28,0,0,1-.27.27H45.07a.28.28,0,0,1-.27-.27В54.31a.27.27,0,0,1,.27-.27ZM28.6,54h9.58a.27.27,0,0,1,.27.27В63.9a.28.28,0,0,1-.27.27H28.6a.28.28,0,0,1-.27-.27В54.31A.27.27,0,0,1,28.6,54Z"/>
      </svg>
    </div>
  `
}
// Экземпляр карты и вспомогательные структуры
let mapInstance = null
let mapglApi = null
let boundsListener = null
let markers = []
let districtPolygons = []
let cachedDistricts = null // кэш координат после первой загрузки
let districtPopup = null
let heatMarkers = []
let inHeatmapDetail = false
let mapDistrictClickOff = null
let heatHitAreas = []
let cachedApartments = null
let allApartments = []
let selectedDistrictFeature = null
let facilityMarkers = []
let facilityLines = []
let heatClusters = []

// Читает центр карты из .env (VITE_MAP_CENTER) и нормализует порядок [lon,lat]
function parseEnvCenter() {
  const raw = import.meta.env.VITE_MAP_CENTER || ''
  const parts = raw.split(',').map((v) => Number(v.trim()))
  if (parts.length === 2 && parts.every((n) => Number.isFinite(n))) {
    const [a, b] = parts
    // If looks like [lat, lon], convert to [lon, lat]
    const looksLikeLatLon = Math.abs(a) <= 90 && Math.abs(b) <= 180 && Math.abs(b) > Math.abs(a)
    return looksLikeLatLon ? [b, a] : [a, b]
  }
  // Default: Moscow center [lon, lat]
  return [37.618423, 55.751244]
}

// Инициализация 2ГИС MapGL и установка ограничений (Москва)
onMounted(async () => {
  const apiKey = import.meta.env.VITE_DGIS_API_KEY
  if (!apiKey) {
    // eslint-disable-next-line no-console
    console.warn('VITE_DGIS_API_KEY не задан. Укажите ключ в .env.local')
  }

  mapglApi = await load()
  mapInstance = new mapglApi.Map(mapContainerRef.value, {
    key: apiKey,
    center: parseEnvCenter(),
    zoom: Number(import.meta.env.VITE_MAP_ZOOM || 13),
  })

  // Примерные границы Москвы (bbox) в формате [lon, lat]
  const moscowBounds = {
    northEast: [37.955, 55.917],
    southWest: [37.319, 55.561],
  }

  // Подгоняем вид к Москве
  try {
    mapInstance.fitBounds(moscowBounds)
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('fitBounds недоступен или произошла ошибка:', e)
  }

  // Ограничиваем выход за границы: возвращаем назад при выходе
  // Не даём «уезжать» за границы Москвы при перемещении
  const clampToBounds = () => {
    try {
      const center = mapInstance.getCenter()
      const [lon, lat] = center
      const minLon = moscowBounds.southWest[0]
      const maxLon = moscowBounds.northEast[0]
      const minLat = moscowBounds.southWest[1]
      const maxLat = moscowBounds.northEast[1]

      const clampedLon = Math.min(Math.max(lon, minLon), maxLon)
      const clampedLat = Math.min(Math.max(lat, minLat), maxLat)

      if (clampedLon !== lon || clampedLat !== lat) {
        mapInstance.setCenter([clampedLon, clampedLat])
      }
    } catch {
      // ignore
    }
  }

  boundsListener = mapInstance.on('moveend', clampToBounds)
  // Применим метки, если уже пришли
  addMarkersFromProps()
})

onBeforeUnmount(() => {
  if (boundsListener && typeof boundsListener === 'function') {
    boundsListener()
    boundsListener = null
  }
  if (mapInstance) {
    mapInstance.destroy()
    mapInstance = null
  }
})

// Удалить все маркеры квартир
function clearMarkers() {
  try {
    markers.forEach((m) => m && typeof m.destroy === 'function' && m.destroy())
  } catch {}
  markers = []
}

// Отрисовать входные точки (используется вне режима «районы»)
function addMarkersFromProps() {
  if (!mapInstance) return
  clearMarkers()
  if (!Array.isArray(props.points) || props.points.length === 0) return
  try {
    const bounds = { northEast: [-Infinity, -Infinity], southWest: [Infinity, Infinity] }
    props.points.forEach((p) => {
      if (typeof p?.longitude !== 'number' || typeof p?.latitude !== 'number') return
      if (mapglApi && mapglApi.HtmlMarker) {
        const marker = new mapglApi.HtmlMarker(mapInstance, {
          coordinates: [p.longitude, p.latitude],
          html: createApartmentMarkerHtml(),
        })
        markers.push(marker)
      } else {
        const marker = new mapglApi.Marker(mapInstance, {
          coordinates: [p.longitude, p.latitude],
          icon: APARTMENT_ICON,
          size: [40, 40],
        })
        markers.push(marker)
      }
      // expand bounds
      bounds.northEast[0] = Math.max(bounds.northEast[0], p.longitude)
      bounds.northEast[1] = Math.max(bounds.northEast[1], p.latitude)
      bounds.southWest[0] = Math.min(bounds.southWest[0], p.longitude)
      bounds.southWest[1] = Math.min(bounds.southWest[1], p.latitude)
    })
    if (isFinite(bounds.northEast[0]) && isFinite(bounds.southWest[0])) {
      try {
        // Добавляем внутренние отступы, чтобы метки были видны с запасом
        mapInstance.fitBounds(bounds, { padding: 64 })
        // Чуть уменьшаем зум для большего обзора
        const z = typeof mapInstance.getZoom === 'function' ? mapInstance.getZoom() : null
        if (z != null && typeof mapInstance.setZoom === 'function') {
          mapInstance.setZoom(Math.max(0, z - 0.5))
        }
      } catch {}
    }
  } catch {}
}

watch(() => props.points, () => {
  addMarkersFromProps()
}, { deep: true })

// --- РАЙОНЫ МОСКВЫ ИЗ GEOJSON ---
// Флаг режима «районы»
const districtsVisible = ref(false)

function clearDistricts() {
  try {
    districtPolygons.forEach((poly) => poly && typeof poly.destroy === 'function' && poly.destroy())
  } catch {}
  districtPolygons = []
}

// Загрузка GeoJSON с районами (mo.geojson в public)
async function loadDistrictsGeoJSON() {
  if (cachedDistricts) return cachedDistricts
  try {
    const res = await fetch('/mo.geojson', { cache: 'no-store' })
    if (!res.ok) throw new Error('Failed to load mo.geojson')
    const data = await res.json()
    cachedDistricts = data
    return data
  } catch (e) {
    console.warn('Не удалось загрузить mo.geojson. Поместите файл в папку public/', e)
    return null
  }
}

// Отрисовка одного района (Polygon/MultiPolygon) и подписка на клик → selectDistrict
function drawDistrictPolygonsFromFeature(feature) {
  if (!mapglApi || !mapInstance) return
  const geom = feature && feature.geometry
  if (!geom) return
  const style = {
    fillColor: 'rgba(29, 78, 216, 0.06)',
    strokeColor: 'rgba(29, 78, 216, 0.45)',
    strokeWidth: 2,
    zIndex: 10,
  }
  const title = (feature && feature.properties && (feature.properties.name || feature.properties.NAME || feature.properties.Name)) || 'Район'
  const centroid = getGeometryCentroid(geom)
  try {
    if (geom.type === 'Polygon') {
      // coordinates: [ [ [lon,lat], ... ] , [hole] ...]
      const poly = new mapglApi.Polygon(mapInstance, {
        coordinates: geom.coordinates,
        ...style,
      })
      districtPolygons.push(poly)
      poly.on('click', () => selectDistrict(feature))
    } else if (geom.type === 'MultiPolygon') {
      geom.coordinates.forEach((polyCoords) => {
        const poly = new mapglApi.Polygon(mapInstance, {
          coordinates: polyCoords,
          ...style,
        })
        districtPolygons.push(poly)
        poly.on('click', () => selectDistrict(feature))
      })
    }
  } catch (e) {
    console.warn('Ошибка рисования полигона:', e)
  }
}

function getEventCoords(e) {
  if (!e) return null
  // Пытаемся взять координаты клика из события, иначе null
  if (Array.isArray(e.coordinates)) return e.coordinates
  if (Array.isArray(e.lngLat)) return e.lngLat
  return null
}

// Центроид геометрии района (для попапа по клику вне полигонов)
function getGeometryCentroid(geom) {
  try {
    if (geom.type === 'Polygon') {
      return ringCentroid(geom.coordinates[0] || [])
    }
    if (geom.type === 'MultiPolygon') {
      const rings = geom.coordinates.map((poly) => poly[0] || [])
      const largest = rings.sort((a, b) => b.length - a.length)[0] || []
      return ringCentroid(largest)
    }
  } catch {}
  return mapInstance ? mapInstance.getCenter() : [37.618423, 55.751244]
}

function ringCentroid(ring) {
  if (!Array.isArray(ring) || ring.length === 0) return null
  let sx = 0, sy = 0
  ring.forEach((p) => { sx += p[0]; sy += p[1] })
  return [sx / ring.length, sy / ring.length]
}

function showDistrictPopup(coords, title) {
  try { if (districtPopup && typeof districtPopup.destroy === 'function') districtPopup.destroy() } catch {}
  districtPopup = new mapglApi.HtmlMarker(mapInstance, {
    coordinates: coords,
    html: `<div class="district-popup">${escapeHtml(String(title))}</div>`,
  })
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

// Определение района кликом по карте (геометрическая проверка)
function pointInRing(point, ring) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1]
    const xj = ring[j][0], yj = ring[j][1]
    const intersect = ((yi > point[1]) !== (yj > point[1])) &&
      (point[0] < ((xj - xi) * (point[1] - yi)) / ((yj - yi) || 1e-9) + xi)
    if (intersect) inside = !inside
  }
  return inside
}

function pointInPolygon(point, polygon) {
  const [outer, ...holes] = polygon
  if (!pointInRing(point, outer)) return false
  for (const hole of holes) {
    if (pointInRing(point, hole)) return false
  }
  return true
}

function pointInMultiPolygon(point, multiPoly) {
  for (const poly of multiPoly) {
    if (pointInPolygon(point, poly)) return true
  }
  return false
}

function findDistrictByPoint(point) {
  const gj = cachedDistricts
  if (!gj || !Array.isArray(gj.features)) return null
  for (const f of gj.features) {
    const g = f.geometry
    if (!g) continue
    if (g.type === 'Polygon') {
      if (pointInPolygon(point, g.coordinates)) return f
    } else if (g.type === 'MultiPolygon') {
      if (pointInMultiPolygon(point, g.coordinates)) return f
    }
  }
  return null
}

// Границы геометрии района в формате fitBounds { northEast: [lon,lat], southWest: [lon,lat] }
function geometryBounds(geom) {
  if (!geom) return null
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity
  const update = (lon, lat) => {
    if (!Number.isFinite(lon) || !Number.isFinite(lat)) return
    if (lon < minLon) minLon = lon
    if (lon > maxLon) maxLon = lon
    if (lat < minLat) minLat = lat
    if (lat > maxLat) maxLat = lat
  }
  const walk = (v) => {
    if (!v) return
    if (Array.isArray(v)) {
      if (v.length >= 2 && typeof v[0] === 'number' && typeof v[1] === 'number') {
        update(v[0], v[1])
      } else {
        for (const u of v) walk(u)
      }
    }
  }
  if (geom.type === 'Polygon') walk(geom.coordinates)
  else if (geom.type === 'MultiPolygon') walk(geom.coordinates)
  if (!isFinite(minLon) || !isFinite(minLat) || !isFinite(maxLon) || !isFinite(maxLat)) return null
  return { northEast: [maxLon, maxLat], southWest: [minLon, minLat] }
}

// Фильтрация квартир по выбранному району
function filterApartmentsByDistrict(apts, feature) {
  const g = feature && feature.geometry
  if (!g) return Array.isArray(apts) ? apts : []
  const inPoly = (pt) => g.type === 'Polygon' ? pointInPolygon(pt, g.coordinates)
    : g.type === 'MultiPolygon' ? pointInMultiPolygon(pt, g.coordinates) : true
  const src = Array.isArray(apts) ? apts : []
  const out = []
  for (const p of src) {
    const pt = [p.longitude, p.latitude]
    if (inPoly(pt)) out.push(p)
  }
  return out
}

// Обработчик клика по карте в режиме «районы»:
// - если кликнули по району → selectDistrict
// - иначе пробуем попасть в облако кластера
function attachMapDistrictClick() {
  if (!mapInstance || mapDistrictClickOff) return
  mapDistrictClickOff = mapInstance.on('click', (e) => {
    if (!districtsVisible.value) return
    let coords = (e && (e.lngLat || e.coordinates)) || null
    if (!coords && e && e.point && typeof mapInstance.unproject === 'function') {
      try { coords = mapInstance.unproject(e.point) } catch {}
    }
    if (!coords) return
    // eslint-disable-next-line no-console
    console.log('Map click in district mode', { coords })
    const feat = findDistrictByPoint(coords)
    if (feat) {
      // eslint-disable-next-line no-console
      console.log('District found by point, selecting')
      selectDistrict(feat)
      return
    }
    // Если клик не по району — разрешаем клик по кластеру только после выбора района
    if (!selectedDistrictFeature) return
    const hit = hitHeatCluster(coords)
    if (hit) revealCluster(hit)
  })
}

function detachMapDistrictClick() {
  if (mapDistrictClickOff && typeof mapDistrictClickOff === 'function') {
    mapDistrictClickOff()
    mapDistrictClickOff = null
  }
}

// Включить режим «районы»: отрисовать районы, загрузить квартиры и построить теплокарту
async function showDistricts() {
  districtsVisible.value = true
  clearDistricts()
  const gj = await loadDistrictsGeoJSON()
  if (!gj) return
  // Отображаем полигоны районов
  try {
    const feats = Array.isArray(gj.features) ? gj.features : []
    feats.forEach(drawDistrictPolygonsFromFeature)
  } catch {}
  // Скрываем обычные метки и включаем тепловую карту по данным из JSON
  clearMarkers()
  inHeatmapDetail = false
  selectedDistrictFeature = null
  const apartments = await loadApartmentsFromJson()
  allApartments = apartments
  renderApartmentsHeatmap(allApartments, { allowClusterClicks: false })
  attachMapDistrictClick()
}

// Выключить режим «районы» и вернуть исходные точки
function hideDistricts() {
  clearDistricts()
  try { if (districtPopup && typeof districtPopup.destroy === 'function') districtPopup.destroy() } catch {}
  districtPopup = null
  clearHeatmap()
  // Вернём обычные маркеры, если есть входные точки
  addMarkersFromProps()
  detachMapDistrictClick()
}

async function toggleDistricts() {
  districtsVisible.value = !districtsVisible.value
  if (districtsVisible.value) await showDistricts(); else hideDistricts()
}

// Экспортируем публичные методы для родителя
defineExpose({
  showDistricts,
  hideDistricts,
  backToDistrictClusters,
  setFilters,
})

// --- ТЕПЛОВАЯ КАРТА (моки для Хамовников) ---
// Очистка теплокарты (облака и хит-зоны)
function clearHeatmap() {
  try { heatMarkers.forEach((m) => m && typeof m.destroy === 'function' && m.destroy()) } catch {}
  heatMarkers = []
  try { heatHitAreas.forEach((p) => p && typeof p.destroy === 'function' && p.destroy()) } catch {}
  heatHitAreas = []
}

// Очистка маркеров объектов и линий до них
function clearFacilities() {
  try { facilityMarkers.forEach((m) => m && typeof m.destroy === 'function' && m.destroy()) } catch {}
  facilityMarkers = []
  try { facilityLines.forEach((l) => l && typeof l.destroy === 'function' && l.destroy()) } catch {}
  facilityLines = []
}

// Мок-генератор квартир для дев-режима (если нет JSON)
function buildHamovnikiMock() {
  // Координаты вокруг Хамовников (примерно центр района)
  const base = { lon: 37.580, lat: 55.735 }
  const jitter = (n) => (Math.random() - 0.5) * n
  const qualities = ['good', 'medium', 'bad']
  const result = []
  const total = 16
  for (let i = 0; i < total; i += 1) {
    const q = i < 7 ? 'good' : i < 12 ? 'medium' : 'bad'
    result.push({
      longitude: base.lon + jitter(0.015),
      latitude: base.lat + jitter(0.01),
      quality: q,
      nearest_objects: {
        nearest_kindergartens: [{ distance: 300 + Math.random() * 400 }],
        nearest_child_hospitals: [{ distance: 400 + Math.random() * 800 }],
        nearest_parks: [{ distance: 250 + Math.random() * 700 }],
      },
    })
  }
  return result
}

// Простая «кластеризация по сетке» — объединяем близкие квартиры, считаем центр
function clusterApartments(apts, thresholdDeg = 0.0045) {
  const clusters = []
  apts.forEach((p) => {
    let found = null
    for (const c of clusters) {
      const dx = p.longitude - c.center[0]
      const dy = p.latitude - c.center[1]
      if (Math.abs(dx) + Math.abs(dy) < thresholdDeg) { found = c; break }
    }
    if (!found) {
      found = { points: [], center: [p.longitude, p.latitude] }
      clusters.push(found)
    }
    found.points.push(p)
    // пересчёт центра
    const n = found.points.length
    found.center = [
      (found.center[0] * (n - 1) + p.longitude) / n,
      (found.center[1] * (n - 1) + p.latitude) / n,
    ]
  })
  return clusters
}

// Выбор цвета кластера. Условие:
// green  — медиана расстояний по 3 типам ≤ 1000 м
// orange — медиана расстояний по 3 типам ≤ 2000 м (и не green)
// red    — иначе
function colorForCluster(points) {
  // Правило: зелёный, если по КАЖДОМУ типу объектов медианная дистанция ≤ 1000 м
  // оранжевый: если по каждому ≤ 2000 м (и не зелёный), иначе красный
  const kids = []
  const hosps = []
  const parks = []
  for (const p of points) {
    const d = getDistances(p)
    if (Number.isFinite(d.kindergarten)) kids.push(d.kindergarten)
    if (Number.isFinite(d.hospital)) hosps.push(d.hospital)
    if (Number.isFinite(d.park)) parks.push(d.park)
  }
  const mk = median(kids)
  const mh = median(hosps)
  const mp = median(parks)
  if (mk <= 1000 && mh <= 1000 && mp <= 1000) return 'green'
  if (mk <= 2000 && mh <= 2000 && mp <= 2000) return 'orange'
  return 'red'
}

// Извлечение расстояний по каждому типу объектов из nearest_objects одной квартиры
function getDistances(p) {
  const no = p.nearest_objects || p.nearest || {}
  return {
    kindergarten: firstDistance(no.nearest_kindergartens),
    hospital: firstDistance(no.nearest_child_hospitals || no.nearest_child_polyclinics),
    park: firstDistance(no.nearest_parks),
  }
}

function firstDistance(arr) {
  if (!arr || !arr.length) return Infinity
  const d = Number(arr[0]?.distance)
  return Number.isFinite(d) ? d : Infinity
}

function median(values) {
  if (!values || values.length === 0) return Infinity
  const arr = values.slice().sort((a, b) => a - b)
  const mid = Math.floor(arr.length / 2)
  return arr.length % 2 ? arr[mid] : (arr[mid - 1] + arr[mid]) / 2
}

// Построение теплокарты по массиву квартир: считаем кластера,
// строим облака и создаём кликабельные хит-зоны
function renderApartmentsHeatmap(apartments, options) {
  clearHeatmap()
  const data = Array.isArray(apartments) ? apartments : []
  const clusters = clusterApartments(data)
  heatClusters = []
  const allowClusterClicks = !!(options && options.allowClusterClicks)
  clusters.forEach((c) => {
    const color = colorForCluster(c.points)
    const radiusMeters = 280 // базовый радиус для fallback-хиттеста
    heatClusters.push({ ...c, color, radiusMeters })
    // Построим «облако» кластера как сглаженную выпуклую оболочку
    const cloudRing = buildClusterCloudPolygon(c)
    if (cloudRing && cloudRing.length >= 4) {
      try {
        const hitPoly = new mapglApi.Polygon(mapInstance, {
          coordinates: [cloudRing],
          fillColor: fillColorForHeat(color),
          strokeColor: strokeColorForHeat(color),
          strokeWidth: 2,
          zIndex: 200,
        })
        if (allowClusterClicks) {
          hitPoly.on('click', () => revealCluster(c))
        }
        heatHitAreas.push(hitPoly)
      } catch {}
    }
  })
}

// Выбор района: зум к району, фильтрация квартир по геометрии, перестроение теплокарты
function selectDistrict(feature) {
  selectedDistrictFeature = feature
  // Fit to district bounds
  try {
    const b = geometryBounds(feature.geometry)
    // eslint-disable-next-line no-console
    console.log('Select district -> fitBounds', { bounds: b })
    if (b) mapInstance.fitBounds(b, { padding: 48 })
  } catch {}
  const filtered = filterApartmentsByDistrict(allApartments, feature)
  renderApartmentsHeatmap(filtered, { allowClusterClicks: true })
  try {
    const name = (feature && feature.properties && (feature.properties.name || feature.properties.NAME || feature.properties.Name)) || 'Район'
    emit('district-selected', { name, feature, apartments: filtered })
  } catch {}
}

// Загрузка квартир из public/appartments.json. Поддерживаются разные форматы полей.
// Текущие фильтры (устанавливаются из App.vue)
let activeFilters = { minPrice: null, maxPrice: null, rooms: null }
function setFilters(filters) {
  activeFilters = {
    minPrice: (filters && Number.isFinite(filters.minPrice)) ? Number(filters.minPrice) : null,
    maxPrice: (filters && Number.isFinite(filters.maxPrice)) ? Number(filters.maxPrice) : null,
    rooms: Array.isArray(filters && filters.rooms) && filters.rooms.length ? filters.rooms.map((n) => Number(n)).filter((n) => Number.isFinite(n)) : null,
    // TODO(age-filter): включить флаг из квиза, чтобы при возрасте 0-7 лет не фильтровать вовсе
    // ignoreAllByAge07: filters && filters.ignoreAllByAge07 === true,
  }
}

function applyFilters(apts) {
  const arr = Array.isArray(apts) ? apts : []
  // TODO(age-filter): если в анкетах детей выбран возраст "0-7 лет",
  // то возвращать весь JSON без дополнительных фильтров по цене/комнатам.
  // Пример интеграции:
  // if (activeFilters && activeFilters.ignoreAllByAge07 === true) {
  //   return arr
  // }
  return arr.filter((ap) => {
    // Если активен фильтр по цене, отбрасываем записи без валидной цены
    const priceActive = activeFilters.minPrice != null || activeFilters.maxPrice != null
    const hasPrice = Number.isFinite(ap.price)
    if (priceActive && !hasPrice) return false
    if (activeFilters.minPrice != null && Number.isFinite(ap.price)) {
      if (ap.price < activeFilters.minPrice) return false
    }
    if (activeFilters.maxPrice != null && Number.isFinite(ap.price)) {
      if (ap.price > activeFilters.maxPrice) return false
    }
    if (activeFilters.rooms && activeFilters.rooms.length) {
      const r = Number(ap.rooms)
      const wanted = new Set(activeFilters.rooms)
      // Интерпретация: значение 3 в фильтре означает "3 и более"
      const match = (wanted.has(1) && r === 1) || (wanted.has(2) && r === 2) || (wanted.has(3) && r >= 3)
      if (!match) return false
    }
    return true
  })
}

async function loadApartmentsFromJson() {
  // При наличии кэша всегда возвращаем массив с повторным применением фильтров
  if (cachedApartments) return applyFilters(cachedApartments)
  try {
    const res = await fetch('/appartments.json', { cache: 'no-store' })
    if (!res.ok) throw new Error('Failed to load appartments.json')
    const json = await res.json()
    const arr = Array.isArray(json) ? json : Array.isArray(json?.items) ? json.items : []
    // Вспомогательные функции проверки структуры координат
    const collectPoints = (v, out) => {
      if (!v) return
      if (Array.isArray(v)) {
        if (v.length >= 2 && typeof v[0] === 'number' && typeof v[1] === 'number') {
          const x = Number(v[0]); const y = Number(v[1])
          if (Number.isFinite(x) && Number.isFinite(y)) out.push([x, y])
        } else {
          for (const u of v) collectPoints(u, out)
        }
      } else if (typeof v === 'object' && 'lon' in v && 'lat' in v) {
        const x = Number(v.lon); const y = Number(v.lat)
        if (Number.isFinite(x) && Number.isFinite(y)) out.push([x, y])
      }
    }
    const hasSinglePoint = (entry) => {
      if (!entry || !entry.coordinates) return false
      const pts = []
      collectPoints(entry.coordinates, pts)
      return pts.length === 1
    }
    const firstPoint = (entry) => {
      if (!entry || !entry.coordinates) return null
      const pts = []
      collectPoints(entry.coordinates, pts)
      return pts[0] || null
    }
    const normalizeNearestObjects = (no) => {
      if (!no) return null
      const out = { ...no }
      if (Array.isArray(out.nearest_parks)) {
        out.nearest_parks = out.nearest_parks.map((e) => {
          const fp = firstPoint(e)
          if (fp) {
            return { ...e, coordinates: [ [ fp[0], fp[1] ] ] }
          }
          return e
        })
      }
      return out
    }
    // Парсер цены: извлекает число из строк вида "90 000 ₽"/"90,000"
    const parsePrice = (v) => {
      if (v == null) return NaN
      if (typeof v === 'number') return v
      if (typeof v === 'string') {
        const digits = v.replace(/[^0-9.,]/g, '').replace(/,/g, '')
        const n = Number(digits)
        return Number.isFinite(n) ? n : NaN
      }
      return NaN
    }

    cachedApartments = arr
      .map((it) => {
        const lat = Number(it.latitude ?? it.lat)
        const lon = Number(it.longitude ?? it.lon ?? it.lng)
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null
        const rawNO = it.nearest_objects ?? it.nearest ?? null
        const nearest_objects = normalizeNearestObjects(rawNO)
        return {
          latitude: lat,
          longitude: lon,
          nearest_objects,
          id: it.id ?? null,
          title: it.title ?? null,
          url: it.url ?? null,
          price: parsePrice(it.price ?? it.price_per_month ?? it.rent ?? null),
          area: Number(it.area ?? NaN),
          rooms: it.rooms ?? null,
          room_type: it.room_type ?? null,
          address: it.address ?? null,
          floor: it.floor ?? null,
          total_floors: it.total_floors ?? null,
          metro: it.metro ?? null,
          metro_time: it.metro_time ?? null,
          build_year: it.build_year ?? null,
          description: it.description ?? null,
        }
      })
      .filter(Boolean)
    // применим фильтры при чтении
    return applyFilters(cachedApartments)
  } catch (e) {
    console.warn('Не удалось загрузить appartments.json. Использую моковые данные.', e)
    return buildHamovnikiMock()
  }
}

// Клик по «облаку»: переход в детализацию — точки квартир + объекты и линии
function revealCluster(cluster) {
  // При клике на область — приближаем и показываем точки этого кластера
  inHeatmapDetail = true
  clearHeatmap()
  clearMarkers()
  clearFacilities()
  try { mapInstance.setCenter(cluster.center) } catch {}
  try {
    const z = typeof mapInstance.getZoom === 'function' ? mapInstance.getZoom() : 13
    if (typeof mapInstance.setZoom === 'function') mapInstance.setZoom(Math.max(13, z + 1.5))
  } catch {}
  // Показать маркеры квартир из кластера
  try {
    cluster.points.forEach((p) => {
      const marker = new mapglApi.HtmlMarker(mapInstance, {
        coordinates: [p.longitude, p.latitude],
        html: createApartmentMarkerHtml(),
        zIndex: 290,
      })
      markers.push(marker)
    })
  } catch {}

  // Отрисуем заведения (детсад, дет.поликлиника, парк) и линии расстояний
  try {
    drawFacilitiesForCluster(cluster)
  } catch {}
  try { emit('cluster-selected', { center: cluster.center, apartments: cluster.points }) } catch {}
}

// Вернуться к виду кластера района (очистить детали)
function backToDistrictClusters() {
  if (!selectedDistrictFeature) return
  inHeatmapDetail = false
  clearFacilities()
  clearMarkers()
  clearHeatmap()
  const filtered = filterApartmentsByDistrict(allApartments, selectedDistrictFeature)
  renderApartmentsHeatmap(filtered, { allowClusterClicks: true })
}

// Рисуем маркеры объектов (сад/поликлиника/парк) и линии до них для выбранного кластера
function drawFacilitiesForCluster(cluster) {
  if (!mapglApi || !mapInstance) return
  const dedupe = new Set()
  const addFacility = (type, coord, distanceMeters, fromCoord) => {
    if (!coord) return
    const key = `${type}:${coord[0].toFixed(6)},${coord[1].toFixed(6)}|from:${fromCoord ? fromCoord[0].toFixed(6)+','+fromCoord[1].toFixed(6) : 'na'}`
    if (dedupe.has(key)) return
    dedupe.add(key)
    const icon = type === 'kindergarten' ? '🧒' : (type === 'hospital' ? '🏥' : '🌳')
    const el = `<div class=\"facility-marker facility-${type}\"><span class=\"facility-marker__icon\">${icon}</span><span class=\"facility-marker__badge\">${distanceMeters ? Math.round(distanceMeters) : ''}м</span></div>`
    const fm = new mapglApi.HtmlMarker(mapInstance, { coordinates: coord, html: el, zIndex: 300 })
    facilityMarkers.push(fm)
  }

  // Извлечь одиночную координату объекта. Если координат несколько — игнорируем (вернём null).
  const coordCentroid = (entry, fallbackFrom, fallbackDistance) => {
    if (!entry) return null
    const coords = entry.coordinates
    if (!coords) return null
    const pts = []
    const pushPoint = (v) => {
      if (Array.isArray(v) && v.length >= 2 && typeof v[0] === 'number' && typeof v[1] === 'number') {
        const lon = Number(v[0])
        const lat = Number(v[1])
        if (Number.isFinite(lon) && Number.isFinite(lat)) pts.push([lon, lat])
      }
    }
    const walk = (v) => {
      if (!v) return
      if (Array.isArray(v)) {
        if (v.length >= 2 && typeof v[0] === 'number' && typeof v[1] === 'number') {
          pushPoint(v)
        } else {
          for (const u of v) walk(u)
        }
      } else if (typeof v === 'object' && 'lon' in v && 'lat' in v) {
        pushPoint([v.lon, v.lat])
      }
    }
    walk(coords)
    if (pts.length !== 1) return null
    return pts[0]
  }

  // Линия от точки А к точке Б (поверх всех слоёв)
  const makeLine = (from, to, color) => {
    if (!from || !to) return
    try {
      const line = new mapglApi.Polyline(mapInstance, {
        coordinates: [from, to],
        color: color || '#6B7280',
        width: 4,
        zIndex: 320,
      })
      facilityLines.push(line)
    } catch {}
  }

  const colorForType = (t) => (t === 'kindergarten' ? '#22c55e' : t === 'hospital' ? '#0ea5e9' : '#f59e0b')

  // Выбираем по одному объекту каждого типа для всего кластера
  const selectOnePerType = () => {
    const result = {}
    const defs = [
      { key: 'kindergarten', arrKey: 'nearest_kindergartens', bearing: 45 },
      { key: 'hospital', arrKey: 'nearest_child_hospitals', altArrKey: 'nearest_child_polyclinics', bearing: 90 },
      { key: 'park', arrKey: 'nearest_parks', bearing: 135 },
    ]
    defs.forEach((def) => {
      let best = null
      for (const p of cluster.points) {
        const no = p.nearest_objects || p.nearest || {}
        let list = Array.isArray(no[def.arrKey]) ? no[def.arrKey] : []
        if (def.altArrKey && Array.isArray(no[def.altArrKey])) list = list.concat(no[def.altArrKey])
        for (const e of list) {
          const coord = coordCentroid(e)
          const dist = Number(e && e.distance)
          if (coord && Number.isFinite(dist)) {
            if (!best || dist < best.distance) best = { coord, distance: dist, source: 'exact' }
          }
        }
      }
      if (!best) {
        // fallback: используем медиану дистанций по кластеру и проецируем от центра кластера
        const dsArr = []
        for (const p of cluster.points) {
          const ds = getDistances(p)
          const d = def.key === 'kindergarten' ? ds.kindergarten : def.key === 'hospital' ? ds.hospital : ds.park
          if (Number.isFinite(d)) dsArr.push(d)
        }
        const md = median(dsArr)
        if (Number.isFinite(md) && md !== Infinity) {
          const proj = projectFrom(cluster.center, md, def.bearing)
          if (proj) best = { coord: proj, distance: md, source: 'fallback' }
        }
      }
      result[def.key] = best
    })
    return result
  }

  const selected = selectOnePerType()
  const from = cluster.center
  // eslint-disable-next-line no-console
  console.log('Cluster facility routes', {
    from: { lon: from && from[0], lat: from && from[1] },
    kindergarten: selected.kindergarten ? { lon: selected.kindergarten.coord[0], lat: selected.kindergarten.coord[1], distance: selected.kindergarten.distance, source: selected.kindergarten.source } : null,
    hospital: selected.hospital ? { lon: selected.hospital.coord[0], lat: selected.hospital.coord[1], distance: selected.hospital.distance, source: selected.hospital.source } : null,
    park: selected.park ? { lon: selected.park.coord[0], lat: selected.park.coord[1], distance: selected.park.distance, source: selected.park.source } : null,
  })
  ;(['kindergarten', 'hospital', 'park']).forEach((t) => {
    const item = selected[t]
    if (item && item.coord) {
      addFacility(t, item.coord, item.distance, from)
      makeLine(from, item.coord, colorForType(t))
    }
  })
}

// Fallback‑проекция от исходной точки на заданную дистанцию по азимуту,
// если у объекта нет точных координат
function projectFrom(fromLonLat, distanceMeters, bearingDeg) {
  if (!fromLonLat || !Number.isFinite(distanceMeters)) return null
  const [lon, lat] = fromLonLat
  const latRad = (lat * Math.PI) / 180
  const metersPerDegLat = 111132.954 - 559.822 * Math.cos(2 * latRad) + 1.175 * Math.cos(4 * latRad)
  const metersPerDegLon = (Math.PI / 180) * 6378137 * Math.cos(latRad)
  const br = ((bearingDeg ?? 0) * Math.PI) / 180
  const dx = (Math.cos(br) * distanceMeters) / metersPerDegLon
  const dy = (Math.sin(br) * distanceMeters) / metersPerDegLat
  return [lon + dx, lat + dy]
}

function shortenToMarker(fromLonLat, toLonLat, pixelRadius) {
  // Укорачиваем конец линии, чтобы она не заходила под круглый маркер
  try {
    const map = mapInstance
    if (!map || !map.project || !map.unproject) return null
    const fromPx = map.project(fromLonLat)
    const toPx = map.project(toLonLat)
    const dx = toPx[0] - fromPx[0]
    const dy = toPx[1] - fromPx[1]
    const len = Math.hypot(dx, dy)
    if (!len || !isFinite(len)) return null
    const ratio = Math.max(0, (len - (pixelRadius ?? 20)) / len)
    const adj = [fromPx[0] + dx * ratio, fromPx[1] + dy * ratio]
    return map.unproject(adj)
  } catch {
    return null
  }
}

// Попадание клика в область одного из теплокластеров (по радиусу)
function hitHeatCluster(coord) {
  if (!Array.isArray(heatClusters) || heatClusters.length === 0) return null
  for (const c of heatClusters) {
    const d = distanceMeters(coord, c.center)
    if (d <= (c.radiusMeters || 600)) return c
  }
  return null
}

// Геодезическое расстояние (приближённо, формула haversine)
function distanceMeters(a, b) {
  const toRad = (x) => (x * Math.PI) / 180
  const R = 6378137
  const dLat = toRad((b[1] ?? 0) - (a[1] ?? 0))
  const dLon = toRad((b[0] ?? 0) - (a[0] ?? 0))
  const lat1 = toRad(a[1] ?? 0)
  const lat2 = toRad(b[1] ?? 0)
  const sinDlat = Math.sin(dLat / 2)
  const sinDlon = Math.sin(dLon / 2)
  const h = sinDlat * sinDlat + Math.cos(lat1) * Math.cos(lat2) * sinDlon * sinDlon
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)))
}

// Вспомогательный «круг» как полигон для ореолов/хитов
function createCirclePolygon(center, radiusMeters, steps = 36) {
  const [lon, lat] = center
  const res = []
  const latRad = (lat * Math.PI) / 180
  const metersPerDegLat = 111132.954 - 559.822 * Math.cos(2 * latRad) + 1.175 * Math.cos(4 * latRad)
  const metersPerDegLon = (Math.PI / 180) * 6378137 * Math.cos(latRad)
  const dLat = radiusMeters / metersPerDegLat
  const dLon = radiusMeters / metersPerDegLon
  for (let i = 0; i < steps; i += 1) {
    const a = (i / steps) * Math.PI * 2
    const x = lon + Math.cos(a) * dLon
    const y = lat + Math.sin(a) * dLat
    res.push([x, y])
  }
  res.push(res[0])
  return res
}

// ---------- Heat cloud geometry helpers ----------
// Цвет заливки облака по категории
function fillColorForHeat(kind) {
  if (kind === 'green') return 'rgba(16,185,129,0.42)'
  if (kind === 'orange') return 'rgba(245,158,11,0.42)'
  return 'rgba(239,68,68,0.42)'
}

// Цвет обводки облака по категории
function strokeColorForHeat(kind) {
  if (kind === 'green') return 'rgba(16,185,129,0.6)'
  if (kind === 'orange') return 'rgba(245,158,11,0.6)'
  return 'rgba(239,68,68,0.6)'
}

// Построение «облака» кластера:
// 1) выпуклая оболочка → 2) «раздувание» от центроида → 3) сглаживание Chaikin
// Fallback — суперэллипс, если точек мало
function buildClusterCloudPolygon(cluster) {
  const pts = (cluster.points || []).map((p) => [p.longitude, p.latitude])
  if (pts.length >= 3) {
    const hull = convexHull(pts)
    if (hull && hull.length >= 3) {
      const centroid = ringCentroid(hull)
      const meanDist = meanDistanceMeters(cluster.points, centroid)
      const count = cluster.points.length
      // Масштаб облака от количества и средней удалённости точек
      const scale = clamp(1 + 0.015 * count + meanDist * 0.0006, 1.08, 1.9)
      const inflated = hull.map(([x, y]) => [centroid[0] + (x - centroid[0]) * scale, centroid[1] + (y - centroid[1]) * scale])
      const smoothIter = count > 10 ? 2 : 1
      const smoothed = chaikinSmooth(inflated, smoothIter)
      smoothed.push(smoothed[0])
      return smoothed
    }
  }
  // Fallback без круга: суперэллипс (squircle) с разными осями, чтобы не было ощущения «радиуса»
  const [lon, lat] = cluster.center
  const latRad = (lat * Math.PI) / 180
  const metersPerDegLat = 111132.954 - 559.822 * Math.cos(2 * latRad) + 1.175 * Math.cos(4 * latRad)
  const metersPerDegLon = (Math.PI / 180) * 6378137 * Math.cos(latRad)
  const avgDist = meanDistanceMeters(cluster.points, [lon, lat]) || 160
  const count = (cluster.points || []).length
  const rMeters = clamp(avgDist * (1 + 0.03 * count), 140, 520)
  const rx = (rMeters * 1.4) / metersPerDegLon
  const ry = (rMeters * 0.8) / metersPerDegLat
  const n = 2.5 // степень суперэллипса
  const steps = 28
  const ring = []
  for (let i = 0; i < steps; i += 1) {
    const t = (i / steps) * Math.PI * 2
    const ct = Math.cos(t)
    const st = Math.sin(t)
    const x = lon + Math.sign(ct) * Math.pow(Math.abs(ct), 2 / n) * rx
    const y = lat + Math.sign(st) * Math.pow(Math.abs(st), 2 / n) * ry
    ring.push([x, y])
  }
  ring.push(ring[0])
  return ring
}

// Средняя дистанция от центроида до квартир (для масштабирования облака)
function meanDistanceMeters(points, centerLonLat) {
  if (!points || points.length === 0) return 0
  const [clon, clat] = centerLonLat
  let sum = 0
  for (const p of points) {
    sum += distanceMeters([clon, clat], [p.longitude, p.latitude])
  }
  return sum / points.length
}

function clamp(v, min, max) { return Math.max(min, Math.min(max, v)) }

// Выпуклая оболочка (монотонная цепь)
function convexHull(points) {
  // Monotone chain; works on [x,y] lon/lat
  const pts = [...points]
  pts.sort((a, b) => (a[0] === b[0] ? a[1] - b[1] : a[0] - b[0]))
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
  const lower = []
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop()
    lower.push(p)
  }
  const upper = []
  for (let i = pts.length - 1; i >= 0; i -= 1) {
    const p = pts[i]
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop()
    upper.push(p)
  }
  upper.pop(); lower.pop()
  const hull = lower.concat(upper)
  if (hull.length) hull.push(hull[0])
  return hull
}

// Сглаживание контура облака (Chaikin's corner cutting)
function chaikinSmooth(ring, iterations = 1) {
  let pts = [...ring]
  for (let k = 0; k < iterations; k += 1) {
    const out = []
    for (let i = 0; i < pts.length - 1; i += 1) {
      const p0 = pts[i]
      const p1 = pts[i + 1]
      const Q = [p0[0] * 0.75 + p1[0] * 0.25, p0[1] * 0.75 + p1[1] * 0.25]
      const R = [p0[0] * 0.25 + p1[0] * 0.75, p0[1] * 0.25 + p1[1] * 0.75]
      out.push(Q, R)
    }
    // закрываем
    out.push(out[0])
    pts = out
  }
  return pts
}
</script>

<template>
  <div ref="mapContainerRef" class="map-root">
    <!-- <button class="map-toggle" @click="toggleDistricts">{{ districtsVisible ? 'Скрыть районы' : 'Показать районы' }}</button> -->
  </div>
  
</template>

<style scoped>
.map-root {
  width: 100%;
  height: 100%;
  position: relative;
}

.map-toggle {
  position: absolute;
  right: 12px;
  top: 12px;
  z-index: 5;
  background: #ffffff;
  color: #1f2937;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 8px 12px;
  font-weight: 700;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
}
</style>


