<script setup>
import { ref, computed, onMounted, onBeforeUnmount, defineExpose } from 'vue'
import FiltersModal from './FiltersModal.vue'
const emit = defineEmits(['pick-area', 'cluster-back', 'district-back'])
const props = defineProps({
  district: { type: Object, default: null },
  cluster: { type: Object, default: null },
})

// Текущее количество квартир для счета в district-card
const currentDistrictCount = computed(() => {
  const c = props.cluster && Array.isArray(props.cluster.apartments) ? props.cluster.apartments.length : null
  if (c != null) return c
  const d = props.district && Array.isArray(props.district.apartments) ? props.district.apartments.length : 0
  return d
})

const viewHeight = ref(typeof window !== 'undefined' ? window.innerHeight : 0)
const isDragging = ref(false)
const dragStartY = ref(0)
const dragStartOffset = ref(0)
const offsetPx = ref(0)

const collapsedRatio = 0.75
const handleMinVisiblePx = 48

const maxOffsetPx = computed(() => Math.max(viewHeight.value - handleMinVisiblePx, 0))
const collapsedOffsetPx = computed(() => Math.round(viewHeight.value * collapsedRatio))

const panelStyle = computed(() => ({
  transform: `translateY(${offsetPx.value}px)`,
  transition: isDragging.value ? 'none' : 'transform 320ms cubic-bezier(0.22, 1, 0.36, 1)',
}))

function clampOffset(px) {
  return Math.min(Math.max(px, 0), maxOffsetPx.value)
}

function setExpanded(expanded) {
  offsetPx.value = expanded ? 0 : collapsedOffsetPx.value
}

function toggleExpand() {
  setExpanded(offsetPx.value !== 0)
}

function onPickArea() {
  setExpanded(true)
  emit('pick-area')
}

function onResize() {
  viewHeight.value = window.innerHeight
  if (offsetPx.value === 0) return
  offsetPx.value = clampOffset(collapsedOffsetPx.value)
}

function onGrabStart(e) {
  isDragging.value = true
  dragStartOffset.value = offsetPx.value
  dragStartY.value = 'touches' in e ? e.touches[0].clientY : e.clientY
  window.addEventListener('mousemove', onGrabMove)
  window.addEventListener('mouseup', onGrabEnd)
  window.addEventListener('touchmove', onGrabMove, { passive: false })
  window.addEventListener('touchend', onGrabEnd)
}

function onGrabMove(e) {
  if (!isDragging.value) return
  const currentY = 'touches' in e ? e.touches[0].clientY : e.clientY
  const dy = currentY - dragStartY.value
  const next = clampOffset(dragStartOffset.value + dy)
  if ('preventDefault' in e && typeof e.preventDefault === 'function') e.preventDefault()
  offsetPx.value = next
}

function onGrabEnd() {
  if (!isDragging.value) return
  isDragging.value = false
  const expandThreshold = viewHeight.value * 0.35
  const targetExpanded = offsetPx.value < expandThreshold
  setExpanded(targetExpanded)
  window.removeEventListener('mousemove', onGrabMove)
  window.removeEventListener('mouseup', onGrabEnd)
  window.removeEventListener('touchmove', onGrabMove)
  window.removeEventListener('touchend', onGrabEnd)
}

onMounted(() => {
  viewHeight.value = window.innerHeight
  offsetPx.value = collapsedOffsetPx.value
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('mousemove', onGrabMove)
  window.removeEventListener('mouseup', onGrabEnd)
  window.removeEventListener('touchmove', onGrabMove)
  window.removeEventListener('touchend', onGrabEnd)
})

function collapseFully() {
  offsetPx.value = maxOffsetPx.value
}

function collapsePartial() {
  offsetPx.value = collapsedOffsetPx.value
}

function expand() {
  offsetPx.value = 0
}

defineExpose({ collapseFully, collapsePartial, expand })

// ----- Детальная страница квартиры -----
const selectedApartment = ref(null)
function openApartment(ap) {
  selectedApartment.value = ap
  expand()
}
function closeApartment() {
  selectedApartment.value = null
}
// Единая кнопка «назад» в шапке района: шаг назад по текущему состоянию
function onUnifiedBack() {
  if (selectedApartment.value) {
    // Назад со страницы квартиры → к списку кластера
    closeApartment()
    return
  }
  if (props.cluster) {
    // Назад со списка квартир → к кластерам района
    emit('cluster-back')
    return
  }
  // Назад с кластера района → к выбору районов
  emit('district-back')
}

const filtersOpen = ref(false)
function openFilters() { filtersOpen.value = true }
function closeFilters() { filtersOpen.value = false }
const currentFilters = computed(() => ({
  // В текущей версии фильтры живут в App.vue → MapView.
  // Шторка хранит только локально выбранную квартиру, поэтому префилл передаём из district пропсом сверху.
  // Ожидается, что родитель пробросит district.filters при желании.
  minPrice: (props.district && props.district.filters && Number.isFinite(props.district.filters.minPrice)) ? props.district.filters.minPrice : null,
  maxPrice: (props.district && props.district.filters && Number.isFinite(props.district.filters.maxPrice)) ? props.district.filters.maxPrice : null,
  rooms: (props.district && props.district.filters && Array.isArray(props.district.filters.rooms)) ? props.district.filters.rooms : [],
}))
function onApplyFilters(f) {
  // Пробрасываем наверх — App.vue применит через MapView.setFilters
  // Здесь просто закрываем модалку
  closeFilters()
  // создадим кастомное событие для родителя
  const ev = new CustomEvent('filters-apply', { detail: f })
  try { window.dispatchEvent(ev) } catch {}
}

// ----- Оценка по критериям для выбранной квартиры -----
function firstDistance(arr) {
  if (!arr || !arr.length) return Infinity
  const d = Number(arr[0] && arr[0].distance)
  return Number.isFinite(d) ? d : Infinity
}

function bandForDistance(d) {
  if (d <= 1000) return 'green'
  if (d <= 2000) return 'yellow'
  return 'red'
}

function scoreForDistance(d) {
  if (!Number.isFinite(d)) return 0
  if (d <= 1000) return Math.max(8, +(10 - (d / 1000) * 2).toFixed(1))
  if (d <= 2000) return Math.max(5, +(8 - ((d - 1000) / 1000) * 3).toFixed(1))
  return Math.max(1, +(5 - Math.min(3.5, ((d - 2000) / 1000) * 4)).toFixed(1))
}

function percentForDistance(d) {
  if (!Number.isFinite(d)) return 0
  return Math.max(0, Math.min(100, Math.round(((3000 - d) / 3000) * 100)))
}

function minutesForDistance(d) {
  if (!Number.isFinite(d)) return null
  const minutesPerKm = 12 // ~5 км/ч пешком
  const minutes = Math.round((d / 1000) * minutesPerKm)
  return Math.max(1, minutes)
}

const familyScores = computed(() => {
  const ap = selectedApartment.value
  if (!ap) return null
  const no = (ap && (ap.nearest_objects || ap.nearest)) || {}
  const kd = firstDistance(no.nearest_kindergartens)
  const hd = firstDistance(no.nearest_child_hospitals || no.nearest_child_polyclinics)
  const pd = firstDistance(no.nearest_parks)
  const items = [
    { key: 'kindergarten', label: 'Детские сады', icon: '🧒', distance: kd },
    { key: 'park', label: 'Парки', icon: '🌳', distance: pd },
    { key: 'hospital', label: 'Поликлиника', icon: '🏥', distance: hd },
  ]
  return items.map((it) => {
    const band = bandForDistance(it.distance)
    const score = scoreForDistance(it.distance)
    const percent = percentForDistance(it.distance)
    const verdict = band === 'green' ? 'Отлично' : band === 'yellow' ? 'Хорошо' : 'Удовлетворительно'
    const minutes = minutesForDistance(it.distance)
    return { ...it, band, score, percent, verdict, minutes }
  })
})

const familyTotal = computed(() => {
  const arr = familyScores.value || []
  if (!arr.length) return null
  const sum = arr.reduce((s, x) => s + (Number(x.score) || 0), 0)
  return +(sum / arr.length).toFixed(1)
})

// Цвета для фона плейсхолдера фото в списке
const photoBgColors = ['#cde7ff', '#c7f0db', '#fde68a', '#fbcfe8', '#e9d5ff', '#fecaca']
function getPhotoBg(idx) {
  const arr = photoBgColors
  if (!Number.isInteger(idx) || idx < 0) return arr[0]
  return arr[idx % arr.length]
}
</script>

<template>
  <div class="sheet">
    <div class="sheet__panel" :style="panelStyle">
      <div class="sheet__handle" @click="toggleExpand" @mousedown="onGrabStart" @touchstart.passive="onGrabStart">
        <div class="sheet__grab" />
      </div>

      <div class="sheet__content">
        <div class="sheet__cta">
          <button class="cta" @click="onPickArea">
            <span class="cta__icon" aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            </span>
            Подобрать район
          </button>
        </div>

        <div class="sheet__quick-actions">
          <div class="chips" aria-label="Быстрые действия">
            <button class="chip" type="button">
              <span class="chip__icon" aria-hidden="true">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m19 21-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
              </span>
              Сохранённое
            </button>
            <button class="chip chip--strong" type="button">
              <span class="chip__icon" aria-hidden="true">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
              </span>
              43 мин
            </button>
            <button class="chip" type="button">Поесть</button>
            <button class="chip" type="button">Скидки для вас</button>
            <button class="chip" type="button">Парки</button>
            <button class="chip" type="button">Развлечения</button>
          </div>
        </div>

        <div class="sheet__search">
          <div class="search">
            <span class="search__icon" aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            </span>
            <input class="search__input" placeholder="Поиск" />
            <span class="search__icon" aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>
            </span>
            <span class="search__divider" />
            <span class="search__icon" aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
            </span>
          </div>
        </div>

        <!-- Динамический контент: шапка района + единая кнопка назад -->
        <div v-if="district" class="district-card">
          <div class="district-card__header">
            <button class="ap-detail__back" type="button" @click="onUnifiedBack" aria-label="Назад">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            </button>
            <div class="district-card__margin">
              <h3 class="district-card__title">{{ district.name }}</h3>
              <div class="district-card__meta">
                <span class="district-card__score">Подобрано: {{ currentDistrictCount }} квартир</span>
                <span v-if="district.rating != null" class="district-card__match">Совпадение: <strong>{{ district.rating }}</strong>/10</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="cluster && !selectedApartment" class="cluster-card">
          <div class="cluster-card__header">
            <h3 class="cluster-card__title">Квартиры в выбранном кластере</h3>
          </div>
          <div class="cluster-list">
            <div v-for="(ap, idx) in cluster.apartments" :key="ap.id || (ap.longitude + ',' + ap.latitude)" class="ap-card" @click="openApartment(ap)">
              <div class="ap-card__photo" :style="{ background: getPhotoBg(idx) }" aria-hidden="true">
                <svg class="ap-card__photo-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <path d="M0 16h4l12-13.696 12 13.696h4l-13.984-16h-4zM4 32h8v-9.984q0-0.832 0.576-1.408t1.44-0.608h4q0.8 0 1.408 0.608t0.576 1.408v9.984h8v-13.408l-12-13.248-12 13.248v13.408zM26.016 6.112l4 4.576v-8.672h-4v4.096z"></path>
                </svg>
              </div>
              <div class="ap-card__body">
                <div class="ap-card__meta ap-card__meta--top">
                  <span v-if="ap.room_type">{{ ap.room_type }}</span>
                  <span v-else-if="ap.rooms">{{ ap.rooms }}-комнатная</span>
                  <span v-if="Number.isFinite(ap.area)">, {{ Math.round(ap.area) }} м²</span>
                </div>
                <div class="ap-card__price" v-if="Number.isFinite(ap.price)">{{ ap.price.toLocaleString('ru-RU') }} ₽/мес.</div>
                <div class="ap-card__addr">{{ ap.address || 'Адрес не указан' }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Детальная страница квартиры -->
        <div v-if="selectedApartment" class="ap-detail">
          <div class="ap-detail__header">
            <h3 class="ap-detail__title">{{ selectedApartment.room_type || (selectedApartment.rooms ? selectedApartment.rooms + '-комнатная' : 'Квартира') }}, <span v-if="Number.isFinite(selectedApartment.area)">{{ Math.round(selectedApartment.area) }} м²</span></h3>
          </div>
          <!-- <div class="ap-detail__media" aria-hidden="true">Фото</div> -->
          <div class="ap-detail__body">
            <div v-if="familyScores" class="family-score">
              <div class="family-score__header">
                <h4 class="family-score__title">Для вашей семьи:</h4>
                <span class="family-score__total" v-if="familyTotal != null">{{ familyTotal }}/10</span>
              </div>
              <div class="family-score__items">
                <div v-for="row in familyScores" :key="row.key" class="family-score__row">
                  <div class="family-score__top">
                    <div class="family-score__label"><span class="family-score__icon" aria-hidden="true">{{ row.icon }}</span>{{ row.label }}</div>
                    <div class="family-score__verdict" :class="'is-' + row.band">{{ row.verdict }}</div>
                  </div>
                  <div class="family-score__bar">
                    <div class="family-score__bar-fill" :class="'is-' + row.band" :style="{ width: row.percent + '%' }" />
                  </div>
                <div v-if="row.minutes != null" class="family-score__foot">~ {{ row.minutes }} мин пешком</div>
                </div>
              </div>
            </div>

            <div class="ap-detail__price" v-if="Number.isFinite(selectedApartment.price)">{{ selectedApartment.price.toLocaleString('ru-RU') }} ₽/мес.</div>
            <div class="ap-detail__addr">{{ selectedApartment.address || 'Адрес не указан' }}</div>

            <div class="ap-detail__badges">
              <span v-if="selectedApartment.floor != null && selectedApartment.total_floors != null" class="badge">Этаж {{ selectedApartment.floor }} / {{ selectedApartment.total_floors }}</span>
              <span v-if="selectedApartment.metro" class="badge">{{ selectedApartment.metro }}<span v-if="selectedApartment.metro_time"> · {{ selectedApartment.metro_time }} мин</span></span>
              <span v-if="selectedApartment.build_year" class="badge">Год постройки: {{ selectedApartment.build_year }}</span>
            </div>

            <div v-if="selectedApartment.description" class="ap-detail__desc">{{ selectedApartment.description }}</div>

            <!-- Главное в этой квартире -->
            <div class="highlights">
              <h4 class="highlights__title">Главное в этой квартире</h4>
              <div class="highlights__grid">
                <div class="highlight"><span class="highlight__icon" aria-hidden="true">🍇</span><span class="highlight__text">Можно с животными</span></div>
                <div class="highlight"><span class="highlight__icon" aria-hidden="true">🅿️</span><span class="highlight__text">Есть парковка</span></div>
                <div class="highlight"><span class="highlight__icon" aria-hidden="true">🌳</span><span class="highlight__text">Окна во двор</span></div>
                <div class="highlight"><span class="highlight__icon" aria-hidden="true">🛏️</span><span class="highlight__text">С мебелью</span></div>
                <div class="highlight"><span class="highlight__icon" aria-hidden="true">❄️</span><span class="highlight__text">Кондиционер</span></div>
                <div class="highlight"><span class="highlight__icon" aria-hidden="true">🛠️</span><span class="highlight__text">Хороший ремонт</span></div>
              </div>
            </div>

            <div class="ap-detail__actions">
              <a v-if="selectedApartment.url" class="action action--primary" :href="selectedApartment.url" target="_blank" rel="noopener">Забронировать</a>
            </div>
          </div>
        </div>

        <div v-if="district" class="filters-cta">
          <button class="filters-btn" type="button" @click="openFilters">
            <span class="filters-btn__icon" aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
            </span>
            Фильтры
          </button>
        </div>

        <div class="sheet__spacer" />
      </div>
    </div>
  </div>
  <FiltersModal v-model="filtersOpen" :initial-filters="currentFilters" @apply="onApplyFilters" />

</template>

<style scoped>
.sheet {
  position: fixed;
  inset: 0;
  z-index: 350;
  pointer-events: none;
}
.district-card__margin {
  margin-left: 20px;
}
.sheet__panel {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  top: 0;
  transform: translateY(75%);
  transition: transform 320ms cubic-bezier(0.22, 1, 0.36, 1);
  background: #ffffff;
  border-top-left-radius: 16px;
  border-top-right-radius: 16px;
  box-shadow: 0 -10px 30px -15px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  pointer-events: auto;
  max-height: 100%;
}

.sheet__handle {
  display: flex;
  justify-content: center;
  padding: 8px 0 6px 0;
}

.sheet__grab {
  width: 40px;
  height: 6px;
  border-radius: 9999px;
  background: #e5e7eb; /* gray-300 */
}

.sheet__content {
  padding: 0 16px 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.sheet__cta {
  display: flex;
  justify-content: center;
}

.cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #111827; /* gray-100 */
  color: #f3f4f6; /* gray-900 */
  border-radius: 9999px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  margin: 10px 0;
}

.cta__icon {
  display: inline-flex;
}

.chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 6px;
}

.chip {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #f3f4f6; /* gray-100 */
  color: #1f2937; /* gray-800 */
  border-radius: 9999px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 500;
  border: none;
}

.chip--strong {
  background: #eef2ff; /* indigo-50 */
  color: #1e40af; /* indigo-800 */
  font-weight: 600;
}

.chip__icon {
  display: inline-flex;
}

.filters-cta { display: flex; justify-content: center; }
.filters-btn { display: inline-flex; align-items: center; gap: 8px; background: #1d4ed8; color: #fff; border: none; border-radius: 12px; padding: 10px 16px; font-weight: 800; }
.filters-btn__icon { display: inline-flex; }

.sheet__search {
  padding-top: 4px;
}

.search {
  display: grid;
  grid-template-columns: 24px 1fr 24px 1px 24px;
  align-items: center;
  background: #f3f4f6; /* gray-100 */
  border-radius: 12px;
  padding: 8px 8px;
}

.search__icon {
  display: inline-flex;
  justify-content: center;
  color: #6b7280; /* gray-500 */
}

.search__input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  color: #1f2937; /* gray-800 */
}

.search__divider {
  height: 24px;
  width: 1px;
  background: #d1d5db; /* gray-300 */
  justify-self: center;
}

.sheet__spacer {
  height: 8px;
}

/* District */
.district-card { background: #fff; border: 2px solid #e5e7eb; border-radius: 12px; padding: 12px; }
.district-card__header { display: flex; align-items: center; }
.district-card__title { font-weight: 800; color: #1f2937; margin: 10px 0;}
.district-card__meta { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.district-card__score { color: #10B981; font-weight: 700; }
.district-card__match { color: #10B981; font-weight: 800; }

/* Cluster list */
.cluster-card { background: #fff; border: 2px solid #e5e7eb; border-radius: 12px; padding: 12px; display: grid; gap: 10px; overflow: auto;}
.cluster-card__header { display: flex; justify-content: space-between; align-items: center; }
.cluster-card__title { font-weight: 800; color: #1f2937; }
.cluster-list { display: grid; gap: 10px; overflow: auto;}
.ap-card { display: grid; grid-template-columns: 84px 1fr; gap: 10px; background: #fff; border: 2px solid #e5e7eb; border-radius: 12px; padding: 10px; }
.ap-card__photo { width: 84px; height: 84px; border-radius: 10px; background: #e5e7eb; color: #6b7280; display: flex; align-items: center; justify-content: center; }
.ap-card__photo-icon { width: 36px; height: 36px; fill: #6b7280; }
.ap-card__meta { color: #6b7280; font-size: 14px; }
.ap-card__meta--top { margin-bottom: 4px; }
.ap-card__price { font-weight: 900; color: #111827; font-size: 20px; }
.ap-card__addr { color: #374151; }
.ap-card__link { color: #1d4ed8; font-weight: 700; text-decoration: none; }

/* Apartment detail */
.ap-detail { display: grid; gap: 12px; background: #fff; border: 2px solid #e5e7eb; border-radius: 12px; padding: 12px; overflow: auto;}
.ap-detail__header { display: flex; align-items: center; gap: 8px; }
.ap-detail__back { background: #f3f4f6; border: none; border-radius: 10px; padding: 6px; color: #374151; }
.ap-detail__title { font-weight: 900; color: #111827; }
.ap-detail__media { height: 160px; border-radius: 12px; background: #e5e7eb; color: #6b7280; display: flex; align-items: center; justify-content: center; font-weight: 800; }
.ap-detail__price { font-size: 22px; font-weight: 900; color: #111827; }
.ap-detail__addr { color: #374151; }
.ap-detail__badges { display: flex; flex-wrap: wrap; gap: 8px; }
.badge { background: #f3f4f6; color: #1f2937; border-radius: 9999px; padding: 6px 10px; font-weight: 600; font-size: 12px; }
.ap-detail__desc { color: #4b5563; white-space: pre-line; }
.ap-detail__actions { display: flex; gap: 10px; }
.action { display: inline-flex; align-items: center; justify-content: center; padding: 10px 14px; border-radius: 12px; font-weight: 800; text-decoration: none; }
.action--primary { background: #1d4ed8; color: #fff; margin: 20px 0; width: 100%;}

/* Family score */
.family-score { background: #eff6ff; border: 2px solid rgba(59,130,246,0.25); border-radius: 12px; padding: 12px; padding: 12px; margin: 20px 0; }
.family-score__header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 6px; }
.family-score__title { font-weight: 800; color: #1f2937; }
.family-score__total { font-weight: 900; color: #4A90E2; }
.family-score__items { display: grid; gap: 10px; }
.family-score__row { display: grid; gap: 6px; }
.family-score__top { display: flex; align-items: center; justify-content: space-between; }
.family-score__label { display: inline-flex; align-items: center; gap: 6px; font-weight: 700; color: #1f2937; }
.family-score__icon { font-size: 18px; }
.family-score__verdict { font-weight: 800; }
.family-score__verdict.is-green { color: #10B981; }
.family-score__verdict.is-yellow { color: #D97706; }
.family-score__verdict.is-red { color: #EF4444; }
.family-score__bar { height: 8px; background: #e5e7eb; border-radius: 9999px; overflow: hidden; }
.family-score__bar-fill { height: 100%; border-radius: 9999px; width: 0; }
.family-score__bar-fill.is-green { background: #10B981; }
.family-score__bar-fill.is-yellow { background: #F59E0B; }
.family-score__bar-fill.is-red { background: #EF4444; }

.family-score__foot { color: #374151; font-size: 12px; }

/* Highlights */
.highlights { margin-top: 8px; }
.highlights__title { font-weight: 800; color: #1f2937; margin-bottom: 8px; }
.highlights__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; }
.highlight { display: inline-flex; align-items: center; gap: 8px; color: #1f2937; }
.highlight__icon { font-size: 18px; line-height: 1; }
.highlight__text { font-weight: 600; color: #1f2937; }
</style>


