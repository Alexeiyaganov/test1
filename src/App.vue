<script setup>
import MapView from './components/MapView.vue'
import BottomSheet from './components/BottomSheet.vue'
import QuizModal from './components/QuizModal.vue'
import { ref, onMounted } from 'vue'
// Слушаем применение фильтров из FiltersModal
const lastFilters = ref({ minPrice: null, maxPrice: null, rooms: [] })
if (typeof window !== 'undefined') {
  window.addEventListener('filters-apply', (e) => {
    const f = e && e.detail
    lastFilters.value = f || { minPrice: null, maxPrice: null, rooms: [] }
    try { mapRef.value && mapRef.value.setFilters && mapRef.value.setFilters(lastFilters.value) } catch {}
    try { mapRef.value && mapRef.value.showDistricts && mapRef.value.showDistricts() } catch {}
    // дополним выбранный район метаданными фильтров для префилла в шторке
    if (selectedDistrict.value) selectedDistrict.value = { ...selectedDistrict.value, filters: lastFilters.value }
  })
}

const quizOpen = ref(false)
const mapPoints = ref([])
const districtStats = ref(null)
const selectedPriorityId = ref(null)
const sheetRef = ref(null)
const mapRef = ref(null)
function onPickArea() {
  quizOpen.value = true
}

async function onQuizComplete(payload) {
  quizOpen.value = false
  // свернуть нижнюю панель полностью
  try { sheetRef.value && sheetRef.value.collapseFully && sheetRef.value.collapseFully() } catch {}
  // Запускаем режим районов с теплокартой по данным из JSON
  selectedPriorityId.value = Array.isArray(payload?.priorities) && payload.priorities.length ? payload.priorities[0].id : null
  lastFilters.value = (payload && payload.filters) ? payload.filters : { minPrice: null, maxPrice: null, rooms: [] }
  // Сброс локального выбора (возвращаемся к общему виду районов)
  selectedDistrict.value = null
  selectedCluster.value = null
  try { mapRef.value && mapRef.value.setFilters && mapRef.value.setFilters(lastFilters.value) } catch {}
  // Полный перезапуск режима районов, чтобы карта обновилась после повторного квиза
  try { mapRef.value && mapRef.value.hideDistricts && mapRef.value.hideDistricts() } catch {}
  try { mapRef.value && mapRef.value.showDistricts && mapRef.value.showDistricts() } catch {}
}

const selectedDistrict = ref(null)
const selectedCluster = ref(null)

async function ensureDistrictStats() {
  if (districtStats.value) return districtStats.value
  try {
    const res = await fetch('/district_statistics.json', { cache: 'no-store' })
    if (!res.ok) throw new Error('Failed to load district_statistics.json')
    const json = await res.json()
    districtStats.value = json && (json.district_statistics || json)
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn('Не удалось загрузить district_statistics.json', e)
    districtStats.value = null
  }
  return districtStats.value
}

function metricKeysForPriority(id) {
  if (id === 'kindergartens') return ['детские сады']
  if (id === 'green-yard') return ['парки']
  if (id === 'clinic-walk') return ['детские поликлиники', 'поликлиники']
  // fallback: базовые семейные метрики
  return ['детские сады', 'парки', 'детские поликлиники', 'поликлиники']
}

function computeDistrictRatingByStats(stats, districtName, priorityId) {
  if (!stats || !districtName) return null
  const keys = metricKeysForPriority(priorityId)
  const entries = Object.entries(stats)
  if (!entries.length) return null
  const sumFor = (obj) => keys.reduce((s, k) => s + (Number(obj[k]) || 0), 0)
  const values = entries.map(([, obj]) => sumFor(obj || {}))
  const maxVal = Math.max(0, ...values)
  const current = sumFor(stats[districtName] || {})
  if (!Number.isFinite(current) || maxVal <= 0) return 0
  const score = Math.max(0, Math.min(10, (current / maxVal) * 10))
  return +score.toFixed(1)
}

async function onDistrictSelected(payload) {
  await ensureDistrictStats()
  const rating = computeDistrictRatingByStats(districtStats.value, payload?.name, selectedPriorityId.value)
  selectedDistrict.value = { ...payload, rating, filters: lastFilters.value }
  selectedCluster.value = null
}

function onClusterSelected(payload) {
  selectedCluster.value = payload
}

function onClusterBack() {
  selectedCluster.value = null
  try { mapRef.value && mapRef.value.backToDistrictClusters && mapRef.value.backToDistrictClusters() } catch {}
}

function onDistrictBack() {
  // Сбросить выбранный район, вернуться к общему виду (районы + теплокарта по всем данным)
  selectedDistrict.value = null
  selectedCluster.value = null
  try { mapRef.value && mapRef.value.showDistricts && mapRef.value.showDistricts() } catch {}
}

onMounted(() => { ensureDistrictStats() })
</script>

<template>
  <div class="app-layout">
    <MapView ref="mapRef" :points="mapPoints" @district-selected="onDistrictSelected" @cluster-selected="onClusterSelected" />
    <BottomSheet ref="sheetRef" @pick-area="onPickArea" :district="selectedDistrict" :cluster="selectedCluster" @cluster-back="onClusterBack" @district-back="onDistrictBack" />
    <QuizModal v-model="quizOpen" @complete="onQuizComplete" />
  </div>
  
</template>

<style scoped>
.app-layout {
  position: fixed;
  inset: 0;
}
</style>
