<script setup lang="ts">

// ref для видео
const videoEl = ref<HTMLVideoElement | null>(null)
let stream: MediaStream | null = null

// useFetch
const { data } = await useFetch('/api/test')

// функция для старта камеры
async function startCamera() {
  if (!videoEl.value) return

  try {
    stream = await navigator.mediaDevices.getUserMedia({ 
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        
        frameRate: { ideal: 30 }
      },
      audio: false
    })
    videoEl.value.srcObject = stream
  } catch (err) {
    console.error('Ошибка доступа к камере:', err)
  }
}

// функция для остановки камеры
function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }
  if (videoEl.value) videoEl.value.srcObject = null
}

// функция для кнопки
function logData() {
  console.log(data.value, stream, videoEl.value)
}



// Очистка потока при размонтировании
onBeforeUnmount(() => {
  stopCamera()
})
</script>

<template>
  <UPageHero
    title="Ultimate Vue UI library"
    description="A Nuxt/Vue-integrated UI library providing a rich set of fully-styled, accessible and highly customizable components for building modern web applications."
    headline="New release"
    orientation="vertical"
  >
    <video
      ref="videoEl"
      autoplay
      playsinline
      class="rounded-lg shadow-2xl ring ring-default object-cover w-full"
    ></video>
  </UPageHero>

  <div class="flex justify-center  mt-5 gap-5 flex-1">
    <UButton @click="logData" size="xl"  >
      Test
    </UButton>

    <UButton @click="startCamera" size="xl" >
      Start Camera
    </UButton>

    <UButton @click="stopCamera" size="xl" >
      Stop Camera
    </UButton>
  </div>
</template>
