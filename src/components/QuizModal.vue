<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'start', 'complete'])

const isOpen = ref(props.modelValue)
const viewHeight = ref(typeof window !== 'undefined' ? window.innerHeight : 0)
const isDragging = ref(false)
const offsetPx = ref(0)
const dragStartY = ref(0)
const dragStartOffset = ref(0)

function resetState() {
  // Полный сброс состояния квиза при новом запуске
  step.value = 1
  children.value = []
  childCounter = 0
  addChild()
  editingChildId.value = null
  selectedTagIds.value = []
  selectedBudgetId.value = null
  selectedRooms.value = []
  isLoading.value = false
  if (loaderTimer) { clearTimeout(loaderTimer); loaderTimer = null }
}

watch(() => props.modelValue, (v, old) => {
  isOpen.value = v
  if (v && old === false) {
    resetState()
  }
})
watch(isOpen, (v) => {
  emit('update:modelValue', v)
  if (v) offsetPx.value = 0
})

const totalSteps = 3
const step = ref(1)
const children = ref([])
const editingChildId = ref(null)
let childCounter = 0

// Шаг 2: приоритеты (выберите один)
const tags = [
  { id: 'kindergartens', label: 'Детские сады', emoji: '🧒' },
  { id: 'green-yard', label: 'Зеленый сквер у дома', emoji: '🌿' },
  { id: 'clinic-walk', label: 'Поликлиника в пешей доступности', emoji: '🏥' },
]
const selectedTagIds = ref([])

// Бюджет: 3 предустановленных варианта
const budgetOptions = [
  { id: 'lt60', label: 'до 60\u00A0000 \u20BD', max: 60000, min: null },
  { id: 'lt90', label: 'до 90\u00A0000 \u20BD', max: 90000, min: null },
  { id: 'ge90', label: '90\u00A0000 \u20BD и больше', max: null, min: 90000 },
]
const selectedBudgetId = ref(null)

// --- Фильтры ---
const selectedRooms = ref([]) // массив чисел
const roomOptions = [1,2,3]

function open() {
  isOpen.value = true
  emit('start')
}

function close() {
  isOpen.value = false
}

const isLoading = ref(false)
let loaderTimer = null

function next() {
  if (step.value < totalSteps) {
    step.value += 1
  } else {
    const selectedTags = tags.filter((t) => selectedTagIds.value.includes(t.id))
    const budget = budgetOptions.find((o) => o.id === selectedBudgetId.value)
    emit('complete', {
      children: children.value,
      priorities: selectedTags,
      filters: {
        maxPrice: (budget && budget.max != null) ? budget.max : null,
        minPrice: (budget && budget.min != null) ? budget.min : null,
        rooms: Array.isArray(selectedRooms.value) && selectedRooms.value.length ? selectedRooms.value.slice() : null,
        // TODO(age-filter): если выбран возраст "0-7 лет", передавать маркер игнорирования фильтров
        // ignoreAllByAge07: children.value.some((c) => c.age === '0-7') ? true : false,
      },
    })
    close()
  }
}

function back() {
  if (step.value > 1) step.value -= 1
}

function addChild() {
  childCounter += 1
  children.value.push({ id: childCounter, age: null, name: `Ребенок ${childCounter}` })
}

function removeChild(id) {
  children.value = children.value.filter((c) => c.id !== id)
}

function setAge(child, age) {
  child.age = age
}

function startEditName(child) {
  editingChildId.value = child.id
}

function stopEditName() {
  editingChildId.value = null
}

function onNameKeydown(e) {
  if (e.key === 'Enter') {
    e.preventDefault()
    e.currentTarget && typeof e.currentTarget.blur === 'function' && e.currentTarget.blur()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    stopEditName()
  }
}

const progressPercent = computed(() => Math.round((step.value / totalSteps) * 100))
const nextDisabled = computed(() => step.value === 3 && isLoading.value)
const nextLabel = computed(() => {
  if (step.value < totalSteps) return 'Далее'
  return isLoading.value ? 'Идёт подбор…' : 'Посмотреть'
})
const selectedTagsText = computed(() => {
  const labels = (tags || []).filter((t) => selectedTagIds.value.includes(t.id)).map((t) => t.label.toLowerCase())
  if (labels.length === 0) return 'подходящие для вас районы'
  if (labels.length === 1) return labels[0]
  if (labels.length === 2) return `${labels[0]} и ${labels[1]}`
  const last = labels.pop()
  return `${labels.join(', ')} и ${last}`
})

const panelStyle = computed(() => ({
  transform: `translateY(${offsetPx.value}px)`,
  transition: isDragging.value ? 'none' : 'transform 300ms cubic-bezier(0.22, 1, 0.36, 1)',
}))

function onResize() {
  viewHeight.value = window.innerHeight
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
  const next = Math.max(dragStartOffset.value + dy, 0)
  if ('preventDefault' in e && typeof e.preventDefault === 'function') e.preventDefault()
  offsetPx.value = next
}

function onGrabEnd() {
  if (!isDragging.value) return
  isDragging.value = false
  const closeThreshold = viewHeight.value * 0.25
  if (offsetPx.value > closeThreshold) {
    close()
    offsetPx.value = 0
  } else {
    offsetPx.value = 0
  }
  window.removeEventListener('mousemove', onGrabMove)
  window.removeEventListener('mouseup', onGrabEnd)
  window.removeEventListener('touchmove', onGrabMove)
  window.removeEventListener('touchend', onGrabEnd)
}

watch(step, (v) => {
  if (v === 3) {
    isLoading.value = true
    if (loaderTimer) clearTimeout(loaderTimer)
    loaderTimer = setTimeout(() => {
      isLoading.value = false
    }, 2000)
  } else {
    isLoading.value = false
    if (loaderTimer) {
      clearTimeout(loaderTimer)
      loaderTimer = null
    }
  }
})

function toggleTag(id) {
  const idx = selectedTagIds.value.indexOf(id)
  if (idx !== -1) {
    selectedTagIds.value.splice(idx, 1)
    return
  }
  // Разрешаем выбрать только один пункт
  selectedTagIds.value.splice(0, selectedTagIds.value.length)
  selectedTagIds.value.push(id)
}

function toggleBudget(id) {
  selectedBudgetId.value = selectedBudgetId.value === id ? null : id
}

function isTagSelected(id) {
  return selectedTagIds.value.includes(id)
}

onMounted(() => {
  if (children.value.length === 0) addChild()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('mousemove', onGrabMove)
  window.removeEventListener('mouseup', onGrabEnd)
  window.removeEventListener('touchmove', onGrabMove)
  window.removeEventListener('touchend', onGrabEnd)
  if (loaderTimer) clearTimeout(loaderTimer)
})
</script>

<template>
  <div v-if="isOpen" class="quiz__overlay">
    <div class="quiz" :style="panelStyle" role="dialog" aria-modal="true">
      <div class="quiz__grab" @mousedown="onGrabStart" @touchstart.passive="onGrabStart" />

      <div class="quiz__body">
        <div v-if="step === 1" class="quiz__step">
          <div class="quiz__header">
            <h2 class="quiz__title">Расскажите о вашей семье</h2>
            <p class="quiz__subtitle">Сколько у вас детей и какого они возраста?</p>
          </div>

          <div class="quiz__children" role="list">
            <div v-for="c in children" :key="c.id" class="child-card">
              <div class="child-card__header">
                <template v-if="editingChildId === c.id">
                  <input
                    class="child-card__name-input"
                    v-model="c.name"
                    @blur="stopEditName"
                    @keydown="onNameKeydown"
                    maxlength="40"
                    autofocus
                  />
                </template>
                <template v-else>
                  <h3 class="child-card__title" @click="startEditName(c)">{{ c.name }}</h3>
                </template>
                <button class="child-card__remove" @click="removeChild(c.id)">&times;</button>
              </div>
              <div class="child-card__ages">
                <button class="age" :class="{ selected: c.age === '0-7' }" @click="setAge(c, '0-7')">0-7 лет</button>
                <button class="age" :class="{ selected: c.age === '7-14' }" @click="setAge(c, '7-14')">7-14 лет</button>
                <button class="age" :class="{ selected: c.age === '14-17' }" @click="setAge(c, '14-17')">14-17 лет</button>
              </div>
            </div>
          </div>

          <button class="btn-add" @click="addChild">Добавить ребенка</button>

          <div class="filters">
          <div class="filters__field">
            <div class="filters__label">Бюджет</div>
            <div class="filters__budget">
              <button
                v-for="b in budgetOptions"
                :key="b.id"
                type="button"
                class="filters__budget-btn"
                :class="{ selected: selectedBudgetId === b.id }"
                @click="toggleBudget(b.id)"
              >
                {{ b.label }}
              </button>
            </div>
          </div>
            <div class="filters__field">
              <div class="filters__label">Количество комнат</div>
              <div class="filters__rooms filters__rooms--compact">
                <button v-for="r in roomOptions" :key="r" type="button" class="filters__room"
                        :class="{ selected: selectedRooms.includes(r) }"
                        @click="selectedRooms.includes(r) ? selectedRooms.splice(selectedRooms.indexOf(r),1) : selectedRooms.push(r)">
                  {{ r === 3 ? '3+' : r }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="step === 2" class="quiz__step">
          <div class="quiz__header">
            <h2 class="quiz__title">Что для вас важнее всего?</h2>
            <p class="quiz__subtitle">Выберите один вариант.</p>
          </div>

          <div class="tags">
            <button
              v-for="t in tags"
              :key="t.id"
              class="tag"
              :class="{ selected: isTagSelected(t.id) }"
              type="button"
              @click="toggleTag(t.id)"
            >
              <span class="tag__emoji" aria-hidden="true">{{ t.emoji }}</span>
              <span class="tag__text">{{ t.label }}</span>
            </button>
          </div>
        </div>

        <div v-else-if="step === 3" class="quiz__step quiz__step--center">
          <div class="result__icon" aria-hidden="true">
            <div class="circle">
              <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="#10B981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
          </div>
          <h2 class="result__title">Спасибо! Я всё понял.</h2>
          <p class="result__subtitle">Ищу для вас районы, где есть {{ selectedTagsText }}.</p>

          <div class="loader" v-if="isLoading">
            <span class="dot" /><span class="dot" /><span class="dot" />
          </div>
        </div>

        <div class="quiz__spacer" />
      </div>

      <div class="quiz__footer">
        <div class="progress">
          <span class="progress__text">Шаг {{ step }} из {{ totalSteps }}</span>
          <div class="progress__bar"><div class="progress__bar-fill" :style="{ width: progressPercent + '%' }" /></div>
          <button v-if="step > 1" class="btn-back" @click="back">Назад</button>
        </div>
        <button class="btn-next" :disabled="nextDisabled" @click="next">{{ nextLabel }}</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quiz__overlay {
  position: fixed;
  inset: 0;
  z-index: 360;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: flex-end;
}

.quiz {
  width: 100%;
  height: 95%;
  background: #f9fafb; /* gray-50 */
  border-top-left-radius: 24px;
  border-top-right-radius: 24px;
  box-shadow: 0 -20px 40px -20px rgba(0, 0, 0, 0.35);
  padding: 12px 16px 16px 16px;
  display: flex;
  flex-direction: column;
  animation: slide-up 380ms cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

@keyframes slide-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

.quiz__grab {
  width: 40px;
  height: 6px;
  border-radius: 9999px;
  background: #d1d5db;
  align-self: center;
  margin-bottom: 12px;
}

.quiz__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
}

.quiz__header { text-align: center; }
.quiz__title { font-size: 22px; font-weight: 800; color: #1f2937; margin-bottom: 6px; }
.quiz__subtitle { color: #6b7280; }

.quiz__children { display: grid; gap: 10px; }
.child-card { background: #fff; border: 2px solid #e5e7eb; border-radius: 16px; padding: 12px; }
.child-card__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.child-card__title { font-weight: 700; color: #1f2937; }
.child-card__name-input { font-weight: 700; color: #1f2937; border: 2px solid #e5e7eb; border-radius: 10px; padding: 6px 10px; background: #fff; width: 100%; max-width: 220px; }
.child-card__remove { font-size: 20px; color: #9ca3af; background: none; border: none; }
.child-card__ages { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.age { padding: 8px; border: 2px solid #e5e7eb; border-radius: 10px; background: #fff; font-size: 14px; color: #1f2937}
.age.selected { background: #dbeafe; color: #2563eb; border-color: #93c5fd; }

.btn-add { width: 100%; padding: 12px; background: rgba(59, 130, 246, 0.1); color: #2563eb; font-weight: 700; border: 2px dashed rgba(59, 130, 246, 0.4); border-radius: 12px; }

/* Filters */
.filters { margin-top: 12px; display: grid; gap: 12px; }
.filters__field { display: grid; gap: 6px; }
.filters__label { font-weight: 800; color: #1f2937; }
.filters__input { border: 2px solid #e5e7eb; border-radius: 10px; padding: 8px 10px; background: #fff; color: #1f2937; }
.filters__rooms { display: grid; grid-template-columns: repeat(8, 1fr); gap: 6px; }
.filters__rooms--compact { grid-template-columns: repeat(3, 1fr); }
.filters__room { padding: 8px 0; border: 2px solid #e5e7eb; border-radius: 10px; background: #fff; font-weight: 700; color: #1f2937; }
.filters__room.selected { background: #dbeafe; color: #2563eb; border-color: #93c5fd; }

/* Budget buttons */
.filters__budget { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.filters__budget-btn { padding: 10px 8px; border: 2px solid #e5e7eb; border-radius: 10px; background: #fff; font-weight: 700; color: #1f2937; }
.filters__budget-btn.selected { background: #dbeafe; color: #2563eb; border-color: #93c5fd; }

.tags { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.tag { background: #fff; border: 2px solid #e5e7eb; border-radius: 16px; padding: 12px; font-weight: 600; color: #1f2937; }
.tag.selected { background: #eff6ff; color: #1d4ed8; border-color: #c7d2fe; }
.tag__emoji { margin-right: 8px; font-size: 18px; }
.tag__text { vertical-align: middle; }

.quiz__spacer { height: 8px; }

.quiz__footer { margin-top: auto; display: grid; gap: 10px; }
.progress { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 12px; }
.progress__text { color: #6b7280; font-weight: 600; }
.progress__bar { grid-column: 1 / -1; height: 6px; background: #e5e7eb; border-radius: 9999px; overflow: hidden; }
.progress__bar-fill { height: 100%; background: #4A90E2; width: 0; transition: width 300ms ease; }

.btn-back { justify-self: end; color: #6b7280; font-weight: 600; background: none; border: none; }
.btn-next { width: 100%; background: #4A90E2; color: #fff; font-weight: 800; padding: 12px; border-radius: 16px; border: none; font-size: 16px; }
.btn-next:disabled { opacity: 0.6; }

.quiz__step--center { text-align: center; padding-top: 12px; }
.result__icon { display: flex; justify-content: center; margin-bottom: 12px; }
.result__icon .circle { width: 64px; height: 64px; border-radius: 9999px; background: #d1fae5; display: flex; align-items: center; justify-content: center; }
.result__title { font-size: 22px; font-weight: 800; color: #1f2937; margin: 12px 0 8px; }
.result__subtitle { color: #6b7280; }

.loader { display: flex; gap: 6px; justify-content: center; margin-top: 14px; }
.loader .dot { width: 8px; height: 8px; border-radius: 50%; background: #9ca3af; animation: bounce 1s infinite ease-in-out alternate; }
.loader .dot:nth-child(2) { animation-delay: 0.15s; }
.loader .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce { from { transform: translateY(0); opacity: .7; } to { transform: translateY(-6px); opacity: 1; } }
</style>


