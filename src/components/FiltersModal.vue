<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  initialFilters: { type: Object, default: () => ({ minPrice: null, maxPrice: null, rooms: [] }) },
})
const emit = defineEmits(['update:modelValue', 'apply'])

const isOpen = ref(!!props.modelValue)
watch(() => props.modelValue, (v) => { isOpen.value = v })
watch(isOpen, (v) => {
  emit('update:modelValue', v)
  // При каждом открытии актуализируем значения из initialFilters
  if (v) fromInitial()
})
// Если снаружи изменили initialFilters — подставляем новые в локальное состояние
watch(() => props.initialFilters, () => {
  fromInitial()
}, { deep: true })

// Локальное состояние фильтров
const priceMin = ref(null)
const priceMax = ref(null)
const rooms = ref([]) // массив чисел

// Моки чекбоксов (не передаются наружу)
const withHighSchool = ref(false)
const withStrollerWalks = ref(false)
const withQuietEvenings = ref(false)
const withStressFreeParking = ref(false)

function fromInitial() {
  const f = props.initialFilters || {}
  priceMin.value = Number.isFinite(f.minPrice) ? Number(f.minPrice) : null
  priceMax.value = Number.isFinite(f.maxPrice) ? Number(f.maxPrice) : null
  rooms.value = Array.isArray(f.rooms) ? f.rooms.slice() : []
}

function resetAll() {
  priceMin.value = null
  priceMax.value = null
  rooms.value = []
  withHighSchool.value = false
  withStrollerWalks.value = false
  withQuietEvenings.value = false
  withStressFreeParking.value = false
}

function toggleRoom(n) {
  const idx = rooms.value.indexOf(n)
  if (idx !== -1) rooms.value.splice(idx, 1)
  else rooms.value.push(n)
}

function close() { isOpen.value = false }

function apply() {
  const filters = {
    minPrice: Number.isFinite(priceMin.value) ? Number(priceMin.value) : null,
    maxPrice: Number.isFinite(priceMax.value) ? Number(priceMax.value) : null,
    rooms: rooms.value.length ? rooms.value.slice() : null,
  }
  emit('apply', filters)
  close()
}

onMounted(() => { fromInitial(); window.addEventListener('keydown', onEsc) })
onBeforeUnmount(() => { window.removeEventListener('keydown', onEsc) })
function onEsc(e) { if (e.key === 'Escape') close() }

const panelStyle = computed(() => ({ }));
</script>

<template>
  <div v-if="isOpen" class="filters__overlay">
    <div class="filters" :style="panelStyle" role="dialog" aria-modal="true">
      <div class="filters__header">
        <button class="filters__reset" type="button" @click="resetAll">Сбросить</button>
        <h2 class="filters__title">Фильтры</h2>
        <button class="filters__close" type="button" aria-label="Закрыть" @click="close">✕</button>
      </div>

      <div class="filters__body">
        <section class="card">
          <h3 class="card__title">Основные параметры</h3>
          <div class="price">
            <div class="price__label">Цена, ₽/мес.</div>
            <div class="price__row">
              <input class="price__input" type="number" min="0" step="1000" placeholder="от"
                     v-model.number="priceMin" />
              <input class="price__input" type="number" min="0" step="1000" placeholder="до"
                     v-model.number="priceMax" />
            </div>
          </div>

          <div class="rooms">
            <div class="rooms__label">Количество комнат</div>
            <div class="rooms__row">
              <button type="button" class="rooms__btn" :class="{ selected: rooms.includes(1) }" @click="toggleRoom(1)">1</button>
              <button type="button" class="rooms__btn" :class="{ selected: rooms.includes(2) }" @click="toggleRoom(2)">2</button>
              <button type="button" class="rooms__btn" :class="{ selected: rooms.includes(3) }" @click="toggleRoom(3)">3+</button>
            </div>
          </div>
        </section>

        <section class="card">
          <h3 class="card__title">Сценарии семейной жизни</h3>
          <div class="toggles">
            <div class="toggle">
              <div class="toggle__title">🎓 Школа с высоким рейтингом</div>
              <label class="switch">
                <input type="checkbox" v-model="withHighSchool" />
                <span class="slider" />
              </label>
            </div>
            <div class="toggle">
              <div class="toggle__title">👶 Есть, где гулять с коляской</div>
              <label class="switch">
                <input type="checkbox" v-model="withStrollerWalks" />
                <span class="slider" />
              </label>
            </div>
            <div class="toggle">
              <div class="toggle__title">🕊️ Тишина по вечерам</div>
              <label class="switch">
                <input type="checkbox" v-model="withQuietEvenings" />
                <span class="slider" />
              </label>
            </div>
            <div class="toggle">
              <div class="toggle__title">🅿️ Парковка без стресса</div>
              <label class="switch">
                <input type="checkbox" v-model="withStressFreeParking" />
                <span class="slider" />
              </label>
            </div>
          </div>
        </section>
      </div>

      <div class="filters__footer">
        <button class="btn-primary" type="button" @click="apply">Показать варианты</button>
      </div>
    </div>
  </div>
  
</template>

<style scoped>
.filters__overlay { position: fixed; inset: 0; z-index: 400; background: rgba(0,0,0,.35); display: flex; align-items: flex-end; }
.filters { width: 100%; height: 100%; background: #fff; border-top-left-radius: 24px; border-top-right-radius: 24px; box-shadow: 0 -20px 40px -20px rgba(0,0,0,.35); display: flex; flex-direction: column; }
.filters__header { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; padding: 12px 16px; }
.filters__title { justify-self: center; font-weight: 800; color: #1f2937; }
.filters__reset { justify-self: start; background: none; border: none; color: #6b7280; font-weight: 700; }
.filters__close { justify-self: end; background: none; border: none; color: #6b7280; font-weight: 900; font-size: 18px; }
.filters__body { padding: 0 16px 16px 16px; overflow: auto; display: grid; gap: 12px; }

.card { background: #fff; border: 2px solid #e5e7eb; border-radius: 16px; padding: 12px; display: grid; gap: 12px; }
.card__title { font-weight: 800; color: #1f2937; }

.price__label, .rooms__label { font-weight: 800; color: #1f2937; margin-bottom: 6px; }
.price__row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.price__input { border: 2px solid #e5e7eb; border-radius: 10px; padding: 10px; background: #fff; color: #1f2937; }

.rooms__row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.rooms__btn { padding: 10px 0; border: 2px solid #e5e7eb; border-radius: 10px; background: #fff; font-weight: 700; color: #1f2937; }
.rooms__btn.selected { background: #dbeafe; color: #2563eb; border-color: #93c5fd; }

.toggles { display: grid; gap: 10px; }
.toggle { display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; border: 2px solid #e5e7eb; border-radius: 12px; }
.toggle__title { font-weight: 700; color: #1f2937; }

/* iOS-like switch */
.switch { position: relative; display: inline-block; width: 44px; height: 26px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; inset: 0; background: #e5e7eb; transition: .2s; border-radius: 9999px; }
.slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px; top: 3px; background: #fff; transition: .2s; border-radius: 50%; box-shadow: 0 1px 3px rgba(0,0,0,.15); }
.switch input:checked + .slider { background: #4A90E2; }
.switch input:checked + .slider:before { transform: translateX(18px); }

.filters__footer { margin-top: auto; padding: 12px 16px; box-shadow: 0 -10px 20px -15px rgba(0,0,0,.2); background: #fff; }
.btn-primary { width: 100%; background: #4A90E2; color: #fff; font-weight: 800; padding: 12px; border-radius: 16px; border: none; font-size: 16px; }
</style>


