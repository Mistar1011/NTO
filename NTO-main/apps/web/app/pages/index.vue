<script setup lang="ts">
// 1. Состояние и хуки
const { stream, start, stop } = useUserMedia({
  constraints: { video: {facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 }, frameRate:{ ideal: 30} } }
})
const { connectToServer, sendFrame, processedImage, isConnected } = useCV()

const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const isStreaming = ref(false)
const value = ref('yolo') // Текущий режим

let isLocked = false // Замок на отправку кадра
let offscreenCanvas: HTMLCanvasElement | null = null
let reconnectInterval: any = null

const items = [
  { label: 'Нейросеть', value: 'yolo' },
  { label: 'Фильтр', value: 'gray' },
  { label: 'Оригинал', value: 'none' },
  { label: 'Линейка', value: 'ruler' },
  { label: 'Маркер', value: 'aruco' },
  { label: 'Игра', value: 'ar_game' }
  { label: '3Д', value: '3Dar_game' }
]

const captureAndSend = () => {
  if (!videoRef.value || !isStreaming.value || !isConnected.value || isLocked) return
  if (value.value === 'none') return

  const v = videoRef.value
  
  // Создаем/обновляем canvas для отправки с сохранением пропорций
  if (!offscreenCanvas) {
    offscreenCanvas = document.createElement("canvas")
    // Вместо жестких 640x360, берем пропорцию видео
    const scale = 640 / v.videoWidth 
    offscreenCanvas.width = 640
    offscreenCanvas.height = v.videoHeight * scale
  }

  isLocked = true 
  const octx = offscreenCanvas.getContext("2d")
  // Рисуем четко в размер canvas
  octx?.drawImage(v, 0, 0, offscreenCanvas.width, offscreenCanvas.height)

  offscreenCanvas.toBlob((blob) => {
    if (blob && isStreaming.value && value.value !== 'none') {
      sendFrame({ image: blob, mode: value.value })
    } else {
      isLocked = false
    }
  }, "image/jpeg", 0.8) // Чуть снизил качество до 0.7 для скорости
}

// 3. ПРИЕМ МАСКИ (Результат от сервера)
watch(processedImage, (newUrl) => {
  if (!newUrl) return
  const canvas = canvasRef.value
  const ctx = canvas?.getContext('2d')
  if (!ctx || !canvas) return

  const img = new Image()
  img.onload = () => {
    if (value.value !== 'none') {
      // КЛЮЧЕВОЙ МОМЕНТ: 
      // Синхронизируем размер канваса с видео, чтобы наложение было 1-в-1
      if (canvas.width !== videoRef.value!.videoWidth) {
         canvas.width = videoRef.value!.videoWidth
         canvas.height = videoRef.value!.videoHeight
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height)
      // Рисуем маску, растягивая её ровно на размер видео кадра
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
    }
    URL.revokeObjectURL(newUrl)
    isLocked = false 
    requestAnimationFrame(captureAndSend)
  }
  img.src = newUrl
})

// 4. РЕАКЦИЯ НА ИЗМЕНЕНИЯ (Watchers)
watch(value, (newMode) => {
  const ctx = canvasRef.value?.getContext('2d')
  ctx?.clearRect(0, 0, canvasRef.value!.width, canvasRef.value!.height)
  
  if (newMode !== 'none' && isStreaming.value) {
    isLocked = false
    captureAndSend() // Запускаем цикл заново при смене режима
  }
})

watchEffect(() => {
  if (videoRef.value) videoRef.value.srcObject = stream.value || null
})

// 5. ЖИЗНЕННЫЙ ЦИКЛ
const startProcessing = async () => {
  try {
    await start()
    isStreaming.value = true
    if (videoRef.value) {
      videoRef.value.onloadedmetadata = () => {
        if (canvasRef.value) {
          canvasRef.value.width = videoRef.value!.videoWidth
          canvasRef.value.height = videoRef.value!.videoHeight
        }
        captureAndSend()
      }
    }
  } catch (e) { console.error(e) }
}

const stopProcessing = () => {
  isStreaming.value = false
  isLocked = false
  stop()
}

onMounted(() => {
  connectToServer()
  // Авто-реконнект
  reconnectInterval = setInterval(() => {
    if (!isConnected.value) connectToServer()
  }, 3000)
})

onUnmounted(() => {
  clearInterval(reconnectInterval)
  stop()
})
</script>

<template>
  <UContainer class="h-screen flex items-center justify-center bg-slate-950 p-4">
    <UCard class="w-full max-w-4xl bg-slate-900 border-slate-800 shadow-2xl overflow-hidden">
      
      <template #header>
        <div class="flex justify-between items-center text-white">
          <div class="flex gap-5 items-center">
            <h1 class="text-xl font-bold tracking-tight">OpenCV <span class="text-primary-500">Live</span></h1>
            <USelect v-model="value" :items="items" color="success" variant="outline" class="w-48" />
          </div>
          <UBadge :color="isConnected ? 'success' : 'error'" variant="solid">
            {{ isConnected ? 'Connected' : 'Disconnected' }}
          </UBadge>
        </div>
      </template>

      <div class="relative w-full aspect-video bg-black rounded-lg overflow-hidden border border-slate-700">
        <video 
          ref="videoRef" 
          autoplay 
          playsinline 
          class="absolute inset-0 w-full h-full object-contain"
          :class="{ 'opacity-0': value === 'gray' }" 
        />

        <canvas 
          ref="canvasRef" 
          class="absolute inset-0 w-full h-full object-contain pointer-events-none z-10"
          v-show="isStreaming && value !== 'none'" 
        />

        <div v-if="!isStreaming" class="absolute inset-0 flex flex-col items-center justify-center text-slate-500 bg-slate-900 z-20">
          <UIcon name="i-heroicons-video-camera" class="w-16 h-16 mb-4 text-slate-700" />
          <p>Система готова к запуску</p>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-center">
          <UButton 
            size="xl" 
            :color="isStreaming ? 'error' : 'success'" 
            @click="isStreaming ? stopProcessing() : startProcessing()" 
            class="px-10 font-bold"
          >
            {{ isStreaming ? 'Остановить' : 'Запустить камеру' }}
          </UButton>
        </div>
      </template>
    </UCard>
  </UContainer>
</template>